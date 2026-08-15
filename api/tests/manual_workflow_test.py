"""
Manual workflow test to validate the Phase 2 Module 1 Dashboard functionality.
This simulates the user walking through the UI workflow programmatically.
"""
import requests
import json

BASE_URL = "http://localhost:8001"

def test_manual_workflow():
    """Test the complete manual workflow as specified in the blueprint."""
    
    print("Starting manual workflow test...")
    
    # Step 1: Register a user
    print("\n1. Registering user...")
    register_response = requests.post(f"{BASE_URL}/auth/register", json={
        "email": "testuser@example.com",
        "password": "testpassword123"
    })
    assert register_response.status_code == 201, f"Registration failed: {register_response.text}"
    print("PASS: User registered successfully")
    
    # Step 2: Login
    print("\n2. Logging in...")
    login_response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "testuser@example.com",
        "password": "testpassword123"
    })
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("PASS: Login successful")
    
    # Step 3: Create a material record
    print("\n3. Creating material record...")
    material_response = requests.post(f"{BASE_URL}/records/materials", 
        json={
            "name": "Test Graphene Material",
            "material_type": "Graphene",
            "core_size_nm": 10.0,
            "source_type": "user_contribution"
        },
        headers=headers
    )
    assert material_response.status_code == 201, f"Material creation failed: {material_response.text}"
    material_id = material_response.json()["id"]
    print(f"PASS: Material record created with ID: {material_id}")
    
    # Step 4: Check that it appears in data table as "pending"
    print("\n4. Checking material appears in data table as pending...")
    materials_response = requests.get(f"{BASE_URL}/records/materials?status=pending", headers=headers)
    assert materials_response.status_code == 200, f"Failed to fetch materials: {materials_response.text}"
    materials = materials_response.json()["items"]
    assert len(materials) == 1, f"Expected 1 pending material, got {len(materials)}"
    assert materials[0]["id"] == material_id, "Material ID mismatch"
    print("PASS: Material appears in pending list")
    
    # Step 5: Approve the record via review workflow
    print("\n5. Approving the record via review workflow...")
    approve_response = requests.put(f"{BASE_URL}/records/reviews/material_record/{material_id}",
        json={
            "status": "approved",
            "notes": "Approved for testing"
        },
        headers=headers
    )
    assert approve_response.status_code == 200, f"Approval failed: {approve_response.text}"
    print("PASS: Record approved successfully")
    
    # Step 6: Confirm it now shows as "approved"
    print("\n6. Confirming record shows as approved...")
    approved_materials = requests.get(f"{BASE_URL}/records/materials?status=approved", headers=headers)
    assert approved_materials.status_code == 200, f"Failed to fetch approved materials: {approved_materials.text}"
    approved = approved_materials.json()["items"]
    assert len(approved) == 1, f"Expected 1 approved material, got {len(approved)}"
    assert approved[0]["id"] == material_id, "Approved material ID mismatch"
    print("PASS: Record shows as approved")
    
    # Step 7: Confirm it appears in trainable-dataset filtered view
    print("\n7. Confirming record appears in trainable dataset...")
    trainable_response = requests.get(f"{BASE_URL}/records/trainable?record_type=material", headers=headers)
    assert trainable_response.status_code == 200, f"Failed to fetch trainable dataset: {trainable_response.text}"
    trainable = trainable_response.json()
    assert "materials" in trainable, "Missing 'materials' in trainable response"
    assert len(trainable["materials"]) == 1, f"Expected 1 trainable material, got {len(trainable['materials'])}"
    assert trainable["materials"][0]["id"] == material_id, "Trainable material ID mismatch"
    print("PASS: Record appears in trainable dataset")
    
    # Step 8: Edit the same record
    print("\n8. Editing the material record...")
    edit_response = requests.put(f"{BASE_URL}/records/materials/{material_id}",
        json={
            "core_size_nm": 15.0
        },
        headers=headers
    )
    assert edit_response.status_code == 200, f"Edit failed: {edit_response.text}"
    print("PASS: Record edited successfully")
    
    # Step 9: Confirm the audit log shows two versions
    print("\n9. Checking audit log shows two versions...")
    versions_response = requests.get(f"{BASE_URL}/records/material_record/{material_id}/versions", headers=headers)
    assert versions_response.status_code == 200, f"Failed to fetch versions: {versions_response.text}"
    versions = versions_response.json()
    assert len(versions) == 2, f"Expected 2 versions, got {len(versions)}"
    assert versions[0]["version_number"] == 1, "First version should be version 1"
    assert versions[1]["version_number"] == 2, "Second version should be version 2"
    assert versions[0]["data_snapshot"]["core_size_nm"] == 10.0, "First version should have original core_size"
    assert versions[1]["data_snapshot"]["core_size_nm"] == 10.0, "Second version snapshot should have old core_size"
    print("PASS: Audit log shows two versions with correct data")
    
    # Step 10: Attempt to submit a duplicate (same name + material type)
    print("\n10. Attempting to submit duplicate record...")
    duplicate_response = requests.post(f"{BASE_URL}/records/materials",
        json={
            "name": "Test Graphene Material",
            "material_type": "Graphene",
            "source_type": "user_contribution"
        },
        headers=headers
    )
    assert duplicate_response.status_code == 409, f"Expected 409 Conflict, got {duplicate_response.status_code}"
    error_detail = duplicate_response.json()["detail"]
    assert "Duplicate material record found" in error_detail, f"Expected duplicate error message, got: {error_detail}"
    assert "Test Graphene Material" in error_detail, "Error should mention the duplicate name"
    assert "Graphene" in error_detail, "Error should mention the duplicate type"
    print(f"PASS: Duplicate submission rejected with clear message: {error_detail}")
    
    # Step 11: Test with DOI duplicate detection
    print("\n11. Testing DOI duplicate detection...")
    doi_material_response = requests.post(f"{BASE_URL}/records/materials",
        json={
            "name": "DOI Test Material",
            "material_type": "Graphene",
            "doi": "10.1234/test.doi.12345",
            "source_type": "literature_mined"
        },
        headers=headers
    )
    assert doi_material_response.status_code == 201, f"DOI material creation failed: {doi_material_response.text}"
    doi_material_id = doi_material_response.json()["id"]
    
    # Try duplicate with same DOI
    doi_duplicate_response = requests.post(f"{BASE_URL}/records/materials",
        json={
            "name": "Different Name",
            "material_type": "Graphene",
            "doi": "10.1234/test.doi.12345",
            "source_type": "user_contribution"
        },
        headers=headers
    )
    assert doi_duplicate_response.status_code == 409, f"Expected 409 for DOI duplicate, got {doi_duplicate_response.status_code}"
    doi_error_detail = doi_duplicate_response.json()["detail"]
    assert "10.1234/test.doi.12345" in doi_error_detail, "Error should mention the DOI"
    assert str(doi_material_id) in doi_error_detail, "Error should mention the conflicting record ID"
    print(f"PASS: DOI duplicate detection works: {doi_error_detail}")
    
    print("\n" + "="*50)
    print("MANUAL WORKFLOW TEST: ALL STEPS PASSED")
    print("="*50)
    print("\nBlueprint Validation Criteria:")
    print("1. Versioning creates new versions not overwrites")
    print("2. Unreviewed records excluded from trainable query")
    print("3. Duplicate DOI rejected with clear message")
    
    return True

if __name__ == "__main__":
    try:
        test_manual_workflow()
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED ERROR: {e}")
        exit(1)