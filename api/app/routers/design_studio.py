"""
Design Studio API endpoints for retrieval-ranking of sensor designs.

Provides:
- POST /api/v1/design-studio/search - Search and rank existing sensor designs
  by target performance specification with transparent scoring
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, Dict, Any, Union

from app.db.session import get_db
from app.db.models import SensorPerformanceRecord, User
from app.schemas.design_studio import (
    TargetSpec, DesignStudioSearchResponse, DesignStudioErrorResponse,
    RankedSearchResult, DataQualityFlag, FieldScoreBreakdown
)
from app.auth.dependencies import get_current_user

# Import ranking engine with try/except for path flexibility
try:
    from app.ml.design_studio.ranking_engine import RankingEngine, create_data_quality_flag
except ImportError:
    try:
        from ml.design_studio.ranking_engine import RankingEngine, create_data_quality_flag
    except ImportError:
        from design_studio.ranking_engine import RankingEngine, create_data_quality_flag

router = APIRouter(prefix="/api/v1/design-studio", tags=["design-studio"])


@router.post("/search", response_model=Union[DesignStudioSearchResponse, DesignStudioErrorResponse])
async def search_sensor_designs(
    target_spec: TargetSpec,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Search and rank existing sensor designs by target performance specification.
    
    Uses transparent, explainable scoring across available fields:
    - Analyte match (exact/fuzzy)
    - LOD proximity (normalized distance)
    - Nanomaterial type match
    - Transduction type match (if available)
    - Matrix type match (if available)
    
    Returns ranked results with per-field scoring breakdown for explainability.
    No ML/embeddings - pure deterministic scoring.
    
    Args:
        target_spec: Target performance specification
        db: Database session
        current_user: Authenticated user
        
    Returns:
        DesignStudioSearchResponse with ranked results and scoring metadata
    """
    try:
        # Validate target spec
        if not any([target_spec.analyte, target_spec.lod_mol_per_l, target_spec.nanomaterial]):
            # Return HTTP 200 with structured error
            return JSONResponse(
                status_code=200,
                content=DesignStudioErrorResponse(
                    success=False,
                    error="At least one search criterion (analyte, lod_mol_per_l, or nanomaterial) must be provided",
                    error_type="validation_error"
                ).model_dump()
            )
        
        # Build query filters based on provided target spec
        query = db.query(SensorPerformanceRecord)
        
        # Apply filters if specified
        if target_spec.analyte:
            # Case-insensitive partial match for analyte
            query = query.filter(
                SensorPerformanceRecord.analyte.ilike(f"%{target_spec.analyte}%")
            )
        
        if target_spec.nanomaterial:
            # Case-insensitive partial match for nanomaterial
            query = query.filter(
                SensorPerformanceRecord.nanomaterial.ilike(f"%{target_spec.nanomaterial}%")
            )
        
        # Execute query to get candidate records
        records = query.all()
        
        # Convert records to dictionaries for scoring
        record_dicts = []
        for record in records:
            record_dict = {
                'id': record.id,
                'nanomaterial': record.nanomaterial,
                'analyte': record.analyte,
                'lod_mol_per_l': record.lod_mol_per_l,
                'sensitivity_value': record.sensitivity_value,
                'sensitivity_unit': record.sensitivity_unit,
                'linear_range_low': record.linear_range_low,
                'linear_range_high': record.linear_range_high,
                'response_time_s': record.response_time_s,
                'source_type': record.source_type,
                'doi': record.doi,
                'extraction_confidence': record.extraction_confidence,
                # Note: transduction_type and matrix_type are not in current schema
                # These will be handled as missing fields in scoring
            }
            record_dicts.append(record_dict)
        
        # Initialize ranking engine
        ranking_engine = RankingEngine()
        
        # Convert target spec to dictionary
        target_dict = {
            'analyte': target_spec.analyte,
            'lod_mol_per_l': target_spec.lod_mol_per_l,
            'nanomaterial': target_spec.nanomaterial,
            'transduction_type': target_spec.transduction_type,
            'matrix_type': target_spec.matrix_type,
        }
        
        # Rank records
        ranked_results = ranking_engine.rank_records(record_dicts, target_dict)
        
        # Filter out zero-score results (no meaningful match)
        meaningful_results = [r for r in ranked_results if r[0] > 0]
        
        # Determine if we have sparse data
        low_data_flag = len(meaningful_results) < target_spec.max_results
        
        # Build response objects
        ranked_search_results = []
        for rank, (score, record_dict, field_breakdowns) in enumerate(meaningful_results[:target_spec.max_results], start=1):
            # Create data quality flag
            data_quality = create_data_quality_flag(record_dict)
            
            # Convert field breakdowns to schema objects
            field_breakdown_objs = []
            for fb in field_breakdowns:
                if hasattr(fb, 'model_dump'):
                    field_breakdown_objs.append(FieldScoreBreakdown(**fb.model_dump()))
                elif hasattr(fb, 'dict'):
                    field_breakdown_objs.append(FieldScoreBreakdown(**fb.dict()))
                else:
                    field_breakdown_objs.append(fb)
            
            # Create ranked result
            ranked_result = RankedSearchResult(
                id=record_dict['id'],
                nanomaterial=record_dict['nanomaterial'],
                analyte=record_dict['analyte'],
                lod_mol_per_l=record_dict['lod_mol_per_l'],
                sensitivity_value=record_dict['sensitivity_value'],
                sensitivity_unit=record_dict['sensitivity_unit'],
                linear_range_low=record_dict['linear_range_low'],
                linear_range_high=record_dict['linear_range_high'],
                response_time_s=record_dict['response_time_s'],
                source_type=record_dict['source_type'],
                doi=record_dict['doi'],
                overall_score=score,
                rank=rank,
                field_breakdown=field_breakdown_objs,
                data_quality=data_quality
            )
            ranked_search_results.append(ranked_result)
        
        # Build search metadata
        search_metadata = {
            'weights_used': ranking_engine.weights,
            'total_candidates': len(records),
            'meaningful_matches': len(meaningful_results),
            'fields_scored': len(field_breakdown_objs) if 'field_breakdown_objs' in locals() and field_breakdown_objs else 0,
            'target_spec': target_dict
        }
        
        return DesignStudioSearchResponse(
            success=True,
            results=ranked_search_results,
            total_matches=len(meaningful_results),
            low_data_flag=low_data_flag,
            search_metadata=search_metadata
        )
        
    except Exception as e:
        # Handle unexpected errors with structured error response
        return DesignStudioErrorResponse(
            success=False,
            error=f"Search failed: {str(e)}",
            error_type="search_error"
        )