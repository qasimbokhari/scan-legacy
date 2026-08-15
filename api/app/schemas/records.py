from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, UUID4, ConfigDict
from uuid import UUID


# Base schemas for Material Records
class MaterialRecordBase(BaseModel):
    name: str = Field(..., min_length=1, description="Material name")
    material_type: str = Field(..., min_length=1, description="Type of material")
    core_size_nm: Optional[float] = Field(None, ge=0, description="Core size in nanometers")
    zeta_potential_mv: Optional[float] = Field(None, description="Zeta potential in millivolts")
    zeta_potential_flagged: Optional[int] = Field(None, ge=0, le=1, description="1 if flagged as implausible, 0 otherwise")
    surface_area_m2g: Optional[float] = Field(None, ge=0, description="Surface area in m²/g")
    coating: Optional[str] = Field(None, description="Coating material")
    source_type: Literal["literature_mined", "user_contribution", "api_sync"] = Field(..., description="Source of the data")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    extraction_confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score for data extraction")


class MaterialRecordCreate(MaterialRecordBase):
    contributor_id: Optional[UUID4] = None


class MaterialRecordUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    material_type: Optional[str] = Field(None, min_length=1)
    core_size_nm: Optional[float] = Field(None, ge=0)
    zeta_potential_mv: Optional[float] = Field(None)
    zeta_potential_flagged: Optional[int] = Field(None, ge=0, le=1)
    surface_area_m2g: Optional[float] = Field(None, ge=0)
    coating: Optional[str] = None
    source_type: Optional[Literal["literature_mined", "user_contribution", "api_sync"]] = None
    doi: Optional[str] = None
    extraction_confidence: Optional[float] = Field(None, ge=0, le=1)


class MaterialRecordOut(MaterialRecordBase):
    id: UUID4
    contributor_id: Optional[UUID4] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Base schemas for Toxicity Records
class ToxicityRecordBase(BaseModel):
    material_id: UUID4 = Field(..., description="ID of the associated material record")
    ic50: Optional[float] = Field(None, gt=0, description="IC50 value")
    ec50: Optional[float] = Field(None, gt=0, description="EC50 value")
    pec50: Optional[float] = Field(None, description="pEC50 value")
    cell_line: Optional[str] = Field(None, description="Cell line used")
    exposure_time_h: Optional[float] = Field(None, gt=0, description="Exposure time in hours")


class ToxicityRecordCreate(ToxicityRecordBase):
    pass


class ToxicityRecordUpdate(BaseModel):
    material_id: Optional[UUID4] = None
    ic50: Optional[float] = Field(None, gt=0)
    ec50: Optional[float] = Field(None, gt=0)
    pec50: Optional[float] = None
    cell_line: Optional[str] = None
    exposure_time_h: Optional[float] = Field(None, gt=0)


class ToxicityRecordOut(ToxicityRecordBase):
    id: UUID4
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Base schemas for Sensor Performance Records
class SensorPerformanceRecordBase(BaseModel):
    nanomaterial: str = Field(..., min_length=1, description="Nanomaterial used")
    analyte: str = Field(..., min_length=1, description="Analyte detected")
    lod_mol_per_l: Optional[float] = Field(None, gt=0, description="Limit of detection in mol/L")
    sensitivity_value: Optional[float] = Field(None, description="Sensitivity value")
    sensitivity_unit: Optional[str] = Field(None, description="Unit for sensitivity")
    linear_range_low: Optional[float] = Field(None, description="Lower bound of linear range")
    linear_range_high: Optional[float] = Field(None, description="Upper bound of linear range")
    response_time_s: Optional[float] = Field(None, gt=0, description="Response time in seconds")
    source_type: Literal["literature_mined", "user_contribution", "api_sync"] = Field(..., description="Source of the data")
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    extraction_confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score for data extraction")


class SensorPerformanceRecordCreate(SensorPerformanceRecordBase):
    contributor_id: Optional[UUID4] = None


class SensorPerformanceRecordUpdate(BaseModel):
    nanomaterial: Optional[str] = Field(None, min_length=1)
    analyte: Optional[str] = Field(None, min_length=1)
    lod_mol_per_l: Optional[float] = Field(None, gt=0)
    sensitivity_value: Optional[float] = None
    sensitivity_unit: Optional[str] = None
    linear_range_low: Optional[float] = None
    linear_range_high: Optional[float] = None
    response_time_s: Optional[float] = Field(None, gt=0)
    source_type: Optional[Literal["literature_mined", "user_contribution", "api_sync"]] = None
    doi: Optional[str] = None
    extraction_confidence: Optional[float] = Field(None, ge=0, le=1)


class SensorPerformanceRecordOut(SensorPerformanceRecordBase):
    id: UUID4
    contributor_id: Optional[UUID4] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Record Version schemas
class RecordVersionOut(BaseModel):
    id: UUID4
    record_type: str
    record_id: UUID4
    version_number: int
    data_snapshot: dict
    edited_by: Optional[UUID4] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Record Review schemas
class RecordReviewBase(BaseModel):
    record_type: str = Field(..., description="Type of record being reviewed")
    record_id: UUID4 = Field(..., description="ID of the record being reviewed")
    status: Literal["pending", "approved", "rejected"] = Field(..., description="Review status")
    notes: Optional[str] = Field(None, description="Reviewer notes")


class RecordReviewCreate(RecordReviewBase):
    reviewer_id: Optional[UUID4] = None


class RecordReviewUpdate(BaseModel):
    status: Literal["approved", "rejected"] = Field(..., description="Review status")
    notes: Optional[str] = Field(None, description="Reviewer notes")


class RecordReviewOut(RecordReviewBase):
    id: UUID4
    reviewer_id: Optional[UUID4] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Query parameters for filtering
class RecordQueryParams(BaseModel):
    status: Optional[Literal["pending", "approved", "rejected"]] = None
    record_type: Optional[Literal["material", "toxicity", "sensor_performance"]] = None
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)


# Response schemas for list endpoints
class MaterialRecordListResponse(BaseModel):
    items: list[MaterialRecordOut]
    total: int
    skip: int
    limit: int


class ToxicityRecordListResponse(BaseModel):
    items: list[ToxicityRecordOut]
    total: int
    skip: int
    limit: int


class SensorPerformanceRecordListResponse(BaseModel):
    items: list[SensorPerformanceRecordOut]
    total: int
    skip: int
    limit: int


# Data health summary
class DataHealthSummary(BaseModel):
    material_records: int
    toxicity_records: int
    sensor_performance_records: int
    pending_reviews: int
    approved_records: int
    rejected_records: int
