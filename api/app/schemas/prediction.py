from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class PredictionEnvelope(BaseModel):
    """
    Wrapper for all predicted/extracted parameters with uncertainty and metadata.
    
    For ML predictions: uses ML confidence metrics.
    For physics-based analyzer results: uses fit-quality metrics (R², residuals).
    """
    value: float | dict
    confidence_band: tuple[float, float] = Field(..., description="Lower and upper bounds of confidence interval")
    method: str = Field(..., description="Method used to extract the value")
    caveat: Optional[str] = Field(None, description="Plain-language caveat when applicable")
    is_verified: bool = Field(True, description="Whether the method has been validated against reference data")
    
    # Optional ML-specific fields (only for ML predictions)
    confidence_tier: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = None
    training_data_count: Optional[int] = None
    shap_values: Optional[dict] = None
    physical_plausibility: Optional[Literal["pass", "flagged", "fail"]] = None
    dataset_version_id: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    trained_at: Optional[datetime] = None
    
    # Optional physics-specific fields (for analyzer results)
    fit_quality: Optional[float] = Field(None, description="R² or fit quality metric")
    residual_std_error: Optional[float] = Field(None, description="Standard error of residuals")