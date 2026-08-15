# Database Testing Policy

## Issue Resolution Summary

### Issue 1: Live 404s on Render
**Status: RESOLVED - No actual issue**

Investigation revealed that the live endpoints are working correctly:
- `/health` returns `{"status":"ok","environment":"production"}`
- `/records/health/summary` returns valid data
- `/records/materials` returns `{"items":[],"total":0,"skip":0,"limit":100}`
- `/records/toxicity` returns valid empty list

The frontend is correctly configured to call these endpoints. The backend router uses prefix `/records` which matches the frontend calls. The latest commit (54f1eebd1) has been deployed on Render and all endpoints are functional.

### Issue 2: SQLite vs PostgreSQL Testing
**Status: RESOLVED - Reverted to PostgreSQL**

## Why SQLite Was Temporarily Used

During Phase 2 implementation, the configuration was temporarily switched from PostgreSQL to SQLite for local development convenience. This was done because:
1. The PostgreSQL container needed to be started via docker-compose
2. SQLite provided a faster development iteration cycle
3. No immediate database was available during initial development

## The Problem with SQLite Testing

SQLite is significantly more lenient than PostgreSQL in several critical areas:

1. **Type Checking**: SQLite has dynamic typing and will store any data type in any column, while PostgreSQL enforces strict type constraints
2. **JSON Serialization**: SQLite stores JSON as TEXT, while PostgreSQL uses JSONB with proper validation and indexing
3. **UUID Handling**: SQLite treats UUIDs as plain text, while PostgreSQL has native UUID types with proper validation
4. **Datetime Precision**: SQLite has limited datetime precision compared to PostgreSQL's TIMESTAMP WITH TIME ZONE
5. **Constraint Enforcement**: PostgreSQL enforces foreign key constraints more strictly than SQLite

A test passing on SQLite does NOT guarantee it will pass on PostgreSQL, which is what runs in production on Render.

## Resolution

The configuration has been reverted to use PostgreSQL by default:

```python
# api/app/core/config.py
DATABASE_URL: str = "postgresql://scan:scan@localhost:5432/scan_legacy"
```

## Testing Verification

### All 60 pytest tests pass against PostgreSQL
```
====================== 60 passed, 281 warnings in 8.76s =======================
```

### Manual workflow test passes against PostgreSQL
The standalone manual workflow test (`tests/manual_workflow_standalone.py`) was updated to:
- Use random values for email, material names, and DOIs to avoid conflicts with existing test data
- Clean up test records after completion
- Verify all blueprint validation criteria against real PostgreSQL

### JSON Serialization Validation
The versioning system's JSON snapshot storage was verified to work correctly with PostgreSQL's JSONB column type. UUIDs and datetimes are properly converted to strings/ISO format before storage in the JSONB field.

## Behavioral Differences: None Observed

After running all tests against PostgreSQL, no behavioral differences from SQLite were observed. This indicates:
1. The JSON serialization code properly handles the type conversions
2. The schema constraints are compatible between the two databases
3. The ORM (SQLAlchemy) abstracts the differences correctly

## Recommendation: Keep PostgreSQL as Default

**Recommendation: PostgreSQL should remain the default for all testing and development.**

### Reasons:
1. **Production Parity**: PostgreSQL is what runs in production on Render
2. **Type Safety**: PostgreSQL's strict type checking catches errors early
3. **JSONB Performance**: PostgreSQL's JSONB provides better performance and indexing
4. **Constraint Enforcement**: Foreign key and unique constraints are properly enforced
5. **Prevents Silent Failures**: Eliminates the risk of "works on SQLite, fails in production"

### SQLite as Optional Local Convenience
SQLite can be kept as an **optional** override via environment variable for quick prototyping, but:
- It should NEVER be used for CI/CD or final testing
- It should be clearly documented as "for prototyping only"
- All final verification must run against PostgreSQL

## Database Setup

### Local Development (PostgreSQL)
```bash
# Start PostgreSQL via docker-compose
docker-compose up -d

# Run migrations
cd api
python -m alembic upgrade head

# Run tests
python -m pytest tests/ -v
```

### Standalone Manual Workflow Test
```bash
cd api
python tests/manual_workflow_standalone.py
```

## Environment Variables

The following environment variables can be set in `api/.env`:

```bash
# Production: Render Postgres (set automatically by Render)
DATABASE_URL=postgresql://...

# Local Development: PostgreSQL via docker-compose (default)
# No need to set DATABASE_URL - it uses the default from config.py

# Optional: SQLite for quick prototyping (NOT recommended for final testing)
DATABASE_URL=sqlite:///./scan_legacy.db
```

## Commit History

- Commit 54f1eebd1: Phase 2 implementation (used SQLite - **incorrect for production parity**)
- Current commit: Reverted to PostgreSQL, updated configuration, verified all tests pass

## Conclusion

All Phase 2 Module 1 functionality has been verified against real PostgreSQL:
- CRUD operations work correctly
- Versioning creates new rows (not overwrites)
- Review workflow functions properly
- Duplicate detection works as specified
- JSON serialization handles UUIDs and datetimes correctly
- All 60 pytest tests pass
- Manual workflow test passes with cleanup

The live Render deployment is functional and the endpoints are returning valid responses.