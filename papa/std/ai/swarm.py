#!/usr/bin/env python3
"""
Papa-Lang Swarm Orchestrator
Orchestrates multiple Researcher agents working in parallel on different aspects of the codebase.

Usage:
    pl swarm --task "full security audit" --db architecture.db
    pl swarm --task "refactor auth module" --db architecture.db --agents 4
"""

import os
import sys
import json
import sqlite3
import asyncio
import argparse
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

try:
    import anthropic
except ImportError:
    anthropic = None

from .researcher import Researcher, ResearchReport, Finding, SYSTEM_PROMPT

__version__ = "0.1.0"
__author__ = "papa-nexus"


# ─────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────

@dataclass
class SubTask:
    """A decomposed subtask for parallel execution."""
    id: str
    title: str
    description: str
    focus_modules: list[str] = field(default_factory=list)
    max_files: int = 15
    priority: int = 0
    depends_on: list[str] = field(default_factory=list)


@dataclass
class SwarmReport:
    """Unified report from all swarm agents."""
    task: str
    subtasks: list[SubTask] = field(default_factory=list)
    reports: list[ResearchReport] = field(default_factory=list)
    synthesis: str = ""
    total_files_analyzed: int = 0
    total_findings: int = 0
    conflicts: list[str] = field(default_factory=list)
    agents_used: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


# ─────────────────────────────────────────────
# Task Decomposer
# ─────────────────────────────────────────────

DECOMPOSE_PROMPT = """You are a task decomposition expert for codebase analysis.

Given a high-level task and a project structure, break it down into {max_agents} parallel subtasks.

PROJECT MODULES:
{modules}

DEPENDENCY EDGES (top 50):
{edges}

TASK: {task}

Return a JSON array of subtasks, each with:
- id: unique identifier (e.g., "sub_1")
- title: short title
- description: what this subtask should analyze
- focus_modules: list of module paths to focus on
- priority: 0 (highest) to 3 (lowest)
- depends_on: list of subtask IDs this depends on (empty for independent tasks)

Return ONLY valid JSON, no markdown.
"""


class Swarm:
    """Orchestrates multiple Researcher agents working in parallel."""

    def __init__(
        self,
        db_path: str,
        project_root: str = ".",
        max_agents: int = 4,
        model: str = "claude-sonnet-4-5-20251001",
    ):
        self.db_path = db_path
        self.project_root = Path(project_root).resolve()
        self.max_agents = max_agents
        self.model = model
        self.agents: list[Researcher] = []

        if anthropic is None:
            raise ImportError(
                "anthropic package required. Install with: pip install anthropic"
            )
        self.client = anthropic.Anthropic()

    def _get_project_info(self) -> tuple[list[str], list[tuple]]:
        """Get project modules and dependency edges from architecture.db."""
        db = sqlite3.connect(self.db_path)
        cur = db.cursor()

        # Get unique modules
        cur.execute("SELECT DISTINCT module FROM nodes ORDER BY module")
        modules = [row[0] for row in cur.fetchall()]

        # Get dependency edges
        cur.execute("SELECT source, target, edge_type FROM edges LIMIT 50")
        edges = cur.fetchall()

        db.close()
        return modules, edges

    def decompose_task(self, task: str) -> list[SubTask]:
        """Split task into parallel subtasks using Claude."""
        modules, edges = self._get_project_info()

        modules_str = "\n".join(f"- {m}" for m in modules[:50])
        edges_str = "\n".join(f"  {s} -> {t} ({et})" for s, t, et in edges[:50])

        prompt = DECOMPOSE_PROMPT.format(
            max_agents=self.max_agents,
            modules=modules_str,
            edges=edges_str,
            task=task,
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = message.content[0].text.strip()

        # Parse JSON response
        try:
            # Handle markdown code blocks
            if response_text.startswith("```"):
                response_text = response_text.split("\n", 1)[1].rsplit("```", 1)[0]
            subtasks_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Fallback: create simple subtasks
            subtasks_data = [
                {
                    "id": f"sub_{i+1}",
                    "title": f"Analyze chunk {i+1}",
                    "description": f"Analyze modules {', '.join(modules[i::self.max_agents][:5])}",
                    "focus_modules": modules[i::self.max_agents][:5],
                    "priority": i,
                    "depends_on": [],
                }
                for i in range(min(self.max_agents, len(modules)))
            ]

        subtasks = []
        for st in subtasks_data[:self.max_agents]:
            subtasks.append(SubTask(
                id=st.get('id', f'sub_{len(subtasks)+1}'),
                title=st.get('title', 'Analysis subtask'),
                description=st.get('description', task),
                focus_modules=st.get('focus_modules', []),
                max_files=st.get('max_files', 15),
                priority=st.get('priority', 0),
                depends_on=st.get('depends_on', []),
            ))

        return subtasks

    def _run_agent(self, subtask: SubTask) -> ResearchReport:
        """Run a single Researcher agent on a subtask."""
        agent = Researcher(
            db_path=self.db_path,
            project_root=str(self.project_root),
            model=self.model,
        )
        self.agents.append(agent)

        # Modify task to focus on specific modules
        focused_task = (
            f"{subtask.description}\n\n"
            f"Focus on these modules: {', '.join(subtask.focus_modules)}"
            if subtask.focus_modules
            else subtask.description
        )

        try:
            report = agent.analyze(
                task=focused_task,
                max_files=subtask.max_files,
            )
            return report
        except Exception as e:
            return ResearchReport(
                task=subtask.title,
                summary=f"Agent error: {str(e)}",
            )
        finally:
            agent.close()

    def run_parallel(self, subtasks: list[SubTask]) -> list[ResearchReport]:
        """Run Researcher agents in parallel using ThreadPoolExecutor."""
        # Separate independent and dependent tasks
        independent = [st for st in subtasks if not st.depends_on]
        dependent = [st for st in subtasks if st.depends_on]

        reports = []

        # Run independent tasks in parallel
        with ThreadPoolExecutor(max_workers=self.max_agents) as executor:
            futures = {
                executor.submit(self._run_agent, st): st
                for st in independent
            }
            for future in futures:
                try:
                    report = future.result(timeout=300)
                    reports.append(report)
                except Exception as e:
                    st = futures[future]
                    reports.append(ResearchReport(
                        task=st.title,
                        summary=f"Execution error: {str(e)}",
                    ))

        # Run dependent tasks sequentially
        for st in dependent:
            report = self._run_agent(st)
            reports.append(report)

        return reports

    def synthesize(self, task: str, reports: list[ResearchReport]) -> str:
        """Final synthesis pass — merge findings and resolve conflicts."""
        if not reports:
            return "No reports to synthesize."

        reports_text = []
        for i, report in enumerate(reports):
            reports_text.append(
                f"### Agent {i+1}: {report.task}\n"
                f"Files: {report.files_analyzed}, Findings: {len(report.findings)}\n"
                f"Summary: {report.summary}\n"
                f"Findings:\n" + "\n".join(
                    f"- [{f.category}] {f.file_path}:{f.line or '?'} — {f.description}"
                    for f in report.findings
                )
            )

        synthesis_prompt = f"""You are synthesizing multiple code analysis reports into a unified report.

ORIGINAL TASK: {task}

AGENT REPORTS:
{"\n\n".join(reports_text)}

INSTRUCTIONS:
1. Merge all findings, removing duplicates
2. Identify and flag any CONFLICTS between agent findings
3. Provide a unified summary
4. List prioritized recommendations
5. Follow Zero-Hallucination rules — only reference confirmed findings

Output a structured synthesis report.
"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": synthesis_prompt}],
        )

        return message.content[0].text

    def run(self, task: str) -> SwarmReport:
        """Execute full swarm analysis pipeline."""
        print(f"Decomposing task into {self.max_agents} subtasks...")
        subtasks = self.decompose_task(task)
        print(f"Created {len(subtasks)} subtasks:")
        for st in subtasks:
            print(f"  [{st.id}] {st.title} (priority: {st.priority})")

        print(f"\nRunning {len(subtasks)} agents in parallel...")
        reports = self.run_parallel(subtasks)

        print(f"\nSynthesizing {len(reports)} reports...")
        synthesis = self.synthesize(task, reports)

        # Collect all findings
        all_findings = []
        for report in reports:
            all_findings.extend(report.findings)

        # Detect conflicts (same file, different conclusions)
        conflicts = self._detect_conflicts(all_findings)

        return SwarmReport(
            task=task,
            subtasks=subtasks,
            reports=reports,
            synthesis=synthesis,
            total_files_analyzed=sum(r.files_analyzed for r in reports),
            total_findings=len(all_findings),
            conflicts=conflicts,
            agents_used=len(subtasks),
        )

    def _detect_conflicts(self, findings: list[Finding]) -> list[str]:
        """Detect conflicting findings about the same file."""
        from collections import defaultdict
        by_file = defaultdict(list)
        for f in findings:
            if f.file_path:
                by_file[f.file_path].append(f)

        conflicts = []
        for filepath, file_findings in by_file.items():
            if len(file_findings) < 2:
                continue
            categories = set(f.category for f in file_findings)
            if 'CONFIRMED' in categories and 'NEEDS_REVIEW' in categories:
                conflicts.append(
                    f"Conflict in {filepath}: one agent confirmed, another needs review"
                )

        return conflicts

    def generate_report(self, swarm_report: SwarmReport, fmt: str = "markdown") -> str:
        """Generate formatted swarm report."""
        if fmt == "json":
            return json.dumps(asdict(swarm_report), indent=2, default=str)

        lines = [
            f"# Swarm Analysis Report: {swarm_report.task}",
            f"",
            f"**Generated:** {swarm_report.timestamp}",
            f"**Agents used:** {swarm_report.agents_used}",
            f"**Total files analyzed:** {swarm_report.total_files_analyzed}",
            f"**Total findings:** {swarm_report.total_findings}",
            f"",
        ]

        if swarm_report.conflicts:
            lines.extend([
                "## Conflicts Detected",
                "",
                *[f"- {c}" for c in swarm_report.conflicts],
                "",
            ])

        lines.extend([
            "## Subtasks",
            "",
            *[
                f"- **[{st.id}]** {st.title} — {st.description[:100]}..."
                for st in swarm_report.subtasks
            ],
            "",
            "## Synthesis",
            "",
            swarm_report.synthesis,
            "",
            "## Individual Agent Reports",
            "",
        ])

        for i, report in enumerate(swarm_report.reports):
            lines.extend([
                f"### Agent {i+1}: {report.task[:80]}",
                f"Files: {report.files_analyzed}, Findings: {len(report.findings)}",
                "",
                report.summary[:500] if report.summary else "No summary",
                "",
            ])

        return "\n".join(lines)

    def close(self):
        for agent in self.agents:
            try:
                agent.close()
            except Exception:
                pass


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog='pl swarm',
        description='Papa-Lang Swarm — Multi-agent parallel codebase analysis',
    )
    parser.add_argument('--task', '-t', required=True, help='Analysis task description')
    parser.add_argument('--db', required=True, help='Path to architecture.db')
    parser.add_argument('--root', default='.', help='Project root directory')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--format', '-f', choices=['markdown', 'json'], default='markdown')
    parser.add_argument('--agents', type=int, default=4, help='Max parallel agents')
    parser.add_argument('--model', default='claude-sonnet-4-5-20251001', help='Claude model')

    args = parser.parse_args()

    swarm = Swarm(
        db_path=args.db,
        project_root=args.root,
        max_agents=args.agents,
        model=args.model,
    )

    try:
        report = swarm.run(args.task)
        output = swarm.generate_report(report, fmt=args.format)

        if args.output:
            Path(args.output).write_text(output)
            print(f"\nReport saved to: {args.output}")
        else:
            print(output)

        print(f"\nSwarm complete: {report.agents_used} agents, "
              f"{report.total_files_analyzed} files, "
              f"{report.total_findings} findings.")
    finally:
        swarm.close()


if __name__ == '__main__':
    main()
