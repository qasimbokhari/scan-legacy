from datetime import datetime
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, UUID4
from uuid import UUID
from app.schemas.prediction import PredictionEnvelope


# CV/LSV Analysis Schemas
class CVLSVAnalysisBase(BaseModel):
    analysis_type: Literal["cv-lsv"] = Field(default="cv-lsv")
    scan_rate_v_s: Optional[float] = Field(None, gt=0, description="Scan rate in V/s")
    electrode_area_cm2: Optional[float] = Field(None, gt=0, description="Electrode area in cm²")
    concentration_mol_cm3: Optional[float] = Field(None, gt=0, description="Concentration in mol/cm³")
    n_electrons: Optional[int] = Field(None, gt=0, description="Number of electrons transferred")
    temperature_k: Optional[float] = Field(None, gt=0, description="Temperature in Kelvin")


class CVLSVAnalysisCreate(CVLSVAnalysisBase):
    pass


class CVLSVAnalysisOut(CVLSVAnalysisBase):
    id: UUID4
    uploaded_by: UUID4
    created_at: datetime
    
    model_config = {"from_attributes": True}


# EIS Analysis Schemas
class EISAnalysisBase(BaseModel):
    analysis_type: Literal["eis"] = Field(default="eis")


class EISAnalysisCreate(EISAnalysisBase):
    pass


class EISAnalysisOut(EISAnalysisBase):
    id: UUID4
    uploaded_by: UUID4
    created_at: datetime
    
    model_config = {"from_attributes": True}


# Response schemas for analyzer results
class AnalyzerResultOut(BaseModel):
    id: UUID4
    analysis_type: Literal["cv-lsv", "eis"]
    raw_data: dict
    processed_results: dict
    fit_metadata: Optional[dict] = None
    uploaded_by: UUID4
    created_at: datetime
    scan_rate_v_s: Optional[float] = None
    electrode_area_cm2: Optional[float] = None
    concentration_mol_cm3: Optional[float] = None
    n_electrons: Optional[int] = None
    temperature_k: Optional[float] = None
    
    model_config = {"from_attributes": True}


# Error response schema
class AnalyzerErrorResponse(BaseModel):
    success: bool = Field(default=False)
    error: str = Field(..., description="Error message")
    error_type: Literal["parse_error", "fit_error", "validation_error"] = Field(..., description="Type of error")