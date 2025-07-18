import pytest
from fastapi import status


class TestAuthRegister:
    """Test cases for POST /auth/register endpoint"""
    
    def test_register_success(self, client, sample_user_data, test_utils):
        """Test successful user registration"""
        response = client.post("/api/v1/auth/register", json=sample_user_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        # Validate response structure
        test_utils.assert_auth_response(data, has_user=True)
        
        # Validate user data
        user = data["user"]
        test_utils.assert_user_response(
            user, 
            sample_user_data["email"], 
            sample_user_data["name"]
        )
    
    def test_register_duplicate_email(self, client, sample_user_data):
        """Test registration with duplicate email returns 409"""
        # Register first user
        response1 = client.post("/api/v1/auth/register", json=sample_user_data)
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to register same email again
        response2 = client.post("/api/v1/auth/register", json=sample_user_data)
        assert response2.status_code == status.HTTP_409_CONFLICT
        assert "already registered" in response2.json()["detail"].lower()
    
    def test_register_invalid_email(self, client, invalid_user_data):
        """Test registration with invalid email format"""
        response = client.post("/api/v1/auth/register", json=invalid_user_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_weak_password(self, client, sample_user_data):
        """Test registration with weak password"""
        weak_data = sample_user_data.copy()
        weak_data["password"] = "123"  # Too short
        
        response = client.post("/api/v1/auth/register", json=weak_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.json()["detail"].lower()
    
    def test_register_missing_fields(self, client):
        """Test registration with missing required fields"""
        # Missing name
        response1 = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "testpassword123"
        })
        assert response1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing email
        response2 = client.post("/api/v1/auth/register", json={
            "name": "Test User",
            "password": "testpassword123"
        })
        assert response2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing password
        response3 = client.post("/api/v1/auth/register", json={
            "name": "Test User",
            "email": "test@example.com"
        })
        assert response3.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_password_complexity(self, client, sample_user_data):
        """Test password complexity requirements"""
        # Password without letters
        no_letters = sample_user_data.copy()
        no_letters["password"] = "12345678"
        response1 = client.post("/api/v1/auth/register", json=no_letters)
        assert response1.status_code == status.HTTP_400_BAD_REQUEST
        
        # Password without numbers
        no_numbers = sample_user_data.copy()
        no_numbers["password"] = "testpassword"
        response2 = client.post("/api/v1/auth/register", json=no_numbers)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST


class TestAuthLogin:
    """Test cases for POST /auth/login endpoint"""
    
    def test_login_success(self, client, registered_user, login_data, test_utils):
        """Test successful login"""
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Validate response structure (no user object in login response)
        test_utils.assert_auth_response(data, has_user=False)
    
    def test_login_invalid_credentials(self, client, registered_user, login_data):
        """Test login with invalid credentials"""
        # Wrong password
        wrong_password = login_data.copy()
        wrong_password["password"] = "wrongpassword"
        response1 = client.post("/api/v1/auth/login", json=wrong_password)
        assert response1.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid credentials" in response1.json()["detail"].lower()
        
        # Wrong email
        wrong_email = login_data.copy()
        wrong_email["email"] = "wrong@example.com"
        response2 = client.post("/api/v1/auth/login", json=wrong_email)
        assert response2.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid credentials" in response2.json()["detail"].lower()
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "somepassword123"
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid credentials" in response.json()["detail"].lower()
    
    def test_login_missing_fields(self, client):
        """Test login with missing fields"""
        # Missing email
        response1 = client.post("/api/v1/auth/login", json={
            "password": "testpassword123"
        })
        assert response1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing password
        response2 = client.post("/api/v1/auth/login", json={
            "email": "test@example.com"
        })
        assert response2.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_invalid_email_format(self, client):
        """Test login with invalid email format"""
        response = client.post("/api/v1/auth/login", json={
            "email": "invalid-email",
            "password": "testpassword123"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuthRefresh:
    """Test cases for POST /auth/refresh endpoint"""
    
    def test_refresh_success(self, client, refresh_token):
        """Test successful token refresh"""
        response = client.post("/api/v1/auth/refresh", json={
            "refreshToken": refresh_token
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Validate response structure
        assert "accessToken" in data
        assert isinstance(data["accessToken"], str)
        assert len(data["accessToken"]) > 0
    
    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token"""
        response = client.post("/api/v1/auth/refresh", json={
            "refreshToken": "invalid-token"
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()
    
    def test_refresh_missing_token(self, client):
        """Test refresh with missing token"""
        response = client.post("/api/v1/auth/refresh", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_refresh_empty_token(self, client):
        """Test refresh with empty token"""
        response = client.post("/api/v1/auth/refresh", json={
            "refreshToken": ""
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthLogout:
    """Test cases for POST /auth/logout endpoint"""
    
    def test_logout_success(self, client, refresh_token):
        """Test successful logout"""
        response = client.post("/api/v1/auth/logout", json={
            "refreshToken": refresh_token
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Validate response structure
        assert "message" in data
        assert "logged out" in data["message"].lower()
    
    def test_logout_invalid_token(self, client):
        """Test logout with invalid token"""
        response = client.post("/api/v1/auth/logout", json={
            "refreshToken": "invalid-token"
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "invalid" in response.json()["detail"].lower()
    
    def test_logout_token_already_used(self, client, refresh_token):
        """Test logout with already revoked token"""
        # First logout should succeed
        response1 = client.post("/api/v1/auth/logout", json={
            "refreshToken": refresh_token
        })
        assert response1.status_code == status.HTTP_200_OK
        
        # Second logout with same token should fail
        response2 = client.post("/api/v1/auth/logout", json={
            "refreshToken": refresh_token
        })
        assert response2.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_logout_missing_token(self, client):
        """Test logout with missing token"""
        response = client.post("/api/v1/auth/logout", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuthMe:
    """Test cases for GET /auth/me endpoint"""
    
    def test_me_success(self, client, auth_headers, sample_user_data, test_utils):
        """Test successful user profile retrieval"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Validate user data structure
        assert "id" in data
        assert "email" in data
        assert "name" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "is_active" in data
        
        # Validate user data values
        assert data["email"] == sample_user_data["email"]
        assert data["name"] == sample_user_data["name"]
        assert data["is_active"] is True
    
    def test_me_invalid_token(self, client):
        """Test /me with invalid access token"""
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid-token"
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_me_missing_token(self, client):
        """Test /me without authorization header"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_me_malformed_header(self, client, access_token):
        """Test /me with malformed authorization header"""
        # Missing 'Bearer' prefix
        response1 = client.get("/api/v1/auth/me", headers={
            "Authorization": access_token
        })
        assert response1.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Wrong prefix
        response2 = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Token {access_token}"
        })
        assert response2.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthFlow:
    """Integration tests for complete authentication flows"""
    
    def test_complete_auth_flow(self, client, sample_user_data, test_utils):
        """Test complete authentication flow: register -> login -> refresh -> me -> logout"""
        
        # 1. Register
        register_response = client.post("/api/v1/auth/register", json=sample_user_data)
        assert register_response.status_code == status.HTTP_201_CREATED
        register_data = register_response.json()
        
        # 2. Login
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        assert login_response.status_code == status.HTTP_200_OK
        login_data = login_response.json()
        
        # 3. Use access token to get user profile
        me_response = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {login_data['accessToken']}"
        })
        assert me_response.status_code == status.HTTP_200_OK
        
        # 4. Refresh token
        refresh_response = client.post("/api/v1/auth/refresh", json={
            "refreshToken": login_data["refreshToken"]
        })
        assert refresh_response.status_code == status.HTTP_200_OK
        refresh_data = refresh_response.json()
        
        # 5. Use new access token
        me_response2 = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {refresh_data['accessToken']}"
        })
        assert me_response2.status_code == status.HTTP_200_OK
        
        # 6. Logout
        logout_response = client.post("/api/v1/auth/logout", json={
            "refreshToken": login_data["refreshToken"]
        })
        assert logout_response.status_code == status.HTTP_200_OK
    
    def test_refresh_after_logout_fails(self, client, sample_user_data):
        """Test that refresh token cannot be used after logout"""
        
        # Register and login
        client.post("/api/v1/auth/register", json=sample_user_data)
        login_response = client.post("/api/v1/auth/login", json={
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        login_data = login_response.json()
        refresh_token = login_data["refreshToken"]
        
        # Logout
        client.post("/api/v1/auth/logout", json={
            "refreshToken": refresh_token
        })
        
        # Try to refresh after logout
        refresh_response = client.post("/api/v1/auth/refresh", json={
            "refreshToken": refresh_token
        })
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_multiple_users_isolation(self, client, sample_user_data, sample_user_data_2):
        """Test that multiple users are properly isolated"""
        
        # Register two users
        user1_response = client.post("/api/v1/auth/register", json=sample_user_data)
        user2_response = client.post("/api/v1/auth/register", json=sample_user_data_2)
        
        user1_data = user1_response.json()
        user2_data = user2_response.json()
        
        # Get profiles with respective tokens
        profile1 = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {user1_data['accessToken']}"
        }).json()
        
        profile2 = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {user2_data['accessToken']}"
        }).json()
        
        # Verify users are different
        assert profile1["email"] == sample_user_data["email"]
        assert profile2["email"] == sample_user_data_2["email"]
        assert profile1["id"] != profile2["id"]
        
        # Verify tokens don't work cross-user
        wrong_profile = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {user2_data['accessToken']}"
        }).json()
        assert wrong_profile["email"] == sample_user_data_2["email"]  # Should get user2, not user1
