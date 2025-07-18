# FeedMerge API Tests

This directory contains integration tests for the FeedMerge API endpoints.

## Setup

1. Install test dependencies:
```bash
pip install -r requirements.txt
```

2. Make sure the main application dependencies are installed and database is accessible.

## Running Tests

### Quick Start
```bash
# Run all tests
python test_runner.py

# Run only authentication tests
python test_runner.py auth

# Run with coverage report
python test_runner.py --coverage

# Run with verbose output
python test_runner.py --verbose
```

### Using pytest directly
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/api/auth.test.py

# Run specific test class
pytest tests/api/auth.test.py::TestAuthRegister

# Run specific test method
pytest tests/api/auth.test.py::TestAuthRegister::test_register_success

# Run with coverage
pytest --cov=app --cov-report=html

# Run tests matching a pattern
pytest -k "register"

# Run tests with specific markers
pytest -m "auth"
```

## Test Structure

### Authentication Tests (`auth.test.py`)
- **TestAuthRegister**: User registration endpoint tests
  - Success scenarios
  - Validation errors (email format, password strength)
  - Duplicate email handling
  - Missing field validation

- **TestAuthLogin**: User login endpoint tests
  - Successful authentication
  - Invalid credentials handling
  - Input validation

- **TestAuthRefresh**: Token refresh endpoint tests
  - Valid token refresh
  - Invalid/expired token handling

- **TestAuthLogout**: Logout endpoint tests
  - Successful logout
  - Token revocation
  - Invalid token handling

- **TestAuthMe**: User profile endpoint tests
  - Authenticated user profile retrieval
  - Authorization header validation

- **TestAuthFlow**: End-to-end authentication flow tests
  - Complete user journey testing
  - Token lifecycle management
  - Multi-user isolation

### Test Database

Tests use an isolated SQLite database (`test.db`) that is:
- Created fresh for each test session
- Cleaned up automatically after tests
- Independent from your development database

### Fixtures and Utilities

The test suite includes comprehensive fixtures for:
- **Database setup**: Clean database state for each test
- **Sample data**: Predefined user data for testing
- **Authentication helpers**: Pre-authenticated users and tokens
- **Test utilities**: Common assertion helpers

## Test Categories

Tests are organized with pytest markers:
- `@pytest.mark.auth`: Authentication-related tests
- `@pytest.mark.api`: API endpoint tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Tests that take longer to run

## Coverage

Generate coverage reports with:
```bash
pytest --cov=app --cov-report=html
```

View the HTML report at `htmlcov/index.html`

## Best Practices

1. **Isolation**: Each test is independent and doesn't affect others
2. **Clean State**: Database is reset between tests
3. **Comprehensive**: Tests cover both success and failure scenarios
4. **Realistic**: Uses actual HTTP requests through FastAPI test client
5. **Maintainable**: Well-organized with clear test names and documentation

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure you're running from the `server/` directory
2. **Database Issues**: Test database is automatically managed
3. **Dependency Issues**: Install missing packages with `pip install -r requirements.txt`

### Debug Mode
Run tests with extra verbosity:
```bash
pytest -vv -s
```

Add print statements or use `--pdb` for debugging:
```bash
pytest --pdb
``` 