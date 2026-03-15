#!/usr/bin/env python3
"""
Papa-Lang AI Researcher Agent
Reads architecture.db, gathers relevant files, and uses Claude for structured analysis.

Usage:
    pl researcher --task "analyze auth flow" --db architecture.db --output report.md
    pl researcher --task "find security issues" --db architecture.db --severity high
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

try:
    import anthropic
except ImportError:
    anthropic = None

__version__ = "0.1.0"
__author__ = "papa-nexus"

# ─────────────────────────────────────────────
# Zero-Hallucination System Prompt
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """You are a code analyst working on Papa Ecosystem.
RULES:
- Only reference files that exist in the provided context
- Never invent function names, routes, or models
- If unsure, say "I cannot determine this without seeing X file"
- Always cite the specific file and line number for each finding
- Distinguish between: CONFIRMED (seen in code) vs INFERRED (logical conclusion)

OUTPUT FORMAT:
For each finding, use:
[CONFIRMED] file:line — description
[INFERRED] based on X — description
[NEEDS_REVIEW] cannot determine without seeing Y
"""


# ─────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────

@dataclass
class Finding:
    """A single research finding."""
    category: str  # CONFIRMED, INFERRED, NEEDS_REVIEW
    file_path: str
    line: Optional[int]
    description: str
    severity: str = "info"  # info, low, medium, high, critical


@dataclass
class ResearchReport:
    """Structured research report."""
    task: str
    summary: str
    findings: list[Finding] = field(default_factory=list)
    files_analyzed: int = 0
    total_lines: int = 0
    model_used: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    raw_response: str = ""


# ─────────────────────────────────────────────
# Researcher
# ─────────────────────────────────────────────

class Researcher:
    """AI Researcher agent that analyzes codebases using Claude."""

    def __init__(
        self,
        db_path: str,
        project_root: str = ".",
        model: str = "claude-sonnet-4-5-20251001",
    ):
        self.db_path = db_path
        self.project_root = Path(project_root).resolve()
        self.model = model
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row

        if anthropic is None:
            raise ImportError(
                "anthropic package required. Install with: pip install anthropic"
            )
        self.client = anthropic.Anthropic()

    def collect_context(self, task: str, max_files: int = 20) -> list[dict]:
        """Query architecture.db for relevant files based on task description."""
        cur = self.db.cursor()
        terms = task.lower().split()

        # Build semantic search query
        conditions = []
        params = []
        for term in terms:
            # Skip common words
            if term in {'the', 'a', 'an', 'in', 'on', 'for', 'to', 'of', 'and', 'or', 'is'}:
                continue
            conditions.append(
                "(LOWER(relative_path) LIKE ? OR LOWER(module) LIKE ? "
                "OR LOWER(functions) LIKE ? OR LOWER(classes) LIKE ? "
                "OR LOWER(exports) LIKE ?)"
            )
            like = f"%{term}%"
            params.extend([like, like, like, like, like])

        where = " OR ".join(conditions) if conditions else "1=1"

        # Score by relevance (number of matching terms)
        sql = f"""
            SELECT *, 
                ({' + '.join([
                    f"(CASE WHEN LOWER(relative_path) LIKE '%{t}%' THEN 2 ELSE 0 END "
                    f"+ CASE WHEN LOWER(functions) LIKE '%{t}%' THEN 1 ELSE 0 END "
                    f"+ CASE WHEN LOWER(classes) LIKE '%{t}%' THEN 1 ELSE 0 END)"
                    for t in terms if t not in {'the','a','an','in','on','for','to','of','and','or','is'}
                ] or ['0'])}) as relevance
            FROM nodes 
            WHERE {where}
            ORDER BY relevance DESC, lines DESC
            LIMIT ?
        """
        params.append(max_files)

        cur.execute(sql, params)
        rows = cur.fetchall()

        files = []
        for row in rows:
            filepath = self.project_root / row['relative_path']
            try:
                content = filepath.read_text(encoding='utf-8', errors='replace')
            except (OSError, FileNotFoundError):
                content = f"[FILE NOT FOUND: {row['relative_path']}]"

            files.append({
                'path': row['relative_path'],
                'language': row['language'],
                'lines': row['lines'],
                'module': row['module'],
                'functions': row['functions'],
                'classes': row['classes'],
                'content': content,
            })

        return files

    def _build_prompt(self, task: str, files: list[dict]) -> str:
        """Build the analysis prompt with file context."""
        context_parts = []
        for f in files:
            context_parts.append(
                f"### FILE: {f['path']} ({f['language']}, {f['lines']} lines)\n"
                f"Module: {f['module']}\n"
                f"Functions: {f['functions']}\n"
                f"Classes: {f['classes']}\n"
                f"\n```{f['language']}\n{f['content']}\n```"
            )

        files_context = "\n\n".join(context_parts)

        return f"""## TASK
{task}

## PROJECT FILES ({len(files)} files)
{files_context}

## INSTRUCTIONS
Analyze the provided files for the given task. Follow Zero-Hallucination rules strictly.
Provide your analysis in this structure:

### Summary
Brief overview of findings.

### Findings
List each finding with [CONFIRMED], [INFERRED], or [NEEDS_REVIEW] prefix.

### Recommendations
Actionable next steps.

### Files Not Available
List any files you would need to see for a complete analysis.
"""

    def analyze(self, task: str, max_files: int = 20, severity: str = "all") -> ResearchReport:
        """Run full analysis: collect context, call Claude, return structured report."""
        # Step 1: Collect relevant files
        files = self.collect_context(task, max_files)

        if not files:
            return ResearchReport(
                task=task,
                summary="No relevant files found in architecture.db for this task.",
                files_analyzed=0,
            )

        # Step 2: Build prompt
        prompt = self._build_prompt(task, files)

        # Step 3: Call Claude API
        message = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_response = message.content[0].text

        # Step 4: Parse response into findings
        findings = self._parse_findings(raw_response, severity)

        return ResearchReport(
            task=task,
            summary=self._extract_summary(raw_response),
            findings=findings,
            files_analyzed=len(files),
            total_lines=sum(f['lines'] for f in files),
            model_used=self.model,
            raw_response=raw_response,
        )

    def _parse_findings(self, response: str, severity_filter: str = "all") -> list[Finding]:
        """Parse Claude's response into structured findings."""
        findings = []
        import re

        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Match [CONFIRMED], [INFERRED], [NEEDS_REVIEW] patterns
            match = re.match(
                r'\[(CONFIRMED|INFERRED|NEEDS_REVIEW)\]\s*'
                r'(?:([\w./\-]+)(?::?(\d+))?\s*[—\-])?\s*(.+)',
                line,
            )
            if match:
                category = match.group(1)
                file_path = match.group(2) or ""
                line_num = int(match.group(3)) if match.group(3) else None
                description = match.group(4)

                # Infer severity from keywords
                sev = "info"
                desc_lower = description.lower()
                if any(w in desc_lower for w in ['critical', 'vulnerability', 'injection', 'rce']):
                    sev = "critical"
                elif any(w in desc_lower for w in ['security', 'unsafe', 'exposed', 'leak']):
                    sev = "high"
                elif any(w in desc_lower for w in ['warning', 'deprecated', 'missing', 'potential']):
                    sev = "medium"
                elif any(w in desc_lower for w in ['suggestion', 'consider', 'minor']):
                    sev = "low"

                if severity_filter == "all" or sev == severity_filter:
                    findings.append(Finding(
                        category=category,
                        file_path=file_path,
                        line=line_num,
                        description=description,
                        severity=sev,
                    ))

        return findings

    def _extract_summary(self, response: str) -> str:
        """Extract the Summary section from Claude's response."""
        lines = response.split('\n')
        in_summary = False
        summary_lines = []
        for line in lines:
            if '### Summary' in line or '## Summary' in line:
                in_summary = True
                continue
            if in_summary and line.startswith('#'):
                break
            if in_summary:
                summary_lines.append(line)
        return '\n'.join(summary_lines).strip() or response[:500]

    def generate_report(self, report: ResearchReport, fmt: str = "markdown") -> str:
        """Generate formatted report output."""
        if fmt == "json":
            return json.dumps(asdict(report), indent=2, default=str)

        lines = [
            f"# Research Report: {report.task}",
            f"",
            f"**Generated:** {report.timestamp}",
            f"**Model:** {report.model_used}",
            f"**Files analyzed:** {report.files_analyzed}",
            f"**Total lines:** {report.total_lines}",
            f"",
            f"## Summary",
            f"",
            report.summary,
            f"",
            f"## Findings ({len(report.findings)})",
            f"",
        ]

        # Group by severity
        for sev in ['critical', 'high', 'medium', 'low', 'info']:
            sev_findings = [f for f in report.findings if f.severity == sev]
            if sev_findings:
                lines.append(f"### {sev.upper()} ({len(sev_findings)})")
                lines.append("")
                for finding in sev_findings:
                    loc = f"{finding.file_path}"
                    if finding.line:
                        loc += f":{finding.line}"
                    lines.append(
                        f"- **[{finding.category}]** {loc} — {finding.description}"
                    )
                lines.append("")

        # Raw response
        lines.extend([
            "## Full Analysis",
            "",
            report.raw_response,
        ])

        return '\n'.join(lines)

    def close(self):
        self.db.close()


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog='pl researcher',
        description='Papa-Lang AI Researcher — Zero-Hallucination code analysis',
    )
    parser.add_argument('--task', '-t', required=True, help='Analysis task description')
    parser.add_argument('--db', required=True, help='Path to architecture.db')
    parser.add_argument('--root', default='.', help='Project root directory')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--format', '-f', choices=['markdown', 'json'], default='markdown')
    parser.add_argument('--max-files', type=int, default=20, help='Max files to analyze')
    parser.add_argument('--severity', default='all', 
                       choices=['all', 'critical', 'high', 'medium', 'low', 'info'],
                       help='Filter findings by severity')
    parser.add_argument('--model', default='claude-sonnet-4-5-20251001', help='Claude model to use')

    args = parser.parse_args()

    researcher = Researcher(
        db_path=args.db,
        project_root=args.root,
        model=args.model,
    )

    try:
        print(f"Researching: {args.task}")
        print(f"Using model: {args.model}")

        report = researcher.analyze(
            task=args.task,
            max_files=args.max_files,
            severity=args.severity,
        )

        output = researcher.generate_report(report, fmt=args.format)

        if args.output:
            Path(args.output).write_text(output)
            print(f"Report saved to: {args.output}")
        else:
            print(output)

        print(f"\nAnalyzed {report.files_analyzed} files, found {len(report.findings)} findings.")
    finally:
        researcher.close()


if __name__ == '__main__':
    main()
