#!/usr/bin/env python3
"""
Papa-Lang Swarm Researcher ANTON — Psychotherapy Literature Analyst
Primary source: PubMed (E-utilities API)
Secondary: Cochrane Library, PsycINFO, ResearchGate

Usage:
    pl anton --query "psychoallergology somatization" --years 7 --output review.md
    pl anton --query "CBT anxiety disorders meta-analysis" --years 5 --format academic
"""

import os, sys, json, argparse, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta

try:
    import anthropic
except ImportError:
    anthropic = None

__version__ = "0.1.0"
__author__ = "papa-nexus"

THERAPEUTIC_FRAMEWORKS = {
    "CBT": {"name": "Cognitive Behavioral Therapy", "founder": "Aaron Beck",
            "focus": "Cognitive distortions, automatic thoughts, behavioral activation",
            "evidence": "Strong for depression, anxiety, PTSD"},
    "REBT": {"name": "Rational Emotive Behavior Therapy", "founder": "Albert Ellis",
             "focus": "Irrational beliefs, ABC model", "evidence": "Moderate for anger, anxiety"},
    "MBCT": {"name": "Mindfulness-Based Cognitive Therapy", "founder": "Segal, Williams, Teasdale",
             "focus": "Decentering, rumination prevention", "evidence": "Strong for recurrent depression"},
    "DBT": {"name": "Dialectical Behavior Therapy", "founder": "Marsha Linehan",
            "focus": "Distress tolerance, emotion regulation, interpersonal effectiveness",
            "evidence": "Strong for BPD, suicidality, self-harm"},
    "ACT": {"name": "Acceptance & Commitment Therapy", "founder": "Steven Hayes",
            "focus": "Psychological flexibility, values-based action",
            "evidence": "Strong for chronic pain, anxiety, depression"},
    "MCT": {"name": "Metacognitive Therapy", "founder": "Adrian Wells",
            "focus": "Metacognitive beliefs about worry and rumination",
            "evidence": "Growing for GAD, depression, PTSD"},
}

BPSM_MODEL = "Biopsychosocial Model: integrate biological, psychological, social factors in all analyses"

SYSTEM_PROMPT = """You are ANTON, a specialized psychotherapy literature analyst.

THERAPEUTIC FRAMEWORKS: """ + json.dumps(THERAPEUTIC_FRAMEWORKS) + """

BPSM: """ + BPSM_MODEL + """

RULES:
- Always cite DOI or PMID for each referenced article
- Distinguish: META-ANALYSIS, RCT, SYSTEMATIC_REVIEW, OBSERVATIONAL, CASE_STUDY
- Rate evidence: HIGH (meta-analysis, large RCT), MODERATE (small RCT), LOW (observational)
- Map findings to CBT/DBT/ACT frameworks
- Include BPSM analysis for clinical recommendations
- Mark uncertain findings as [NEEDS_VERIFICATION]
- Never fabricate DOIs or study results
"""

@dataclass
class PubMedArticle:
    pmid: str
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    journal: str = ""
    year: str = ""
    doi: str = ""
    mesh_terms: list[str] = field(default_factory=list)
    pub_type: str = ""

@dataclass
class LiteratureReview:
    query: str
    search_params: dict = field(default_factory=dict)
    articles_found: int = 0
    articles_analyzed: int = 0
    raw_response: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

class PubMedClient:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, email="papa@papa-ai.ae"):
        self.email = email
        self.api_key = os.getenv("NCBI_API_KEY", "")

    def _fetch(self, endpoint, **params):
        base = {"email": self.email, "tool": "papa-lang-anton"}
        if self.api_key:
            base["api_key"] = self.api_key
        base.update(params)
        url = f"{self.BASE_URL}/{endpoint}?{urllib.parse.urlencode(base)}"
        req = urllib.request.Request(url, headers={"User-Agent": "papa-lang-anton/0.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8")

    def search(self, query, max_results=50, min_date=None, max_date=None):
        params = {"db": "pubmed", "term": query, "retmax": str(max_results),
                  "sort": "relevance", "retmode": "json"}
        if min_date:
            params["mindate"] = min_date
            params["datetype"] = "pdat"
        if max_date:
            params["maxdate"] = max_date
        data = json.loads(self._fetch("esearch.fcgi", **params))
        return data.get("esearchresult", {}).get("idlist", [])

    def fetch_articles(self, pmids):
        if not pmids:
            return []
        xml = self._fetch("efetch.fcgi", db="pubmed", id=",".join(pmids),
                          rettype="xml", retmode="xml")
        articles = []
        try:
            root = ET.fromstring(xml)
            for elem in root.findall(".//PubmedArticle"):
                articles.append(self._parse(elem))
        except ET.ParseError:
            pass
        return articles

    def _parse(self, elem):
        mc = elem.find(".//MedlineCitation")
        pmid = mc.findtext(".//PMID", "")
        art = mc.find(".//Article")
        title = art.findtext(".//ArticleTitle", "") if art else ""
        abst = art.find(".//Abstract") if art else None
        parts = []
        if abst:
            for t in abst.findall(".//AbstractText"):
                label = t.get("Label", "")
                text = t.text or ""
                parts.append(f"{label}: {text}" if label else text)
        abstract = " ".join(parts)
        authors = []
        al = art.find(".//AuthorList") if art else None
        if al:
            for a in al.findall(".//Author"):
                ln = a.findtext("LastName", "")
                fn = a.findtext("ForeName", "")
                if ln: authors.append(f"{ln} {fn}".strip())
        journal = ""
        je = art.find(".//Journal") if art else None
        if je: journal = je.findtext(".//Title", "")
        pd = art.find(".//Journal/JournalIssue/PubDate") if art else None
        year = pd.findtext("Year", "") if pd else ""
        doi = ""
        if art:
            for eid in art.findall(".//ELocationID"):
                if eid.get("EIdType") == "doi": doi = eid.text or ""
        mesh = []
        ml = mc.find(".//MeshHeadingList")
        if ml:
            for h in ml.findall(".//MeshHeading"):
                d = h.findtext(".//DescriptorName", "")
                if d: mesh.append(d)
        pts = []
        if art:
            for pt in art.findall(".//PublicationTypeList/PublicationType"):
                if pt.text: pts.append(pt.text)
        return PubMedArticle(pmid=pmid, title=title, abstract=abstract,
            authors=authors[:5], journal=journal, year=year, doi=doi,
            mesh_terms=mesh, pub_type=", ".join(pts))

class AntonResearcher:
    def __init__(self, model="claude-sonnet-4-5-20251001"):
        self.model = model
        self.pubmed = PubMedClient()
        if anthropic is None:
            raise ImportError("pip install anthropic")
        self.client = anthropic.Anthropic()

    def search_literature(self, query, years=5, max_articles=30):
        min_d = (datetime.now() - timedelta(days=years*365)).strftime("%Y/%m/%d")
        max_d = datetime.now().strftime("%Y/%m/%d")
        print(f"Searching PubMed: '{query}' (last {years} years)...")
        pmids = self.pubmed.search(query, max_articles, min_d, max_d)
        print(f"Found {len(pmids)} articles, fetching details...")
        return self.pubmed.fetch_articles(pmids) if pmids else []

    def analyze(self, query, years=5, max_articles=30, fmt="academic"):
        articles = self.search_literature(query, years, max_articles)
        if not articles:
            return LiteratureReview(query=query, search_params={"years": years})
        arts_text = []
        for a in articles:
            auth = ", ".join(a.authors[:3]) + (" et al." if len(a.authors)>3 else "")
            arts_text.append(f"PMID:{a.pmid} DOI:{a.doi or 'N/A'}\n"
                f"Title: {a.title}\nAuthors: {auth} ({a.year})\n"
                f"Journal: {a.journal}\nType: {a.pub_type}\n"
                f"MeSH: {', '.join(a.mesh_terms[:5])}\n"
                f"Abstract: {a.abstract[:600]}\n")
        prompt = f"""TOPIC: {query}\n\nARTICLES ({len(articles)}):\n{"---\n".join(arts_text)}
\nGenerate: Key Findings (with citations), Current State, Perspectives,
Clinical Recommendations (CBT/DBT/ACT), BPSM Analysis."""
        print(f"Analyzing with Claude ({self.model})...")
        msg = self.client.messages.create(model=self.model, max_tokens=8192,
            system=SYSTEM_PROMPT, messages=[{"role":"user","content":prompt}])
        return LiteratureReview(query=query,
            search_params={"years":years,"format":fmt},
            articles_found=len(articles), articles_analyzed=len(articles),
            raw_response=msg.content[0].text)

    def generate_report(self, review):
        return f"""# Literature Review: {review.query}
## Search Parameters
- Query: {review.query}
- Time range: Last {review.search_params.get('years',5)} years
- Articles: {review.articles_found} found, {review.articles_analyzed} analyzed
- Generated: {review.timestamp}

{review.raw_response}

---
*Generated by ANTON (Papa-Lang Psychotherapy Researcher) v{__version__}*
"""

def main():
    p = argparse.ArgumentParser(prog='pl anton',
        description='ANTON Psychotherapy Literature Analyst')
    p.add_argument('--query', '-q', required=True)
    p.add_argument('--years', type=int, default=5)
    p.add_argument('--max-articles', type=int, default=30)
    p.add_argument('--output', '-o')
    p.add_argument('--format', '-f', choices=['academic','clinical','summary'], default='academic')
    p.add_argument('--model', default='claude-sonnet-4-5-20251001')
    args = p.parse_args()
    r = AntonResearcher(model=args.model)
    print(f"ANTON v{__version__} | Query: {args.query} | {args.years}yr")
    review = r.analyze(args.query, args.years, args.max_articles, args.format)
    report = r.generate_report(review)
    if args.output:
        Path(args.output).write_text(report)
        print(f"Saved: {args.output}")
    else:
        print(report)

if __name__ == '__main__':
    main()
