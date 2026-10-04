def test_register(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "testuser", "password": "password123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "id" in data
    assert "hashed_password" not in data
    assert "password" not in data

def test_register_duplicate_email(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "anotheruser", "password": "password123"},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_register_duplicate_username(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "another@example.com", "username": "testuser", "password": "password123"},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_login_successful(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_password(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 400
    assert "Incorrect" in response.json()["detail"]

def test_login_failed_user_not_found(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "nonexistent@example.com", "password": "password123"},
    )
    assert response.status_code == 400

def test_authenticated_current_user(client):
    # Get token
    login_res = client.post(
        "/api/auth/login",
        data={"username": "test@example.com", "password": "password123"},
    )
    token = login_res.json()["access_token"]

    # Request /me
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"

def test_unauthenticated_request(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401

def test_logout(client):
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["msg"] == "Successfully logged out"
