class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={
            "full_name": "Jane Farmer", "email": "jane@example.com", "password": "password123",
        })
        assert resp.status_code == 201
        body = resp.get_json()
        assert "token" in body
        assert body["user"]["email"] == "jane@example.com"
        assert "password" not in body["user"]

    def test_register_duplicate_email_rejected(self, client, registered_user):
        resp = client.post("/api/auth/register", json={
            "full_name": "Someone Else", "email": "farmer@example.com", "password": "password123",
        })
        assert resp.status_code == 409

    def test_register_missing_fields_rejected(self, client):
        resp = client.post("/api/auth/register", json={"email": "incomplete@example.com"})
        assert resp.status_code == 400

    def test_register_short_password_rejected(self, client):
        resp = client.post("/api/auth/register", json={
            "full_name": "Jane", "email": "jane2@example.com", "password": "short",
        })
        assert resp.status_code == 400

    def test_register_creates_default_geofence(self, client):
        resp = client.post("/api/auth/register", json={
            "full_name": "Jane", "email": "jane3@example.com", "password": "password123",
        })
        headers = {"Authorization": f"Bearer {resp.get_json()['token']}"}
        gf = client.get("/api/geofence", headers=headers)
        assert gf.status_code == 200
        assert gf.get_json()["radius_km"] == 5.0
        assert gf.get_json()["inactivity_threshold_hours"] == 6.0


class TestLogin:
    def test_login_success(self, client, registered_user):
        resp = client.post("/api/auth/login", json={"email": "farmer@example.com", "password": "password123"})
        assert resp.status_code == 200
        assert "token" in resp.get_json()

    def test_login_wrong_password(self, client, registered_user):
        resp = client.post("/api/auth/login", json={"email": "farmer@example.com", "password": "wrongpass"})
        assert resp.status_code == 401

    def test_login_unknown_email(self, client):
        resp = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
        assert resp.status_code == 401

    def test_login_rate_limited_per_account(self, client, registered_user):
        for _ in range(5):
            resp = client.post("/api/auth/login", json={"email": "farmer@example.com", "password": "wrong"})
            assert resp.status_code == 401
        resp = client.post("/api/auth/login", json={"email": "farmer@example.com", "password": "wrong"})
        assert resp.status_code == 429


class TestProfile:
    def test_get_profile_requires_auth(self, client):
        resp = client.get("/api/auth/profile")
        assert resp.status_code == 401

    def test_get_profile(self, client, registered_user):
        headers, user = registered_user
        resp = client.get("/api/auth/profile", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["email"] == user["email"]

    def test_update_profile(self, client, registered_user):
        headers, _ = registered_user
        resp = client.put("/api/auth/profile", json={"farm_name": "New Farm Name"}, headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["farm_name"] == "New Farm Name"


class TestPushToken:
    def test_update_push_token(self, client, registered_user):
        headers, _ = registered_user
        resp = client.put("/api/auth/push-token", json={"expo_push_token": "ExponentPushToken[abc]"}, headers=headers)
        assert resp.status_code == 200

    def test_update_push_token_missing_value_rejected(self, client, registered_user):
        headers, _ = registered_user
        resp = client.put("/api/auth/push-token", json={}, headers=headers)
        assert resp.status_code == 400
