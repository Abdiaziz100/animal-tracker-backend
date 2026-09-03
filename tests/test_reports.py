class TestDashboard:
    def test_dashboard_empty(self, client, registered_user):
        headers, _ = registered_user
        resp = client.get("/api/dashboard", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["total_animals"] == 0

    def test_dashboard_counts_reflect_animals(self, client, registered_animal):
        headers, animal = registered_animal
        client.post(
            "/api/tracking/update", json={"lat": -1.55, "lng": 37.10},
            headers={"X-Device-Token": animal["device_token"]},
        )
        resp = client.get("/api/dashboard", headers=headers)
        body = resp.get_json()
        assert body["total_animals"] == 1
        assert body["outside_farm"] == 1
        assert body["alerts"] == 1


class TestReport:
    def test_report_includes_farmer_and_animals(self, client, registered_animal):
        headers, _ = registered_animal
        resp = client.get("/api/report", headers=headers)
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["farmer"]["email"] == "farmer@example.com"
        assert len(body["animals"]) == 1


class TestAdminGating:
    def test_regular_user_forbidden(self, client, registered_user):
        headers, _ = registered_user
        resp = client.get("/api/admin/users", headers=headers)
        assert resp.status_code == 403

    def test_no_auth_unauthorized(self, client):
        resp = client.get("/api/admin/users")
        assert resp.status_code == 401

    def test_admin_role_allowed(self, client, registered_user, app):
        headers, user = registered_user
        from app.extensions import db
        from app.models import User
        with app.app_context():
            u = db.session.get(User, user["id"])
            u.role = "admin"
            db.session.commit()

        resp = client.get("/api/admin/users", headers=headers)
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1
