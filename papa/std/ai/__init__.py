"""Papa-Lang AI Module — Zero-Hallucination agents for code and research analysis."""

from .researcher import Researcher, ResearchReport, Finding
from .swarm import Swarm, SwarmReport, SubTask
from .anton_researcher import AntonResearcher, LiteratureReview, PubMedClient
from .life_researcher import LifeResearcher, ConstructionAnalysis, ArxivClient

__all__ = [
    # Core
    'Researcher', 'ResearchReport', 'Finding',
    # Swarm
    'Swarm', 'SwarmReport', 'SubTask',
    # ANTON (Psychotherapy)
    'AntonResearcher', 'LiteratureReview', 'PubMedClient',
    # LIFE (Construction)
    'LifeResearcher', 'ConstructionAnalysis', 'ArxivClient',
]
