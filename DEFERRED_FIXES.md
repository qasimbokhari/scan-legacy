# Deferred Fixes and Future Enhancements

This document tracks features and improvements that were intentionally deferred from the initial implementation but are recognized as potential future needs.

## Design Studio Module

### Search History Persistence
- **Status**: Deferred - Out of scope for initial implementation
- **Description**: Add GET /api/v1/design-studio/search/{id} endpoint for retrieving saved search history
- **Reasoning**: No search-history table or model exists in current database schema. Would require:
  - New `DesignStudioSearchHistory` model/table
  - Database migrations
  - CRUD operations for search history
  - Additional access control and privacy considerations
- **Priority**: Medium - Useful for user experience but not core to retrieval-ranking functionality
- **Complexity**: High - Requires database schema changes and additional infrastructure

## General Infrastructure

### PostgreSQL Database Availability
- **Status**: Infrastructure Issue
- **Description**: PostgreSQL database connection not consistently available in local development environment
- **Impact**: Integration tests fail when database is not running
- **Resolution**: Ensure docker-compose PostgreSQL container is started before running integration tests
- **Command**: `docker-compose up -d` from project root