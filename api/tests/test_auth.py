import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.app.main import app
from api.app.db.session import Base, get_db

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
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


def test_successful_registration(client):
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "contributor"
    assert "hashed_password" not in data


def test_duplicate_email_rejection(client):
    # First registration
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    
    # Duplicate registration
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "differentpassword"
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_successful_login(client):
    # Register user first
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    
    # Login
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_fails(client):
    # Register user first
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    
    # Login with wrong password
    response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


def test_successful_token_refresh(client):
    # Register and login
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    login_response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    refresh_token = login_response.json()["refresh_token"]
    
    # Refresh tokens
    response = client.post("/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # Verify new tokens are valid by using them
    me_response = client.get("/auth/me", headers={
        "Authorization": f"Bearer {data['access_token']}"
    })
    assert me_response.status_code == 200


def test_protected_endpoint_with_valid_token(client):
    # Register and login
    client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    login_response = client.post("/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123"
    })
    access_token = login_response.json()["access_token"]
    
    # Access protected endpoint
    response = client.get("/auth/me", headers={
        "Authorization": f"Bearer {access_token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"


def test_protected_endpoint_with_invalid_token(client):
    response = client.get("/auth/me", headers={
        "Authorization": "Bearer invalidtoken"
    })
    assert response.status_code == 401
