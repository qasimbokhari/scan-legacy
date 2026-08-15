import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4, UUID
from app.main import app
from app.db.session import get_db
from app.db.models import Base, MaterialRecord, ToxicityRecord, SensorPerformanceRecord, RecordVersion, RecordReview, User

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_records.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """Create a test user and return auth headers."""
    # Register user
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    
    # Login
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


def test_versioning_creates_new_rows_not_overwrites(db, client, auth_headers):
    """Test that editing a record creates a new version row instead of overwriting."""
    # Create a material record
    create_response = client.post("/records/materials", 
        json={
            "name": "Test Material",
            "material_type": "Graphene",
            "core_size_nm": 10.0,
            "source_type": "user_contribution"
        },
        headers=auth_headers
    )
    assert create_response.status_code == 201
    record_id_str = create_response.json()["id"]
    record_id = UUID(record_id_str)
    
    # Check initial version count
    initial_versions = db.query(RecordVersion).filter(
        RecordVersion.record_type == "material_record",
        RecordVersion.record_id == record_id
    ).count()
    assert initial_versions == 1
    
    # Update the record
    update_response = client.put(f"/records/materials/{record_id_str}",
        json={
            "core_size_nm": 15.0
        },
        headers=auth_headers
    )
    assert update_response.status_code == 200
    
    # Check that version count increased
    final_versions = db.query(RecordVersion).filter(
        RecordVersion.record_type == "material_record",
        RecordVersion.record_id == record_id
    ).count()
    assert final_versions == 2
    
    # Verify the versions have different data
    versions = db.query(RecordVersion).filter(
        RecordVersion.record_type == "material_record",
        RecordVersion.record_id == record_id
    ).order_by(RecordVersion.version_number.asc()).all()
    
    assert versions[0].version_number == 1
    assert versions[1].version_number == 2
    assert versions[0].data_snapshot["core_size_nm"] == 10.0
    assert versions[1].data_snapshot["core_size_nm"] == 10.0  # Should contain old data
    
    # Verify current record has updated value
    updated_record = db.query(MaterialRecord).filter(MaterialRecord.id == record_id).first()
    assert updated_record.core_size_nm == 15.0


def test_unreviewed_records_excluded_from_trainable_query(db, client, auth_headers):
    """Test that unreviewed/pending records are excluded from the trainable dataset query."""
    # Create a material record (will be pending by default)
    create_response = client.post("/records/materials",
        json={
            "name": "Test Material",
            "material_type": "Graphene",
            "source_type": "user_contribution"
        },
        headers=auth_headers
    )
    assert create_response.status_code == 201
    record_id_str = create_response.json()["id"]
    record_id = UUID(record_id_str)
    
    # Verify it's pending
    review = db.query(RecordReview).filter(
        RecordReview.record_type == "material_record",
        RecordReview.record_id == record_id
    ).first()
    assert review.status == "pending"
    
    # Get trainable dataset - should be empty
    trainable_response = client.get("/records/trainable?record_type=material", headers=auth_headers)
    assert trainable_response.status_code == 200
    trainable_data = trainable_response.json()
    assert len(trainable_data["materials"]) == 0
    
    # Approve the record
    approve_response = client.put(f"/records/reviews/material_record/{record_id_str}",
        json={
            "status": "approved",
            "notes": "Looks good"
        },
        headers=auth_headers
    )
    assert approve_response.status_code == 200
    
    # Get trainable dataset again - should now include the record
    trainable_response = client.get("/records/trainable?record_type=material", headers=auth_headers)
    assert trainable_response.status_code == 200
    trainable_data = trainable_response.json()
    assert len(trainable_data["materials"]) == 1
    assert trainable_data["materials"][0]["id"] == record_id_str


def test_duplicate_doi_submission_rejected_with_clear_message(db, client, auth_headers):
    """Test that duplicate DOI submission is rejected with a clear, specific error message."""
    doi = "10.1234/test.doi.12345"
    
    # Create first material record with DOI
    first_response = client.post("/records/materials",
        json={
            "name": "Test Material",
            "material_type": "Graphene",
            "doi": doi,
            "source_type": "literature_mined"
        },
        headers=auth_headers
    )
    assert first_response.status_code == 201
    first_record_id_str = first_response.json()["id"]
    
    # Try to create duplicate with same DOI
    duplicate_response = client.post("/records/materials",
        json={
            "name": "Different Name",
            "material_type": "Graphene",
            "doi": doi,
            "source_type": "user_contribution"
        },
        headers=auth_headers
    )
    
    # Should be rejected with 409 Conflict
    assert duplicate_response.status_code == 409
    error_detail = duplicate_response.json()["detail"]
    
    # Should contain clear error message identifying the conflict
    assert "Duplicate material record found" in error_detail
    assert doi in error_detail
    assert first_record_id_str in error_detail
    
    # Test sensor performance duplicate detection
    sensor_response = client.post("/records/sensor-performance",
        json={
            "nanomaterial": "Graphene",
            "analyte": "Glucose",
            "doi": doi,
            "source_type": "literature_mined"
        },
        headers=auth_headers
    )
    assert sensor_response.status_code == 201
    sensor_record_id_str = sensor_response.json()["id"]
    
    # Try duplicate sensor record
    duplicate_sensor_response = client.post("/records/sensor-performance",
        json={
            "nanomaterial": "Graphene",
            "analyte": "Glucose",
            "doi": doi,
            "source_type": "user_contribution"
        },
        headers=auth_headers
    )
    
    assert duplicate_sensor_response.status_code == 409
    sensor_error_detail = duplicate_sensor_response.json()["detail"]
    assert "Duplicate sensor performance record found" in sensor_error_detail
    assert doi in sensor_error_detail
    assert sensor_record_id_str in sensor_error_detail


def test_duplicate_detection_without_doi(db, client, auth_headers):
    """Test duplicate detection works when DOI is not provided (name+type for materials, material+analyte for sensors)."""
    # Create material without DOI
    first_response = client.post("/records/materials",
        json={
            "name": "Test Material",
            "material_type": "Graphene",
            "source_type": "user_contribution"
        },
        headers=auth_headers
    )
    assert first_response.status_code == 201
    first_record_id = first_response.json()["id"]
    
    # Try duplicate with same name and type but no DOI
    duplicate_response = client.post("/records/materials",
        json={
            "name": "Test Material",
            "material_type": "Graphene",
            "source_type": "user_contribution"
        },
        headers=auth_headers
    )
    
    assert duplicate_response.status_code == 409
    error_detail = duplicate_response.json()["detail"]
    assert "Duplicate material record found" in error_detail
    assert "Test Material" in error_detail
    assert "Graphene" in error_detail


def test_toxicity_record_crud_with_versioning(db, client, auth_headers):
    """Test toxicity record CRUD operations with versioning."""
    # First create a material record to reference
    material_response = client.post("/records/materials",
        json={
            "name": "Test Material",
            "material_type": "Graphene",
            "source_type": "user_contribution"
        },
        headers=auth_headers
    )
    material_id_str = material_response.json()["id"]
    material_id = UUID(material_id_str)
    
    # Create toxicity record
    create_response = client.post("/records/toxicity",
        json={
            "material_id": material_id_str,
            "ic50": 100.0,
            "cell_line": "HEK293",
            "exposure_time_h": 24.0
        },
        headers=auth_headers
    )
    assert create_response.status_code == 201
    toxicity_id_str = create_response.json()["id"]
    toxicity_id = UUID(toxicity_id_str)
    
    # Check versioning
    versions = db.query(RecordVersion).filter(
        RecordVersion.record_type == "toxicity_record",
        RecordVersion.record_id == toxicity_id
    ).count()
    assert versions == 1
    
    # Update toxicity record
    update_response = client.put(f"/records/toxicity/{toxicity_id_str}",
        json={
            "ic50": 150.0
        },
        headers=auth_headers
    )
    assert update_response.status_code == 200
    
    # Check versioning increased
    versions = db.query(RecordVersion).filter(
        RecordVersion.record_type == "toxicity_record",
        RecordVersion.record_id == toxicity_id
    ).count()
    assert versions == 2


def test_review_workflow_complete(db, client, auth_headers):
    """Test complete review workflow: pending -> approved -> rejected."""
    # Create material record
    create_response = client.post("/records/materials",
        json={
            "name": "Test Material",
            "material_type": "Graphene",
            "source_type": "user_contribution"
        },
        headers=auth_headers
    )
    record_id_str = create_response.json()["id"]
    record_id = UUID(record_id_str)
    
    # Check initial status is pending
    review = db.query(RecordReview).filter(
        RecordReview.record_type == "material_record",
        RecordReview.record_id == record_id
    ).first()
    assert review.status == "pending"
    
    # Approve the record
    approve_response = client.put(f"/records/reviews/material_record/{record_id_str}",
        json={
            "status": "approved",
            "notes": "Approved for training"
        },
        headers=auth_headers
    )
    assert approve_response.status_code == 200
    
    # Check status is approved
    db.refresh(review)
    assert review.status == "approved"
    assert review.notes == "Approved for training"
    assert review.reviewed_at is not None
    
    # Reject the record
    reject_response = client.put(f"/records/reviews/material_record/{record_id_str}",
        json={
            "status": "rejected",
            "notes": "Data quality issues"
        },
        headers=auth_headers
    )
    assert reject_response.status_code == 200
    
    # Check status is rejected
    db.refresh(review)
    assert review.status == "rejected"
    assert review.notes == "Data quality issues"


def test_get_record_versions(db, client, auth_headers):
    """Test retrieving version history for a record."""
    # Create material record
    create_response = client.post("/records/materials",
        json={
            "name": "Test Material",
            "material_type": "Graphene",
            "core_size_nm": 10.0,
            "source_type": "user_contribution"
        },
        headers=auth_headers
    )
    record_id_str = create_response.json()["id"]
    
    # Update record twice
    client.put(f"/records/materials/{record_id_str}",
        json={"core_size_nm": 15.0},
        headers=auth_headers
    )
    client.put(f"/records/materials/{record_id_str}",
        json={"core_size_nm": 20.0},
        headers=auth_headers
    )
    
    # Get version history
    versions_response = client.get(f"/records/material_record/{record_id_str}/versions", headers=auth_headers)
    assert versions_response.status_code == 200
    versions = versions_response.json()
    
    # Should have 3 versions
    assert len(versions) == 3
    
    # Check version numbers are sequential
    assert versions[0]["version_number"] == 1
    assert versions[1]["version_number"] == 2
    assert versions[2]["version_number"] == 3
    
    # Check data snapshots
    assert versions[0]["data_snapshot"]["core_size_nm"] == 10.0
    assert versions[1]["data_snapshot"]["core_size_nm"] == 10.0
    assert versions[2]["data_snapshot"]["core_size_nm"] == 15.0


def test_data_health_summary(db, client, auth_headers):
    """Test data health summary endpoint."""
    # Create some test records
    client.post("/records/materials",
        json={"name": "Material 1", "material_type": "Graphene", "source_type": "user_contribution"},
        headers=auth_headers
    )
    client.post("/records/materials",
        json={"name": "Material 2", "material_type": "MWCNT", "source_type": "user_contribution"},
        headers=auth_headers
    )
    
    material_response = client.post("/records/materials",
        json={"name": "Material 3", "material_type": "Graphene", "source_type": "user_contribution"},
        headers=auth_headers
    )
    material_id_str = material_response.json()["id"]
    
    # Approve one record
    client.put(f"/records/reviews/material_record/{material_id_str}",
        json={"status": "approved", "notes": "Good"},
        headers=auth_headers
    )
    
    # Get health summary
    summary_response = client.get("/records/health/summary", headers=auth_headers)
    assert summary_response.status_code == 200
    summary = summary_response.json()
    
    assert summary["material_records"] == 3
    assert summary["pending_reviews"] == 2  # 2 still pending
    assert summary["approved_records"] == 1  # 1 approved
    assert summary["rejected_records"] == 0  # 0 rejected


def test_filter_records_by_status(db, client, auth_headers):
    """Test filtering records by review status."""
    # Create multiple records
    response1 = client.post("/records/materials",
        json={"name": "Material 1", "material_type": "Graphene", "source_type": "user_contribution"},
        headers=auth_headers
    )
    response2 = client.post("/records/materials",
        json={"name": "Material 2", "material_type": "MWCNT", "source_type": "user_contribution"},
        headers=auth_headers
    )
    
    # Approve one
    record_id_str = response1.json()["id"]
    client.put(f"/records/reviews/material_record/{record_id_str}",
        json={"status": "approved", "notes": "Good"},
        headers=auth_headers
    )
    
    # Filter by pending status
    pending_response = client.get("/records/materials?status=pending", headers=auth_headers)
    assert pending_response.status_code == 200
    pending_data = pending_response.json()
    assert len(pending_data["items"]) == 1
    
    # Filter by approved status
    approved_response = client.get("/records/materials?status=approved", headers=auth_headers)
    assert approved_response.status_code == 200
    approved_data = approved_response.json()
    assert len(approved_data["items"]) == 1
    
    # Get all records (no filter)
    all_response = client.get("/records/materials", headers=auth_headers)
    assert all_response.status_code == 200
    all_data = all_response.json()
    assert len(all_data["items"]) == 2
