"""
Tests for Design Studio retrieval-ranking module.

Tests cover:
- Ranking correctness with hand-calculated expected scores
- Partial spec handling
- Sparse/empty result handling with low-data flag
- Malformed input handling (HTTP 200 + structured error)
- Integration test against real PostgreSQL database
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

# Import test dependencies
try:
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import SessionLocal, engine, Base
    from app.db.models import SensorPerformanceRecord, User
    from app.auth.dependencies import get_current_user
    from app.schemas.design_studio import TargetSpec
    try:
        from app.ml.design_studio.ranking_engine import RankingEngine, create_data_quality_flag
    except ImportError:
        try:
            from ml.design_studio.ranking_engine import RankingEngine, create_data_quality_flag
        except ImportError:
            from design_studio.ranking_engine import RankingEngine, create_data_quality_flag
    APP_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    APP_AVAILABLE = False
    TestClient = None
    SessionLocal = None
    engine = None
    Base = None


pytestmark = pytest.mark.skipif(not APP_AVAILABLE, reason="FastAPI app or database not available")


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    if not SessionLocal:
        pytest.skip("Database not available")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def mock_user():
    """Create mock user for authentication."""
    class MockUser:
        id = uuid4()
        email = "test@example.com"
        role = "contributor"
    return MockUser()


@pytest.fixture
def client():
    """Create test client."""
    if not TestClient:
        pytest.skip("TestClient not available")
    return TestClient(app)


class TestRankingEngine:
    """Test the ranking engine logic with deterministic scoring."""
    
    def test_exact_analyte_match_score(self):
        """Test exact analyte match returns weighted score (0.35 for analyte weight)."""
        engine = RankingEngine()
        record = {'analyte': 'Lead', 'nanomaterial': 'Graphene'}
        target = {'analyte': 'Lead', 'lod_mol_per_l': None}
        
        score, breakdowns = engine.score_record(record, target)
        
        # Score should be analyte weight (0.35) since only analyte matches
        expected_score = engine.weights['analyte']  # 0.35
        assert abs(score - expected_score) < 0.01, f"Expected score {expected_score} for exact match, got {score}"
        analyte_breakdown = [b for b in breakdowns if (b.field_name == 'analyte' if hasattr(b, 'field_name') else b.get('field_name') == 'analyte')][0]
        analyte_score = analyte_breakdown.score if hasattr(analyte_breakdown, 'score') else analyte_breakdown.get('score')
        assert analyte_score == 1.0
    
    def test_fuzzy_analyte_match_score(self):
        """Test fuzzy analyte match returns weighted score (PARTIAL_MATCH_SCORE * 0.35 = 0.28)."""
        engine = RankingEngine()
        record = {'analyte': 'Lead ions', 'nanomaterial': 'Graphene'}
        target = {'analyte': 'Lead', 'lod_mol_per_l': None}
        
        score, breakdowns = engine.score_record(record, target)
        
        # Score should be PARTIAL_MATCH_SCORE (0.8) * analyte weight (0.35) = 0.28
        expected_score = engine.PARTIAL_MATCH_SCORE * engine.weights['analyte']
        assert abs(score - expected_score) < 0.01, f"Expected score {expected_score} for fuzzy match, got {score}"
        analyte_breakdown = [b for b in breakdowns if (b.field_name == 'analyte' if hasattr(b, 'field_name') else b.get('field_name') == 'analyte')][0]
        analyte_score = analyte_breakdown.score if hasattr(analyte_breakdown, 'score') else analyte_breakdown.get('score')
        assert analyte_score == engine.PARTIAL_MATCH_SCORE
        analyte_details = analyte_breakdown.details if hasattr(analyte_breakdown, 'details') else analyte_breakdown.get('details')
        assert analyte_details['match_type'] == 'contains'
    
    def test_no_analyte_match_score(self):
        """Test no analyte match returns score 0.0."""
        engine = RankingEngine()
        record = {'analyte': 'Mercury', 'nanomaterial': 'Graphene'}
        target = {'analyte': 'Lead', 'lod_mol_per_l': None}
        
        score, breakdowns = engine.score_record(record, target)
        
        assert score == 0.0, f"Expected score 0.0 for no match, got {score}"
        analyte_breakdown = [b for b in breakdowns if (b.field_name == 'analyte' if hasattr(b, 'field_name') else b.get('field_name') == 'analyte')][0]
        analyte_score = analyte_breakdown.score if hasattr(analyte_breakdown, 'score') else analyte_breakdown.get('score')
        assert analyte_score == 0.0
    
    def test_exact_lod_match_score(self):
        """Test exact LOD match returns weighted score (0.30 for LOD weight)."""
        engine = RankingEngine()
        record = {'analyte': 'Lead', 'lod_mol_per_l': 1e-9}
        target = {'analyte': None, 'lod_mol_per_l': 1e-9}
        
        score, breakdowns = engine.score_record(record, target)
        
        # Score should be LOD weight (0.30) since only LOD matches
        expected_score = engine.weights['lod']  # 0.30
        assert abs(score - expected_score) < 0.01, f"Expected score {expected_score} for exact LOD match, got {score}"
        lod_breakdown = [b for b in breakdowns if (b.field_name == 'lod' if hasattr(b, 'field_name') else b.get('field_name') == 'lod')][0]
        lod_score = lod_breakdown.score if hasattr(lod_breakdown, 'score') else lod_breakdown.get('score')
        assert lod_score == 1.0
    
    def test_lod_within_10_percent_score(self):
        """Test LOD within 10% returns weighted score (1.0 * 0.30 = 0.30)."""
        engine = RankingEngine()
        record = {'analyte': 'Lead', 'lod_mol_per_l': 1.05e-9}  # 5% difference
        target = {'analyte': None, 'lod_mol_per_l': 1e-9}
        
        score, breakdowns = engine.score_record(record, target)
        
        # Score should be 1.0 * LOD weight (0.30) = 0.30
        expected_score = 1.0 * engine.weights['lod']
        assert abs(score - expected_score) < 0.01, f"Expected score {expected_score} for LOD within 10%, got {score}"
        lod_breakdown = [b for b in breakdowns if (b.field_name == 'lod' if hasattr(b, 'field_name') else b.get('field_name') == 'lod')][0]
        lod_score = lod_breakdown.score if hasattr(lod_breakdown, 'score') else lod_breakdown.get('score')
        assert lod_score == 1.0
    
    def test_lod_within_50_percent_score(self):
        """Test LOD within 50% returns weighted score (0.8 * 0.30 = 0.24)."""
        engine = RankingEngine()
        record = {'analyte': 'Lead', 'lod_mol_per_l': 1.4e-9}  # 40% difference
        target = {'analyte': None, 'lod_mol_per_l': 1e-9}
        
        score, breakdowns = engine.score_record(record, target)
        
        # Score should be 0.8 * LOD weight (0.30) = 0.24
        expected_score = 0.8 * engine.weights['lod']
        assert abs(score - expected_score) < 0.01, f"Expected score {expected_score} for LOD within 50%, got {score}"
        lod_breakdown = [b for b in breakdowns if (b.field_name == 'lod' if hasattr(b, 'field_name') else b.get('field_name') == 'lod')][0]
        lod_score = lod_breakdown.score if hasattr(lod_breakdown, 'score') else lod_breakdown.get('score')
        assert lod_score == 0.8
    
    def test_lod_10x_difference_score(self):
        """Test LOD 10x difference returns score 0.0."""
        engine = RankingEngine()
        record = {'lod_mol_per_l': 10e-9}  # 10x difference, no analyte to avoid interference
        target = {'analyte': None, 'lod_mol_per_l': 1e-9}
        
        score, breakdowns = engine.score_record(record, target)
        
        # According to scoring logic, >5x difference gets score 0.0
        expected_score = 0.0
        assert abs(score - expected_score) < 0.01, f"Expected score {expected_score} for 10x LOD difference, got {score}"
        lod_breakdown = [b for b in breakdowns if (b.field_name == 'lod' if hasattr(b, 'field_name') else b.get('field_name') == 'lod')][0]
        lod_score = lod_breakdown.score if hasattr(lod_breakdown, 'score') else lod_breakdown.get('score')
        assert lod_score == 0.0
    
    def test_combined_scoring_with_weights(self):
        """Test combined scoring with multiple fields and weights."""
        engine = RankingEngine()
        record = {
            'analyte': 'Lead',
            'lod_mol_per_l': 1e-9,
            'nanomaterial': 'Graphene'
        }
        target = {
            'analyte': 'Lead',
            'lod_mol_per_l': 1e-9,
            'nanomaterial': 'Graphene'
        }
        
        score, breakdowns = engine.score_record(record, target)
        
        # All fields score 1.0, so overall should be sum of weights = 0.35 + 0.30 + 0.15 = 0.80
        expected_score = engine.weights['analyte'] + engine.weights['lod'] + engine.weights['nanomaterial']
        assert abs(score - expected_score) < 0.01, f"Expected score {expected_score} for perfect match, got {score}"
        
        # Check that contributions match weights
        total_contribution = 0.0
        for b in breakdowns:
            if hasattr(b, 'contribution'):
                total_contribution += b.contribution
            elif isinstance(b, dict):
                total_contribution += b.get('contribution', 0.0)
        
        assert abs(total_contribution - expected_score) < 0.01
    
    def test_ranking_order_correctness(self):
        """Test that ranking orders records correctly by score."""
        engine = RankingEngine()
        target = {'analyte': 'Lead', 'lod_mol_per_l': 1e-9}
        
        records = [
            {'analyte': 'Lead', 'lod_mol_per_l': 1e-9, 'nanomaterial': 'Graphene'},  # Perfect match
            {'analyte': 'Lead', 'lod_mol_per_l': 1.5e-9, 'nanomaterial': 'Graphene'},  # Close LOD
            {'analyte': 'Lead ions', 'lod_mol_per_l': 1e-9, 'nanomaterial': 'Graphene'},  # Fuzzy analyte
            {'analyte': 'Mercury', 'lod_mol_per_l': 1e-9, 'nanomaterial': 'Graphene'},  # Wrong analyte
        ]
        
        ranked = engine.rank_records(records, target)
        
        # Check order
        assert ranked[0][0] >= ranked[1][0], "First record should have >= score than second"
        assert ranked[1][0] >= ranked[2][0], "Second record should have >= score than third"
        assert ranked[2][0] >= ranked[3][0], "Third record should have >= score than fourth"
        
        # Perfect match should have highest score (sum of analyte + LOD weights = 0.35 + 0.30 = 0.65)
        expected_max_score = engine.weights['analyte'] + engine.weights['lod']
        assert abs(ranked[0][0] - expected_max_score) < 0.01, f"Perfect match should score {expected_max_score}"
    
    def test_partial_spec_handling(self):
        """Test that partial specs (only some fields) work correctly."""
        engine = RankingEngine()
        
        # Only analyte specified
        record = {'analyte': 'Lead', 'lod_mol_per_l': None}
        target = {'analyte': 'Lead', 'lod_mol_per_l': None}
        
        score, breakdowns = engine.score_record(record, target)
        expected_score = engine.weights['analyte']  # 0.35
        assert abs(score - expected_score) < 0.01, f"Partial spec with only analyte should score {expected_score}"
        
        # Only LOD specified
        record2 = {'analyte': None, 'lod_mol_per_l': 1e-9}
        target2 = {'analyte': None, 'lod_mol_per_l': 1e-9}
        
        score2, breakdowns2 = engine.score_record(record2, target2)
        expected_score2 = engine.weights['lod']  # 0.30
        assert abs(score2 - expected_score2) < 0.01, f"Partial spec with only LOD should score {expected_score2}"
    
    def test_custom_weights_are_used(self):
        """Test that custom weights passed to the engine are actually used in scoring."""
        custom_weights = {
            'analyte': 0.50,  # Increase analyte weight
            'lod': 0.30,
            'nanomaterial': 0.10,
            'transduction': 0.05,
            'matrix': 0.05
        }
        engine = RankingEngine(custom_weights=custom_weights)
        
        # Verify custom weights are set
        assert engine.weights['analyte'] == 0.50, "Custom analyte weight should be used"
        assert engine.weights['lod'] == 0.30, "Custom LOD weight should be used"
        
        # Test scoring with custom weights
        record = {'analyte': 'Lead', 'lod_mol_per_l': None}
        target = {'analyte': 'Lead', 'lod_mol_per_l': None}
        
        score, breakdowns = engine.score_record(record, target)
        
        # Score should use custom analyte weight (0.50)
        expected_score = 0.50  # 1.0 * 0.50
        assert abs(score - expected_score) < 0.01, f"Custom weight should be used, expected {expected_score}, got {score}"
    
    def test_matching_is_simple_string_containment_no_ml(self):
        """Test that matching uses simple string containment, not ML/embeddings."""
        engine = RankingEngine()
        
        # Test case-insensitive substring matching (not ML similarity)
        record = {'analyte': 'Lead ions in solution'}
        target = {'analyte': 'Lead'}
        
        score, breakdowns = engine.score_record(record, target)
        
        # Should get fuzzy match score (0.8) because "Lead" is contained in "Lead ions in solution"
        assert score > 0, "Substring match should produce a score"
        
        # Verify it's using string containment logic
        analyte_breakdown = [b for b in breakdowns if (b.field_name == 'analyte' if hasattr(b, 'field_name') else b.get('field_name') == 'analyte')][0]
        match_type = analyte_breakdown.details if hasattr(analyte_breakdown, 'details') else analyte_breakdown.get('details')
        assert match_type['match_type'] in ['exact', 'contains'], "Match type should be exact or contains (string operations)"
        
        # Test that completely different strings get no match (not ML similarity)
        record2 = {'analyte': 'Mercury'}
        target2 = {'analyte': 'Lead'}
        
        score2, breakdowns2 = engine.score_record(record2, target2)
        assert score2 == 0.0, "Completely different strings should get score 0.0 (no ML similarity scoring)"


class TestDesignStudioEndpoints:
    """Test the Design Studio HTTP endpoints."""
    
    @pytest.fixture
    def test_records(self, db_session):
        """Create test sensor performance records."""
        records = []
        
        # Record 1: Perfect match for Lead, LOD 1e-9
        record1 = SensorPerformanceRecord(
            nanomaterial='Graphene',
            analyte='Lead',
            lod_mol_per_l=1e-9,
            sensitivity_value=100.0,
            sensitivity_unit='µA/µM',
            source_type='literature_mined',
            extraction_confidence=0.9,
            doi='10.1000/test1'
        )
        db_session.add(record1)
        records.append(record1)
        
        # Record 2: Close match for Lead, LOD 1.5e-9
        record2 = SensorPerformanceRecord(
            nanomaterial='Graphene',
            analyte='Lead',
            lod_mol_per_l=1.5e-9,
            sensitivity_value=90.0,
            sensitivity_unit='µA/µM',
            source_type='literature_mined',
            extraction_confidence=0.85,
            doi='10.1000/test2'
        )
        db_session.add(record2)
        records.append(record2)
        
        # Record 3: Different analyte (Mercury)
        record3 = SensorPerformanceRecord(
            nanomaterial='MWCNT',
            analyte='Mercury',
            lod_mol_per_l=1e-9,
            sensitivity_value=80.0,
            sensitivity_unit='µA/µM',
            source_type='literature_mined',
            extraction_confidence=0.8,
            doi='10.1000/test3'
        )
        db_session.add(record3)
        records.append(record3)
        
        db_session.commit()
        
        for record in records:
            db_session.refresh(record)
        
        yield records
        
        # Cleanup
        for record in records:
            db_session.delete(record)
        db_session.commit()
    
    def test_search_endpoint_ranking_correctness(self, client, mock_user, test_records):
        """Test search endpoint returns correctly ranked results."""
        # Override auth dependency
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        target_spec = {
            'analyte': 'Lead',
            'lod_mol_per_l': 1e-9,
            'lod_unit': 'mol/L',
            'max_results': 10
        }
        
        response = client.post("/api/v1/design-studio/search", json=target_spec)
        
        # Clean up dependency override
        app.dependency_overrides = {}
        
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        
        result = response.json()
        assert result['success'] == True, "Search should succeed"
        assert len(result['results']) > 0, "Should return some results"
        
        # Check that results are ranked (first should have highest score)
        if len(result['results']) >= 2:
            assert result['results'][0]['overall_score'] >= result['results'][1]['overall_score'], \
                "Results should be ranked by score descending"
        
        # Check that field breakdown is present
        assert 'field_breakdown' in result['results'][0], "Results should include field breakdown"
        assert len(result['results'][0]['field_breakdown']) > 0, "Field breakdown should not be empty"
    
    def test_search_endpoint_partial_spec(self, client, mock_user, test_records):
        """Test search endpoint works with partial spec (only analyte)."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        target_spec = {
            'analyte': 'Lead',
            'max_results': 10
        }
        
        response = client.post("/api/v1/design-studio/search", json=target_spec)
        
        app.dependency_overrides = {}
        
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        
        result = response.json()
        assert result['success'] == True, "Partial spec search should succeed"
        assert len(result['results']) > 0, "Should return results for partial spec"
    
    def test_search_endpoint_sparse_results_low_data_flag(self, client, mock_user, test_records):
        """Test that low-data flag is set when fewer results than requested."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        target_spec = {
            'analyte': 'Lead',
            'max_results': 100  # Request more than available
        }
        
        response = client.post("/api/v1/design-studio/search", json=target_spec)
        
        app.dependency_overrides = {}
        
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        
        result = response.json()
        assert result['success'] == True, "Search should succeed"
        assert result['low_data_flag'] == True, "Low-data flag should be set"
        assert len(result['results']) < 100, "Should return fewer than requested results"
    
    def test_search_endpoint_empty_results(self, client, mock_user, db_session):
        """Test search with no matching records returns empty list with proper flag."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        # Search for non-existent analyte
        target_spec = {
            'analyte': 'NonExistentAnalyte12345',
            'max_results': 10
        }
        
        response = client.post("/api/v1/design-studio/search", json=target_spec)
        
        app.dependency_overrides = {}
        
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        
        result = response.json()
        assert result['success'] == True, "Search should succeed even with no results"
        assert len(result['results']) == 0, "Should return empty list"
        assert result['total_matches'] == 0, "Total matches should be 0"
        assert result['low_data_flag'] == True, "Low-data flag should be set for empty results"
    
    def test_search_endpoint_malformed_input_no_criteria(self, client, mock_user):
        """Test that malformed input (no search criteria) returns HTTP 200 with structured error."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        # Empty target spec (no search criteria)
        target_spec = {
            'max_results': 10
        }
        
        response = client.post("/api/v1/design-studio/search", json=target_spec)
        
        app.dependency_overrides = {}
        
        assert response.status_code == 200, f"Expected status 200 with structured error, got {response.status_code}"
        
        result = response.json()
        assert result['success'] == False, "Success should be False for invalid input"
        assert 'error' in result, "Response should contain 'error' field"
        assert 'error_type' in result, "Response should contain 'error_type' field"
        assert result['error_type'] == 'validation_error', f"Expected error_type 'validation_error', got {result['error_type']}"
    
    def test_search_endpoint_data_quality_flag(self, client, mock_user, db_session):
        """Test that data quality flags are correctly set based on record metadata."""
        # Create test records with different quality levels
        high_quality = SensorPerformanceRecord(
            nanomaterial='Graphene',
            analyte='Lead',
            lod_mol_per_l=1e-9,
            source_type='literature_mined',
            extraction_confidence=0.9,
            doi='10.1000/high_quality'
        )
        
        low_quality = SensorPerformanceRecord(
            nanomaterial='Graphene',
            analyte='Lead',
            lod_mol_per_l=2e-9,
            source_type='user_contribution',
            extraction_confidence=0.5,
            doi=None
        )
        
        db_session.add(high_quality)
        db_session.add(low_quality)
        db_session.commit()
        db_session.refresh(high_quality)
        db_session.refresh(low_quality)
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        target_spec = {
            'analyte': 'Lead',
            'max_results': 10
        }
        
        response = client.post("/api/v1/design-studio/search", json=target_spec)
        
        app.dependency_overrides = {}
        
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        
        result = response.json()
        assert result['success'] == True, "Search should succeed"
        
        # Check data quality flags are present
        for search_result in result['results']:
            assert 'data_quality' in search_result, "Results should include data quality"
            assert 'is_verified' in search_result['data_quality'], "Data quality should include is_verified"
            assert 'source_type' in search_result['data_quality'], "Data quality should include source_type"
        
        # Cleanup
        db_session.delete(high_quality)
        db_session.delete(low_quality)
        db_session.commit()


class TestIntegration:
    """Integration test against real PostgreSQL database."""
    
    def test_full_search_rank_return_cycle(self, client, mock_user, db_session):
        """Test full search → rank → return cycle against real database."""
        # Create a known set of test records
        test_records = []
        
        for i in range(5):
            record = SensorPerformanceRecord(
                nanomaterial=f'TestMaterial{i}',
                analyte='TestAnalyte',
                lod_mol_per_l=1e-9 * (1 + i * 0.5),  # Varying LOD
                sensitivity_value=100.0 - i * 10,
                sensitivity_unit='µA/µM',
                source_type='literature_mined',
                extraction_confidence=0.8,
                doi=f'10.1000/test{i}'
            )
            db_session.add(record)
            test_records.append(record)
        
        db_session.commit()
        
        for record in test_records:
            db_session.refresh(record)
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        target_spec = {
            'analyte': 'TestAnalyte',
            'lod_mol_per_l': 1e-9,
            'max_results': 10
        }
        
        response = client.post("/api/v1/design-studio/search", json=target_spec)
        
        app.dependency_overrides = {}
        
        assert response.status_code == 200, f"Expected status 200, got {response.status_code}"
        
        result = response.json()
        assert result['success'] == True, "Search should succeed"
        assert len(result['results']) == 5, f"Should return all 5 test records, got {len(result['results'])}"
        
        # Verify specific records are returned
        returned_ids = [r['id'] for r in result['results']]
        test_ids = [str(r.id) for r in test_records]
        
        for test_id in test_ids:
            assert test_id in returned_ids, f"Test record {test_id} should be in results"
        
        # Verify ranking (closest LOD should be first)
        assert result['results'][0]['lod_mol_per_l'] == 1e-9, "Closest LOD should be ranked first"
        
        # Verify field breakdown presence
        for search_result in result['results']:
            assert 'field_breakdown' in search_result, "Each result should have field breakdown"
            assert 'data_quality' in search_result, "Each result should have data quality"
            assert 'overall_score' in search_result, "Each result should have overall score"
        
        # Cleanup
        for record in test_records:
            db_session.delete(record)
        db_session.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])