"""
Design Studio module for retrieval-ranking interface.

Provides transparent, explainable search and ranking of sensor designs
from the shared database without using black-box ML models.
"""

from .ranking_engine import RankingEngine, create_data_quality_flag

__all__ = ['RankingEngine', 'create_data_quality_flag']