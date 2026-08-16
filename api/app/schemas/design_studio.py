"""
Design Studio schemas for retrieval-ranking interface.

Supports transparent scoring and explainability for sensor design search.
"""

from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, UUID4
from uuid import UUID


# Target specification input
class TargetSpec(BaseModel):
    """Target performance specification for sensor design search."""
    
    analyte: Optional[str] = Field(None, description="Target analyte to detect")
    lod_mol_per_l: Optional[float] = Field(None, gt=0, description="Target limit of detection in mol/L")
    lod_unit: Optional[str] = Field("mol/L", description="Unit for LOD (e.g., mol/L, ng/mL, ppb)")
    matrix_type: Optional[str] = Field(None, description="Matrix type (blood, wastewater, soil, etc.)")
    transduction_type: Optional[str] = Field(None, description="Transduction type (electrochemical, optical, etc.)")
    nanomaterial: Optional[str] = Field(None, description="Preferred nanomaterial type")
    max_results: Optional[int] = Field(10, ge=1, le=100, description="Maximum number of results to return")


# Per-field scoring breakdown for explainability
class FieldScoreBreakdown(BaseModel):
    """Breakdown of scoring contribution per field."""
    
    field_name: str = Field(..., description="Name of the field (e.g., 'analyte', 'lod')")
    score: float = Field(..., ge=0, le=1, description="Score for this field (0-1)")
    weight: float = Field(..., ge=0, le=1, description="Weight applied to this field")
    contribution: float = Field(..., ge=0, description="Weighted contribution to overall score")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details (e.g., matched value, distance)")


# Data quality flag
class DataQualityFlag(BaseModel):
    """Data quality information for a matched record."""
    
    is_verified: bool = Field(..., description="Whether the record is verified")
    extraction_confidence: Optional[float] = Field(None, description="Extraction confidence score if available")
    source_type: str = Field(..., description="Source type (literature_mined, user_contribution, api_sync)")
    notes: Optional[str] = Field(None, description="Additional quality notes")


# Ranked search result
class RankedSearchResult(BaseModel):
    """Single ranked search result with explainability data."""
    
    id: UUID4 = Field(..., description="Record ID")
    nanomaterial: str = Field(..., description="Nanomaterial used")
    analyte: str = Field(..., description="Analyte detected")
    lod_mol_per_l: Optional[float] = Field(None, description="Limit of detection in mol/L")
    sensitivity_value: Optional[float] = Field(None, description="Sensitivity value")
    sensitivity_unit: Optional[str] = Field(None, description="Unit for sensitivity")
    linear_range_low: Optional[float] = Field(None, description="Lower bound of linear range")
    linear_range_high: Optional[float] = Field(None, description="Upper bound of linear range")
    response_time_s: Optional[float] = Field(None, description="Response time in seconds")
    source_type: str = Field(..., description="Source of the data")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    
    # Ranking information
    overall_score: float = Field(..., ge=0, le=1, description="Overall match score (0-1)")
    rank: int = Field(..., ge=1, description="Rank position")
    
    # Explainability data
    field_breakdown: list[FieldScoreBreakdown] = Field(..., description="Per-field scoring breakdown")
    data_quality: DataQualityFlag = Field(..., description="Data quality information")


# Search response
class DesignStudioSearchResponse(BaseModel):
    """Response from design studio search endpoint."""
    
    success: bool = Field(..., description="Whether the search was successful")
    results: list[RankedSearchResult] = Field(..., description="Ranked search results")
    total_matches: int = Field(..., ge=0, description="Total number of matches found")
    low_data_flag: bool = Field(..., description="True if fewer results than requested due to sparse data")
    search_metadata: Dict[str, Any] = Field(..., description="Metadata about the search (e.g., scoring weights used)")


# Error response (following analyzer module pattern)
class DesignStudioErrorResponse(BaseModel):
    """Structured error response for design studio endpoints."""
    
    success: bool = Field(default=False, description="Always False for error responses")
    error: str = Field(..., description="Error message")
    error_type: Literal["validation_error", "search_error", "database_error"] = Field(..., description="Type of error")
