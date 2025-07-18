import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import sys
import tempfile

# Add the parent directory to the Python path so we can import app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.db.database import get_db, Base
from app.core.config import settings


# Test database URL - using SQLite for tests
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine with connection pooling for SQLite
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the database dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def setup_test_db():
    """Set up test database before all tests"""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up after all tests
    Base.metadata.drop_all(bind=engine)
    # Close all connections
    engine.dispose()
    # Remove test database file
    try:
        if os.path.exists("./test.db"):
            os.remove("./test.db")
    except PermissionError:
        # On Windows, sometimes the file is still locked
        pass


@pytest.fixture(scope="function")
def db_session(setup_test_db):
    """Create a clean database session for each test"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(setup_test_db):
    """Create a test client for each test"""
    # Clear all tables before each test
    with engine.connect() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
        connection.commit()
        
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "name": "Test User",
        "email": "test@example.com",
        "password": "testpassword123"
    }


@pytest.fixture
def sample_user_data_2():
    """Second sample user data for testing"""
    return {
        "name": "Test User 2",
        "email": "test2@example.com", 
        "password": "testpassword456"
    }


@pytest.fixture
def invalid_user_data():
    """Invalid user data for testing validation"""
    return {
        "name": "Test User",
        "email": "invalid-email",
        "password": "123"  # Too short
    }


@pytest.fixture
def registered_user(client, sample_user_data):
    """Create a registered user and return the response"""
    response = client.post("/api/v1/auth/register", json=sample_user_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def access_token(registered_user):
    """Get access token from registered user"""
    return registered_user["accessToken"]


@pytest.fixture
def refresh_token(registered_user):
    """Get refresh token from registered user"""
    return registered_user["refreshToken"]


@pytest.fixture
def auth_headers(access_token):
    """Create authorization headers with access token"""
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def login_data(sample_user_data):
    """Login data extracted from sample user data"""
    return {
        "email": sample_user_data["email"],
        "password": sample_user_data["password"]
    }


# Test utilities
class TestUtils:
    @staticmethod
    def assert_user_response(user_data, expected_email, expected_name):
        """Assert user response format"""
        assert "id" in user_data
        assert user_data["email"] == expected_email
        assert user_data["name"] == expected_name
        assert isinstance(user_data["id"], str)
    
    @staticmethod
    def assert_auth_response(response_data, has_user=True):
        """Assert authentication response format"""
        assert "accessToken" in response_data
        assert "refreshToken" in response_data
        assert isinstance(response_data["accessToken"], str)
        assert isinstance(response_data["refreshToken"], str)
        assert len(response_data["accessToken"]) > 0
        assert len(response_data["refreshToken"]) > 0
        
        if has_user:
            assert "user" in response_data
            user = response_data["user"]
            assert "id" in user
            assert "email" in user
            assert "name" in user


# Make TestUtils available as fixture
@pytest.fixture
def test_utils():
    return TestUtils 