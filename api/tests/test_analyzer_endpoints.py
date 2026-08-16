"""
Test actual HTTP endpoint behavior for malformed file uploads.

Tests that the analyzer endpoints return HTTP 200 with structured error
for malformed files, as required by the original specification.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports (running from api/ directory)
sys.path.append(str(Path(__file__).parent.parent))

import pytest
import io
from fastapi.testclient import TestClient
from app.main import app
from app.auth.dependencies import get_current_user


class TestEndpointMalformedFile:
    """Test actual HTTP endpoint behavior with malformed files."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for authentication."""
        class MockUser:
            id = "test-id"
            email = "test@example.com"
            role = "contributor"
        return MockUser()
    
    def test_cv_lsv_malformed_file_http_response(self, client, mock_user):
        """Test CV/LSV endpoint returns HTTP 200 with structured error for malformed file."""
        # Override auth dependency
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        # Create malformed CSV
        malformed_csv = """invalid,data,here
more,garbage,stuff"""
        
        files = {"file": ("malformed.csv", io.BytesIO(malformed_csv.encode('utf-8')), "text/csv")}
        
        response = client.post("/api/v1/analyzer/cv-lsv", files=files)
        
        # Clean up dependency override
        app.dependency_overrides = {}
        
        # Assert HTTP 200 with structured error
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        
        error_result = response.json()
        assert error_result["success"] == False, "Success should be False"
        assert "error" in error_result, "Response should contain 'error' field"
        assert "error_type" in error_result, "Response should contain 'error_type' field"
        assert error_result["error_type"] == "parse_error", f"Expected error_type 'parse_error', got {error_result['error_type']}"
    
    def test_eis_malformed_file_http_response(self, client, mock_user):
        """Test EIS endpoint returns HTTP 200 with structured error for malformed file."""
        # Override auth dependency
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        # Create malformed CSV
        malformed_csv = """invalid,data,here
more,garbage,stuff"""
        
        files = {"file": ("malformed.csv", io.BytesIO(malformed_csv.encode('utf-8')), "text/csv")}
        
        response = client.post("/api/v1/analyzer/eis", files=files)
        
        # Clean up dependency override
        app.dependency_overrides = {}
        
        # Assert HTTP 200 with structured error
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        
        error_result = response.json()
        assert error_result["success"] == False, "Success should be False"
        assert "error" in error_result, "Response should contain 'error' field"
        assert "error_type" in error_result, "Response should contain 'error_type' field"
        assert error_result["error_type"] == "parse_error", f"Expected error_type 'parse_error', got {error_result['error_type']}"