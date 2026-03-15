#!/usr/bin/env python3
"""
Papa-Lang Swarm Researcher LIFE — Construction Technology Analyst
Sources: ArXiv (cs.CE, eess), ResearchGate, ASCE, ISO standards, SNiP/SP
Focus: BIM, parametric design, digital twins, structural analysis, sustainable construction

Usage:
    pl life --query "BIM parametric design methods 2023" --output analysis.md
    pl life --analyze-project /path/to/project --standards eurocode
"""

import os, sys, json, argparse, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

try:
    import anthropic
except ImportError:
    anthropic = None

__version__ = "0.1.0"
__author__ = "papa-nexus"

# ─────────────────────────────────────────────
# Construction Domain Knowledge
# ─────────────────────────────────────────────

CONSTRUCTION_DOMAINS = {
    "BIM": {
        "name": "Building Information Modeling",
        "standards": ["ISO 19650", "IFC (ISO 16739)", "COBie", "BCF"],
        "tools": ["Revit", "ArchiCAD", "Tekla", "Navisworks", "Solibri"],
        "lod": ["LOD 100 (Conceptual)", "LOD 200 (Approximate)", "LOD 300 (Precise)",
                "LOD 350 (Construction)", "LOD 400 (Fabrication)", "LOD 500 (As-built)"],
    },
    "PARAMETRIC_DESIGN": {
        "name": "Parametric & Computational Design",
        "tools": ["Grasshopper", "Dynamo", "OpenSCAD", "Rhino", "Processing"],
        "methods": ["Generative design", "Topology optimization", "Form-finding",
                    "Evolutionary algorithms", "Multi-objective optimization"],
    },
    "DIGITAL_TWINS": {
        "name": "Digital Twin Technology",
        "components": ["IoT sensors", "Real-time data", "Simulation models",
                       "Predictive analytics", "Lifecycle management"],
        "standards": ["ISO 23247", "DTDL (Azure)", "W3C WoT"],
    },
    "STRUCTURAL_ANALYSIS": {
        "name": "Structural Analysis Methods",
        "methods": ["FEM/FEA", "CFD", "Seismic analysis", "Wind load analysis",
                   "Progressive collapse analysis", "Fatigue analysis"],
        "software": ["ETABS", "SAP2000", "ANSYS", "Abaqus", "RFEM", "Robot Structural"],
    },
    "SUSTAINABLE": {
        "name": "Sustainable Construction",
        "certifications": ["LEED", "BREEAM", "DGNB", "Passive House", "WELL"],
        "topics": ["LCA (Life Cycle Assessment)", "Embodied carbon", "Circular economy",
                  "Mass timber", "Green concrete", "Energy modeling"],
    },
}

STANDARDS_DB = {
    "eurocode": {
        "name": "Eurocodes (EN 1990-1999)",
        "codes": ["EN 1990 (Basis)", "EN 1991 (Actions)", "EN 1992 (Concrete)",
                 "EN 1993 (Steel)", "EN 1994 (Composite)", "EN 1995 (Timber)",
                 "EN 1996 (Masonry)", "EN 1997 (Geotechnical)", "EN 1998 (Seismic)",
                 "EN 1999 (Aluminium)"],
    },
    "aci": {
        "name": "ACI (American Concrete Institute)",
        "codes": ["ACI 318 (Structural Concrete)", "ACI 301 (Specifications)",
                 "ACI 214 (Strength Evaluation)", "ACI 211 (Mix Design)"],
    },
    "sp": {
        "name": "SP (Russian Building Codes)",
        "codes": ["SP 20.13330 (Loads)", "SP 63.13330 (Concrete)",
                 "SP 16.13330 (Steel)", "SP 64.13330 (Masonry)"],
    },
    "iso": {
        "name": "ISO Construction Standards",
        "codes": ["ISO 19650 (BIM)", "ISO 16739 (IFC)", "ISO 21930 (EPD)",
                 "ISO 52000 (Energy Performance)", "ISO 15686 (Service Life)"],
    },
}

SYSTEM_PROMPT = """You are LIFE, a specialized construction technology analyst.

DOMAINS: """ + json.dumps({k: v["name"] for k, v in CONSTRUCTION_DOMAINS.items()}) + """

STANDARDS: """ + json.dumps({k: v["name"] for k, v in STANDARDS_DB.items()}) + """

RULES:
- Always cite DOI or paper ID for referenced papers
- Distinguish: PEER_REVIEWED, CONFERENCE, STANDARD, TECHNICAL_REPORT, CASE_STUDY
- Rate Technology Readiness Level (TRL 1-9) for emerging technologies
- Compare methodologies objectively with pros/cons matrix
- Reference specific standard clauses when applicable
- Mark unverified claims as [NEEDS_VERIFICATION]
- Include practical implementation considerations
"""

@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    published: str = ""
    doi: str = ""

@dataclass
class ConstructionAnalysis:
    query: str
    search_params: dict = field(default_factory=dict)
    papers_found: int = 0
    papers_analyzed: int = 0
    raw_response: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

class ArxivClient:
    BASE_URL = "http://export.arxiv.org/api/query"

    def search(self, query, max_results=30, categories=None):
        cats = categories or ["cs.CE", "eess.SP", "cs.AI"]
        cat_filter = " OR ".join(f"cat:{c}" for c in cats)
        full_query = f"({query}) AND ({cat_filter})"
        params = urllib.parse.urlencode({
            "search_query": full_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "relevance",
            "sortOrder": "descending",
        })
        url = f"{self.BASE_URL}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "papa-lang-life/0.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml = resp.read().decode("utf-8")
        return self._parse(xml)

    def _parse(self, xml_text):
        ns = {"atom": "http://www.w3.org/2005/Atom",
              "arxiv": "http://arxiv.org/schemas/atom"}
        papers = []
        try:
            root = ET.fromstring(xml_text)
            for entry in root.findall("atom:entry", ns):
                aid = entry.findtext("atom:id", "", ns).split("/abs/")[-1]
                title = entry.findtext("atom:title", "", ns).strip().replace("\n"," ")
                abstract = entry.findtext("atom:summary", "", ns).strip().replace("\n"," ")
                authors = [a.findtext("atom:name","",ns) for a in entry.findall("atom:author",ns)]
                cats = [c.get("term","") for c in entry.findall("atom:category",ns)]
                published = entry.findtext("atom:published","",ns)[:10]
                doi = ""
                for link in entry.findall("atom:link", ns):
                    if link.get("title") == "doi":
                        doi = link.get("href", "")
                papers.append(ArxivPaper(arxiv_id=aid, title=title, abstract=abstract,
                    authors=authors[:5], categories=cats, published=published, doi=doi))
        except ET.ParseError:
            pass
        return papers

class LifeResearcher:
    def __init__(self, model="claude-sonnet-4-5-20251001"):
        self.model = model
        self.arxiv = ArxivClient()
        if anthropic is None:
            raise ImportError("pip install anthropic")
        self.client = anthropic.Anthropic()

    def search_papers(self, query, max_papers=30):
        print(f"Searching ArXiv: '{query}'...")
        papers = self.arxiv.search(query, max_papers)
        print(f"Found {len(papers)} papers.")
        return papers

    def analyze(self, query, max_papers=30, standards=None):
        papers = self.search_papers(query, max_papers)
        if not papers:
            return ConstructionAnalysis(query=query, search_params={"max_papers": max_papers})
        
        papers_text = []
        for p in papers:
            auth = ", ".join(p.authors[:3]) + (" et al." if len(p.authors)>3 else "")
            papers_text.append(
                f"ArXiv: {p.arxiv_id} | DOI: {p.doi or 'N/A'}\n"
                f"Title: {p.title}\nAuthors: {auth} ({p.published})\n"
                f"Categories: {', '.join(p.categories[:3])}\n"
                f"Abstract: {p.abstract[:500]}\n")
        
        std_context = ""
        if standards and standards in STANDARDS_DB:
            std = STANDARDS_DB[standards]
            std_context = f"\nRELEVANT STANDARDS ({std['name']}):\n" + \
                "\n".join(f"- {c}" for c in std["codes"])

        prompt = f"""TOPIC: {query}{std_context}

PAPERS ({len(papers)}):
{"---\n".join(papers_text)}

Generate:
1. Technology Overview & State-of-Art
2. Key Findings (with citations)
3. Technology Comparison Matrix
4. Standards Compliance Analysis
5. Implementation Recommendations
6. TRL Assessment for emerging technologies
"""
        print(f"Analyzing with Claude ({self.model})...")
        msg = self.client.messages.create(model=self.model, max_tokens=8192,
            system=SYSTEM_PROMPT, messages=[{"role":"user","content":prompt}])
        return ConstructionAnalysis(query=query,
            search_params={"max_papers": max_papers, "standards": standards},
            papers_found=len(papers), papers_analyzed=len(papers),
            raw_response=msg.content[0].text)

    def analyze_project(self, project_path, standards="eurocode"):
        """Analyze a construction project against standards."""
        path = Path(project_path)
        if not path.exists():
            return ConstructionAnalysis(query=f"Project: {project_path}",
                raw_response=f"Project path not found: {project_path}")
        
        files = []
        for ext in ['*.ifc', '*.rvt', '*.dwg', '*.pdf', '*.xlsx', '*.csv']:
            files.extend(path.rglob(ext))
        
        file_list = "\n".join(f"- {f.relative_to(path)} ({f.stat().st_size//1024}KB)"
                              for f in files[:50])
        
        std = STANDARDS_DB.get(standards, STANDARDS_DB["eurocode"])
        prompt = f"""Analyze this construction project for {std['name']} compliance.

PROJECT FILES:
{file_list or 'No construction files found'}

STANDARDS TO CHECK:
{chr(10).join(f'- {c}' for c in std['codes'])}

Provide: compliance gaps, recommendations, risk assessment.
"""
        msg = self.client.messages.create(model=self.model, max_tokens=4096,
            system=SYSTEM_PROMPT, messages=[{"role":"user","content":prompt}])
        return ConstructionAnalysis(query=f"Project: {project_path}",
            search_params={"standards": standards},
            raw_response=msg.content[0].text)

    def generate_report(self, analysis):
        return f"""# Construction Technology Analysis: {analysis.query}
## Search Parameters
- Query: {analysis.query}
- Papers: {analysis.papers_found} found, {analysis.papers_analyzed} analyzed
- Standards: {analysis.search_params.get('standards', 'N/A')}
- Generated: {analysis.timestamp}

{analysis.raw_response}

---
*Generated by LIFE (Papa-Lang Construction Researcher) v{__version__}*
"""

def main():
    p = argparse.ArgumentParser(prog='pl life',
        description='LIFE Construction Technology Analyst')
    p.add_argument('--query', '-q', help='Research query')
    p.add_argument('--analyze-project', help='Path to construction project')
    p.add_argument('--standards', default='eurocode',
        choices=['eurocode', 'aci', 'sp', 'iso'])
    p.add_argument('--max-papers', type=int, default=30)
    p.add_argument('--output', '-o')
    p.add_argument('--model', default='claude-sonnet-4-5-20251001')
    args = p.parse_args()
    
    if not args.query and not args.analyze_project:
        p.error("Either --query or --analyze-project required")
    
    r = LifeResearcher(model=args.model)
    print(f"LIFE v{__version__}")
    
    if args.analyze_project:
        analysis = r.analyze_project(args.analyze_project, args.standards)
    else:
        analysis = r.analyze(args.query, args.max_papers, args.standards)
    
    report = r.generate_report(analysis)
    if args.output:
        Path(args.output).write_text(report)
        print(f"Saved: {args.output}")
    else:
        print(report)

if __name__ == '__main__':
    main()
