from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from uuid import UUID
from typing import Optional, Literal
from datetime import datetime
import json

from app.db.session import get_db
from app.db.models import (
    MaterialRecord, ToxicityRecord, SensorPerformanceRecord,
    RecordVersion, RecordReview, User
)
from app.schemas.records import (
    MaterialRecordCreate, MaterialRecordUpdate, MaterialRecordOut,
    ToxicityRecordCreate, ToxicityRecordUpdate, ToxicityRecordOut,
    SensorPerformanceRecordCreate, SensorPerformanceRecordUpdate, SensorPerformanceRecordOut,
    RecordVersionOut, RecordReviewCreate, RecordReviewUpdate, RecordReviewOut,
    MaterialRecordListResponse, ToxicityRecordListResponse, SensorPerformanceRecordListResponse,
    DataHealthSummary
)
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/records", tags=["records"])


# Helper functions for versioning
def create_record_version(db: Session, record_type: str, record_id: UUID, data_snapshot: dict, edited_by: Optional[UUID]):
    """Create a new version entry for a record."""
    # Get the current max version number for this record
    max_version = db.query(RecordVersion).filter(
        RecordVersion.record_type == record_type,
        RecordVersion.record_id == record_id
    ).order_by(RecordVersion.version_number.desc()).first()
    
    version_number = 1 if max_version is None else max_version.version_number + 1
    
    # Clean the data snapshot to remove SQLAlchemy internal attributes and convert non-serializable types
    clean_snapshot = {}
    for key, value in data_snapshot.items():
        if not key.startswith('_sa_'):
            # Convert UUID to string for JSON serialization
            if hasattr(value, '__class__') and value.__class__.__name__ == 'UUID':
                clean_snapshot[key] = str(value)
            # Convert datetime to ISO format string
            elif isinstance(value, datetime):
                clean_snapshot[key] = value.isoformat()
            else:
                clean_snapshot[key] = value
    
    new_version = RecordVersion(
        record_type=record_type,
        record_id=record_id,
        version_number=version_number,
        data_snapshot=clean_snapshot,
        edited_by=edited_by
    )
    db.add(new_version)
    db.commit()
    db.refresh(new_version)
    return new_version


def create_record_review(db: Session, record_type: str, record_id: UUID, status: str = "pending"):
    """Create a review entry for a record."""
    existing_review = db.query(RecordReview).filter(
        RecordReview.record_type == record_type,
        RecordReview.record_id == record_id
    ).first()
    
    if existing_review:
        # Update existing review to pending
        existing_review.status = status
        existing_review.reviewed_at = None
        existing_review.notes = None
        db.commit()
        return existing_review
    
    new_review = RecordReview(
        record_type=record_type,
        record_id=record_id,
        status=status
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    return new_review


# Duplicate detection helper
def check_duplicate_material(db: Session, doi: Optional[str], name: str, material_type: str) -> Optional[MaterialRecord]:
    """Check for duplicate material records based on DOI + material type/name combination."""
    if doi:
        # Check by DOI first
        duplicate = db.query(MaterialRecord).filter(
            MaterialRecord.doi == doi,
            MaterialRecord.material_type == material_type
        ).first()
        if duplicate:
            return duplicate
    
    # Check by name + material type if no DOI or no DOI match
    duplicate = db.query(MaterialRecord).filter(
        MaterialRecord.name == name,
        MaterialRecord.material_type == material_type
    ).first()
    return duplicate


def check_duplicate_sensor(db: Session, doi: Optional[str], nanomaterial: str, analyte: str) -> Optional[SensorPerformanceRecord]:
    """Check for duplicate sensor performance records based on DOI + nanomaterial/analyte combination."""
    if doi:
        # Check by DOI first
        duplicate = db.query(SensorPerformanceRecord).filter(
            SensorPerformanceRecord.doi == doi,
            SensorPerformanceRecord.nanomaterial == nanomaterial,
            SensorPerformanceRecord.analyte == analyte
        ).first()
        if duplicate:
            return duplicate
    
    # Check by nanomaterial + analyte if no DOI or no DOI match
    duplicate = db.query(SensorPerformanceRecord).filter(
        SensorPerformanceRecord.nanomaterial == nanomaterial,
        SensorPerformanceRecord.analyte == analyte
    ).first()
    return duplicate


# MATERIAL RECORDS
@router.post("/materials", response_model=MaterialRecordOut, status_code=status.HTTP_201_CREATED)
def create_material_record(
    record: MaterialRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check for duplicates
    duplicate = check_duplicate_material(db, record.doi, record.name, record.material_type)
    if duplicate:
        conflict_info = f"DOI: {record.doi}" if record.doi else f"Name: {record.name}, Type: {record.material_type}"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate material record found. A record with {conflict_info} already exists (ID: {duplicate.id})."
        )
    
    # Create new record
    new_record = MaterialRecord(
        **record.model_dump(exclude_unset=True),
        contributor_id=current_user.id if record.contributor_id is None else record.contributor_id
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    # Create initial version
    create_record_version(
        db, "material_record", new_record.id,
        new_record.__dict__.copy(), current_user.id
    )
    
    # Create pending review
    create_record_review(db, "material_record", new_record.id, "pending")
    
    return new_record


@router.get("/materials/{record_id}", response_model=MaterialRecordOut)
def get_material_record(record_id: UUID, db: Session = Depends(get_db)):
    record = db.query(MaterialRecord).filter(MaterialRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material record not found")
    return record


@router.put("/materials/{record_id}", response_model=MaterialRecordOut)
def update_material_record(
    record_id: UUID,
    record_update: MaterialRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record = db.query(MaterialRecord).filter(MaterialRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material record not found")
    
    # Store old data for versioning
    old_data = record.__dict__.copy()
    
    # Update record
    for field, value in record_update.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    
    record.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(record)
    
    # Create new version
    create_record_version(
        db, "material_record", record_id,
        old_data, current_user.id
    )
    
    # Reset review to pending
    create_record_review(db, "material_record", record_id, "pending")
    
    return record


@router.delete("/materials/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record = db.query(MaterialRecord).filter(MaterialRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material record not found")
    
    # Soft delete by setting a flag or just delete for now
    # For this implementation, we'll do hard delete but could add soft delete later
    db.delete(record)
    
    # Clean up versions and reviews
    db.query(RecordVersion).filter(
        RecordVersion.record_type == "material_record",
        RecordVersion.record_id == record_id
    ).delete()
    
    db.query(RecordReview).filter(
        RecordReview.record_type == "material_record",
        RecordReview.record_id == record_id
    ).delete()
    
    db.commit()
    return None


@router.get("/materials", response_model=MaterialRecordListResponse)
def list_material_records(
    status: Optional[Literal["pending", "approved", "rejected"]] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(MaterialRecord)
    
    if status:
        # Filter by review status
        query = query.join(
            RecordReview,
            (MaterialRecord.id == RecordReview.record_id) & 
            (RecordReview.record_type == "material_record")
        ).filter(
            RecordReview.status == status
        )
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return MaterialRecordListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


# TOXICITY RECORDS
@router.post("/toxicity", response_model=ToxicityRecordOut, status_code=status.HTTP_201_CREATED)
def create_toxicity_record(
    record: ToxicityRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify material exists
    material = db.query(MaterialRecord).filter(MaterialRecord.id == record.material_id).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Material record not found"
        )
    
    # Create new record
    new_record = ToxicityRecord(**record.model_dump())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    # Create initial version
    create_record_version(
        db, "toxicity_record", new_record.id,
        new_record.__dict__.copy(), current_user.id
    )
    
    # Create pending review
    create_record_review(db, "toxicity_record", new_record.id, "pending")
    
    return new_record


@router.get("/toxicity/{record_id}", response_model=ToxicityRecordOut)
def get_toxicity_record(record_id: UUID, db: Session = Depends(get_db)):
    record = db.query(ToxicityRecord).filter(ToxicityRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Toxicity record not found")
    return record


@router.put("/toxicity/{record_id}", response_model=ToxicityRecordOut)
def update_toxicity_record(
    record_id: UUID,
    record_update: ToxicityRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record = db.query(ToxicityRecord).filter(ToxicityRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Toxicity record not found")
    
    # Store old data for versioning
    old_data = record.__dict__.copy()
    
    # Update record
    for field, value in record_update.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    
    db.commit()
    db.refresh(record)
    
    # Create new version
    create_record_version(
        db, "toxicity_record", record_id,
        old_data, current_user.id
    )
    
    # Reset review to pending
    create_record_review(db, "toxicity_record", record_id, "pending")
    
    return record


@router.delete("/toxicity/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_toxicity_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record = db.query(ToxicityRecord).filter(ToxicityRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Toxicity record not found")
    
    db.delete(record)
    
    # Clean up versions and reviews
    db.query(RecordVersion).filter(
        RecordVersion.record_type == "toxicity_record",
        RecordVersion.record_id == record_id
    ).delete()
    
    db.query(RecordReview).filter(
        RecordReview.record_type == "toxicity_record",
        RecordReview.record_id == record_id
    ).delete()
    
    db.commit()
    return None


@router.get("/toxicity", response_model=ToxicityRecordListResponse)
def list_toxicity_records(
    status: Optional[Literal["pending", "approved", "rejected"]] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(ToxicityRecord)
    
    if status:
        # Filter by review status
        query = query.join(
            RecordReview,
            (ToxicityRecord.id == RecordReview.record_id) & 
            (RecordReview.record_type == "toxicity_record")
        ).filter(
            RecordReview.status == status
        )
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return ToxicityRecordListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


# SENSOR PERFORMANCE RECORDS
@router.post("/sensor-performance", response_model=SensorPerformanceRecordOut, status_code=status.HTTP_201_CREATED)
def create_sensor_performance_record(
    record: SensorPerformanceRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check for duplicates
    duplicate = check_duplicate_sensor(db, record.doi, record.nanomaterial, record.analyte)
    if duplicate:
        conflict_info = f"DOI: {record.doi}" if record.doi else f"Material: {record.nanomaterial}, Analyte: {record.analyte}"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate sensor performance record found. A record with {conflict_info} already exists (ID: {duplicate.id})."
        )
    
    # Create new record
    new_record = SensorPerformanceRecord(
        **record.model_dump(exclude_unset=True),
        contributor_id=current_user.id if record.contributor_id is None else record.contributor_id
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    
    # Create initial version
    create_record_version(
        db, "sensor_performance_record", new_record.id,
        new_record.__dict__.copy(), current_user.id
    )
    
    # Create pending review
    create_record_review(db, "sensor_performance_record", new_record.id, "pending")
    
    return new_record


@router.get("/sensor-performance/{record_id}", response_model=SensorPerformanceRecordOut)
def get_sensor_performance_record(record_id: UUID, db: Session = Depends(get_db)):
    record = db.query(SensorPerformanceRecord).filter(SensorPerformanceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor performance record not found")
    return record


@router.put("/sensor-performance/{record_id}", response_model=SensorPerformanceRecordOut)
def update_sensor_performance_record(
    record_id: UUID,
    record_update: SensorPerformanceRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record = db.query(SensorPerformanceRecord).filter(SensorPerformanceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor performance record not found")
    
    # Store old data for versioning
    old_data = record.__dict__.copy()
    
    # Update record
    for field, value in record_update.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    
    db.commit()
    db.refresh(record)
    
    # Create new version
    create_record_version(
        db, "sensor_performance_record", record_id,
        old_data, current_user.id
    )
    
    # Reset review to pending
    create_record_review(db, "sensor_performance_record", record_id, "pending")
    
    return record


@router.delete("/sensor-performance/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sensor_performance_record(
    record_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    record = db.query(SensorPerformanceRecord).filter(SensorPerformanceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor performance record not found")
    
    db.delete(record)
    
    # Clean up versions and reviews
    db.query(RecordVersion).filter(
        RecordVersion.record_type == "sensor_performance_record",
        RecordVersion.record_id == record_id
    ).delete()
    
    db.query(RecordReview).filter(
        RecordReview.record_type == "sensor_performance_record",
        RecordReview.record_id == record_id
    ).delete()
    
    db.commit()
    return None


@router.get("/sensor-performance", response_model=SensorPerformanceRecordListResponse)
def list_sensor_performance_records(
    status: Optional[Literal["pending", "approved", "rejected"]] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    query = db.query(SensorPerformanceRecord)
    
    if status:
        # Filter by review status
        query = query.join(
            RecordReview,
            (SensorPerformanceRecord.id == RecordReview.record_id) & 
            (RecordReview.record_type == "sensor_performance_record")
        ).filter(
            RecordReview.status == status
        )
    
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    
    return SensorPerformanceRecordListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit
    )


# VERSION HISTORY
@router.get("/{record_type}/{record_id}/versions", response_model=list[RecordVersionOut])
def get_record_versions(
    record_type: Literal["material_record", "toxicity_record", "sensor_performance_record"],
    record_id: UUID,
    db: Session = Depends(get_db)
):
    versions = db.query(RecordVersion).filter(
        RecordVersion.record_type == record_type,
        RecordVersion.record_id == record_id
    ).order_by(RecordVersion.version_number.asc()).all()
    
    return versions


# REVIEW WORKFLOW
@router.post("/reviews", response_model=RecordReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(
    review: RecordReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if record exists based on type
    if review.record_type == "material_record":
        record = db.query(MaterialRecord).filter(MaterialRecord.id == review.record_id).first()
    elif review.record_type == "toxicity_record":
        record = db.query(ToxicityRecord).filter(ToxicityRecord.id == review.record_id).first()
    elif review.record_type == "sensor_performance_record":
        record = db.query(SensorPerformanceRecord).filter(SensorPerformanceRecord.id == review.record_id).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid record type"
        )
    
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found"
        )
    
    # Check if review already exists
    existing_review = db.query(RecordReview).filter(
        RecordReview.record_type == review.record_type,
        RecordReview.record_id == review.record_id
    ).first()
    
    if existing_review:
        # Update existing review
        existing_review.status = review.status
        existing_review.notes = review.notes
        existing_review.reviewer_id = current_user.id if review.reviewer_id is None else review.reviewer_id
        existing_review.reviewed_at = datetime.utcnow()
        db.commit()
        db.refresh(existing_review)
        return existing_review
    
    # Create new review
    new_review = RecordReview(
        **review.model_dump(exclude_unset=True),
        reviewer_id=current_user.id if review.reviewer_id is None else review.reviewer_id,
        reviewed_at=datetime.utcnow() if review.status != "pending" else None
    )
    db.add(new_review)
    db.commit()
    db.refresh(new_review)
    
    return new_review


@router.put("/reviews/{record_type}/{record_id}", response_model=RecordReviewOut)
def update_review(
    record_type: Literal["material_record", "toxicity_record", "sensor_performance_record"],
    record_id: UUID,
    review_update: RecordReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    review = db.query(RecordReview).filter(
        RecordReview.record_type == record_type,
        RecordReview.record_id == record_id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Update review
    review.status = review_update.status
    review.notes = review_update.notes
    review.reviewer_id = current_user.id
    review.reviewed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(review)
    
    return review


@router.get("/reviews/{record_type}/{record_id}", response_model=RecordReviewOut)
def get_review(
    record_type: Literal["material_record", "toxicity_record", "sensor_performance_record"],
    record_id: UUID,
    db: Session = Depends(get_db)
):
    review = db.query(RecordReview).filter(
        RecordReview.record_type == record_type,
        RecordReview.record_id == record_id
    ).first()
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    return review


# TRAINABLE DATASET (approved records only)
@router.get("/trainable", response_model=dict)
def get_trainable_dataset(
    record_type: Optional[Literal["material", "toxicity", "sensor_performance"]] = Query(None),
    db: Session = Depends(get_db)
):
    """Get only approved records for ML training."""
    result = {}
    
    if record_type is None or record_type == "material":
        material_records = db.query(MaterialRecord).join(
            RecordReview,
            (MaterialRecord.id == RecordReview.record_id) & 
            (RecordReview.record_type == "material_record")
        ).filter(
            RecordReview.status == "approved"
        ).all()
        result["materials"] = [MaterialRecordOut.model_validate(r) for r in material_records]
    
    if record_type is None or record_type == "toxicity":
        toxicity_records = db.query(ToxicityRecord).join(
            RecordReview,
            (ToxicityRecord.id == RecordReview.record_id) & 
            (RecordReview.record_type == "toxicity_record")
        ).filter(
            RecordReview.status == "approved"
        ).all()
        result["toxicity"] = [ToxicityRecordOut.model_validate(r) for r in toxicity_records]
    
    if record_type is None or record_type == "sensor_performance":
        sensor_records = db.query(SensorPerformanceRecord).join(
            RecordReview,
            (SensorPerformanceRecord.id == RecordReview.record_id) & 
            (RecordReview.record_type == "sensor_performance_record")
        ).filter(
            RecordReview.status == "approved"
        ).all()
        result["sensor_performance"] = [SensorPerformanceRecordOut.model_validate(r) for r in sensor_records]
    
    return result


# DATA HEALTH SUMMARY
@router.get("/health/summary", response_model=DataHealthSummary)
def get_data_health_summary(db: Session = Depends(get_db)):
    """Get summary statistics about data health."""
    material_count = db.query(MaterialRecord).count()
    toxicity_count = db.query(ToxicityRecord).count()
    sensor_count = db.query(SensorPerformanceRecord).count()
    
    pending_count = db.query(RecordReview).filter(RecordReview.status == "pending").count()
    approved_count = db.query(RecordReview).filter(RecordReview.status == "approved").count()
    rejected_count = db.query(RecordReview).filter(RecordReview.status == "rejected").count()
    
    return DataHealthSummary(
        material_records=material_count,
        toxicity_records=toxicity_count,
        sensor_performance_records=sensor_count,
        pending_reviews=pending_count,
        approved_records=approved_count,
        rejected_records=rejected_count
    )
