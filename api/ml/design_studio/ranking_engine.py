"""
Transparent ranking engine for Design Studio retrieval-ranking.

This module implements explainable, non-black-box scoring for sensor design search.
Uses weighted similarity scoring across available fields with full per-field breakdown.
"""

from typing import Dict, Any, Optional, List

# Handle import flexibility for different execution contexts
try:
    from app.schemas.design_studio import (
        FieldScoreBreakdown, DataQualityFlag, RankedSearchResult
    )
except ImportError:
    from schemas.design_studio import (
        FieldScoreBreakdown, DataQualityFlag, RankedSearchResult
    )


class RankingEngine:
    """
    Transparent ranking engine for sensor performance records.
    
    Uses weighted similarity scoring with explainable per-field contributions.
    No ML/embeddings - pure deterministic scoring for full transparency.
    
    Field Weights Rationale:
    - Current weights are DEFAULT VALUES that sum to 1.0 (100%)
    - These were chosen as reasonable starting points but are NOT based on
      specific domain expertise or experimental validation
    - Future iterations should adjust weights based on:
      * Domain expert input on relative importance of each field
      * User feedback on ranking quality
      * Analysis of actual search result relevance
    - Weights are configurable via the custom_weights parameter in __init__
    """
    
    # Scoring constants for consistency across field types
    EXACT_MATCH_SCORE = 1.0
    PARTIAL_MATCH_SCORE = 0.8  # Unified partial/contains match score for all fields
    NO_MATCH_SCORE = 0.0
    
    # Default weights for different fields (sum = 1.0)
    # NOTE: These are arbitrary defaults - adjust based on domain requirements
    DEFAULT_WEIGHTS = {
        'analyte': 0.35,           # Analyte match - moderately high importance
        'lod': 0.30,               # LOD proximity - high importance for performance specs
        'nanomaterial': 0.15,      # Material type - moderate importance
        'transduction': 0.10,      # Transduction type - lower importance
        'matrix': 0.10,            # Matrix type - lower importance
    }
    
    def __init__(self, custom_weights: Optional[Dict[str, float]] = None):
        """
        Initialize ranking engine with optional custom weights.
        
        Args:
            custom_weights: Optional custom field weights (keys must match DEFAULT_WEIGHTS)
        """
        self.weights = custom_weights if custom_weights else self.DEFAULT_WEIGHTS.copy()
        
        # Normalize weights to sum to 1.0
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}
    
    def score_record(
        self,
        record: Dict[str, Any],
        target_spec: Dict[str, Any]
    ) -> tuple[float, List[FieldScoreBreakdown]]:
        """
        Score a single record against the target specification.
        
        Args:
            record: Database record as dictionary
            target_spec: Target specification from user
            
        Returns:
            Tuple of (overall_score, field_breakdowns)
        """
        field_breakdowns = []
        total_score = 0.0
        
        # Score each field if present in target spec
        if target_spec.get('analyte') and record.get('analyte'):
            score, breakdown = self._score_analyte(
                record['analyte'], 
                target_spec['analyte']
            )
            field_breakdowns.append(breakdown)
            total_score += breakdown.contribution
        
        if target_spec.get('lod_mol_per_l') and record.get('lod_mol_per_l'):
            score, breakdown = self._score_lod(
                record['lod_mol_per_l'],
                target_spec['lod_mol_per_l']
            )
            field_breakdowns.append(breakdown)
            total_score += breakdown.contribution
        
        if target_spec.get('nanomaterial') and record.get('nanomaterial'):
            score, breakdown = self._score_nanomaterial(
                record['nanomaterial'],
                target_spec['nanomaterial']
            )
            field_breakdowns.append(breakdown)
            total_score += breakdown.contribution
        
        if target_spec.get('transduction_type') and record.get('transduction_type'):
            score, breakdown = self._score_transduction(
                record.get('transduction_type'),
                target_spec['transduction_type']
            )
            field_breakdowns.append(breakdown)
            total_score += breakdown.contribution
        
        if target_spec.get('matrix_type') and record.get('matrix_type'):
            score, breakdown = self._score_matrix(
                record.get('matrix_type'),
                target_spec['matrix_type']
            )
            field_breakdowns.append(breakdown)
            total_score += breakdown.contribution
        
        # Calculate overall score as sum of weighted contributions
        # This gives proper weighting: if only analyte matches (weight 0.35), score is 0.35
        # If all fields match perfectly, score approaches 1.0
        overall_score = total_score if field_breakdowns else 0.0
        
        return overall_score, field_breakdowns
    
    def _score_analyte(self, record_analyte: str, target_analyte: str) -> tuple[float, FieldScoreBreakdown]:
        """
        Score analyte match using exact match and fuzzy matching.
        
        Args:
            record_analyte: Analyte from database record
            target_analyte: Target analyte from spec
            
        Returns:
            Tuple of (score, breakdown)
        """
        # Exact match (case-insensitive)
        if record_analyte.lower().strip() == target_analyte.lower().strip():
            score = self.EXACT_MATCH_SCORE
            details = {
                'match_type': 'exact',
                'record_value': record_analyte,
                'target_value': target_analyte
            }
        # Contains match (e.g., "Lead" matches "Lead ions")
        elif target_analyte.lower() in record_analyte.lower() or record_analyte.lower() in target_analyte.lower():
            score = self.PARTIAL_MATCH_SCORE
            details = {
                'match_type': 'contains',
                'record_value': record_analyte,
                'target_value': target_analyte
            }
        # No match
        else:
            score = self.NO_MATCH_SCORE
            details = {
                'match_type': 'none',
                'record_value': record_analyte,
                'target_value': target_analyte
            }
        
        weight = self.weights.get('analyte', 0.35)
        contribution = score * weight
        
        breakdown = FieldScoreBreakdown(
            field_name='analyte',
            score=score,
            weight=weight,
            contribution=contribution,
            details=details
        )
        
        return score, breakdown
    
    def _score_lod(self, record_lod: float, target_lod: float) -> tuple[float, FieldScoreBreakdown]:
        """
        Score LOD proximity using normalized distance.
        
        Lower LOD is better, so we score based on how close record LOD is to target.
        Score = 1.0 if exact match, decays with distance.
        
        Args:
            record_lod: LOD from database record
            target_lod: Target LOD from spec
            
        Returns:
            Tuple of (score, breakdown)
        """
        # Avoid division by zero
        if target_lod == 0:
            target_lod = 1e-10
        
        # Calculate relative difference
        relative_diff = abs(record_lod - target_lod) / target_lod
        
        # Score decays with distance: 1.0 at exact match, 0.0 at 10x difference
        if relative_diff <= 0.1:  # Within 10%
            score = self.EXACT_MATCH_SCORE
        elif relative_diff <= 0.5:  # Within 50%
            score = 0.8
        elif relative_diff <= 1.0:  # Within 100%
            score = 0.6
        elif relative_diff <= 2.0:  # Within 200%
            score = 0.4
        elif relative_diff <= 5.0:  # Within 500%
            score = 0.2
        else:  # More than 5x difference
            score = self.NO_MATCH_SCORE
        
        weight = self.weights.get('lod', 0.30)
        contribution = score * weight
        
        details = {
            'record_value': record_lod,
            'target_value': target_lod,
            'relative_difference': relative_diff,
            'note': 'Lower LOD is better'
        }
        
        breakdown = FieldScoreBreakdown(
            field_name='lod',
            score=score,
            weight=weight,
            contribution=contribution,
            details=details
        )
        
        return score, breakdown
    
    def _score_nanomaterial(self, record_material: str, target_material: str) -> tuple[float, FieldScoreBreakdown]:
        """
        Score nanomaterial match using exact and fuzzy matching.
        
        Args:
            record_material: Material from database record
            target_material: Target material from spec
            
        Returns:
            Tuple of (score, breakdown)
        """
        # Exact match (case-insensitive)
        if record_material.lower().strip() == target_material.lower().strip():
            score = self.EXACT_MATCH_SCORE
            details = {
                'match_type': 'exact',
                'record_value': record_material,
                'target_value': target_material
            }
        # Contains match (e.g., "Graphene" matches "Graphene oxide")
        elif target_material.lower() in record_material.lower() or record_material.lower() in target_material.lower():
            score = self.PARTIAL_MATCH_SCORE
            details = {
                'match_type': 'contains',
                'record_value': record_material,
                'target_value': target_material
            }
        # No match
        else:
            score = self.NO_MATCH_SCORE
            details = {
                'match_type': 'none',
                'record_value': record_material,
                'target_value': target_material
            }
        
        weight = self.weights.get('nanomaterial', 0.15)
        contribution = score * weight
        
        breakdown = FieldScoreBreakdown(
            field_name='nanomaterial',
            score=score,
            weight=weight,
            contribution=contribution,
            details=details
        )
        
        return score, breakdown
    
    def _score_transduction(self, record_transduction: Optional[str], target_transduction: str) -> tuple[float, FieldScoreBreakdown]:
        """
        Score transduction type match.
        
        Args:
            record_transduction: Transduction type from record (may be None)
            target_transduction: Target transduction type
            
        Returns:
            Tuple of (score, breakdown)
        """
        if not record_transduction:
            score = 0.0
            details = {
                'match_type': 'missing_field',
                'note': 'Transduction type not available in record'
            }
        elif record_transduction.lower().strip() == target_transduction.lower().strip():
            score = 1.0
            details = {
                'match_type': 'exact',
                'record_value': record_transduction,
                'target_value': target_transduction
            }
        else:
            score = 0.0
            details = {
                'match_type': 'none',
                'record_value': record_transduction,
                'target_value': target_transduction
            }
        
        weight = self.weights.get('transduction', 0.10)
        contribution = score * weight
        
        breakdown = FieldScoreBreakdown(
            field_name='transduction',
            score=score,
            weight=weight,
            contribution=contribution,
            details=details
        )
        
        return score, breakdown
    
    def _score_matrix(self, record_matrix: Optional[str], target_matrix: str) -> tuple[float, FieldScoreBreakdown]:
        """
        Score matrix type match.
        
        Args:
            record_matrix: Matrix type from record (may be None)
            target_matrix: Target matrix type
            
        Returns:
            Tuple of (score, breakdown)
        """
        if not record_matrix:
            score = 0.0
            details = {
                'match_type': 'missing_field',
                'note': 'Matrix type not available in record'
            }
        elif record_matrix.lower().strip() == target_matrix.lower().strip():
            score = 1.0
            details = {
                'match_type': 'exact',
                'record_value': record_matrix,
                'target_value': target_matrix
            }
        else:
            score = 0.0
            details = {
                'match_type': 'none',
                'record_value': record_matrix,
                'target_value': target_matrix
            }
        
        weight = self.weights.get('matrix', 0.10)
        contribution = score * weight
        
        breakdown = FieldScoreBreakdown(
            field_name='matrix',
            score=score,
            weight=weight,
            contribution=contribution,
            details=details
        )
        
        return score, breakdown
    
    def rank_records(
        self,
        records: List[Dict[str, Any]],
        target_spec: Dict[str, Any]
    ) -> List[tuple[float, Dict[str, Any], List[FieldScoreBreakdown]]]:
        """
        Rank multiple records against the target specification.
        
        Args:
            records: List of database records as dictionaries
            target_spec: Target specification from user
            
        Returns:
            List of tuples (score, record, field_breakdowns) sorted by score descending
        """
        scored_records = []
        
        for record in records:
            score, field_breakdowns = self.score_record(record, target_spec)
            scored_records.append((score, record, field_breakdowns))
        
        # Sort by score descending
        scored_records.sort(key=lambda x: x[0], reverse=True)
        
        return scored_records


def create_data_quality_flag(record: Dict[str, Any]) -> DataQualityFlag:
    """
    Create data quality flag from record metadata.
    
    Args:
        record: Database record as dictionary
        
    Returns:
        DataQualityFlag object
    """
    source_type = record.get('source_type', 'unknown')
    extraction_confidence = record.get('extraction_confidence')
    
    # Determine if verified based on source type and confidence
    is_verified = (
        source_type == 'literature_mined' and 
        extraction_confidence is not None and 
        extraction_confidence >= 0.7
    )
    
    notes = []
    if not is_verified:
        if source_type == 'user_contribution':
            notes.append("User-contributed data - not literature-verified")
        elif extraction_confidence and extraction_confidence < 0.7:
            notes.append(f"Low extraction confidence ({extraction_confidence:.2f})")
        else:
            notes.append("Source not verified")
    
    return DataQualityFlag(
        is_verified=is_verified,
        extraction_confidence=extraction_confidence,
        source_type=source_type,
        notes="; ".join(notes) if notes else None
    )