from datetime import datetime, timedelta, timezone
from app.extensions import db
from app.models import Animal, LocationHistory


class TestAlertsList:
    def test_empty_alerts_for_new_user(self, client, registered_user):
        headers, _ = registered_user
        resp = client.get("/api/alerts", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_alerts_require_auth(self, client):
        resp = client.get("/api/alerts")
        assert resp.status_code == 401

    def test_alerts_scoped_to_owner(self, client, registered_animal):
        headers, animal = registered_animal
        client.post(
            "/api/tracking/update", json={"lat": -1.55, "lng": 37.10},
            headers={"X-Device-Token": animal["device_token"]},
        )
        other_resp = client.post("/api/auth/register", json={
            "full_name": "Other", "email": "other2@example.com", "password": "password123",
        })
        other_headers = {"Authorization": f"Bearer {other_resp.get_json()['token']}"}
        resp = client.get("/api/alerts", headers=other_headers)
        assert resp.get_json() == []

    def test_limit_param_respected(self, client, registered_animal):
        headers, animal = registered_animal
        # generate several LEFT_FARM/RETURNED pairs
        for _ in range(5):
            client.post("/api/tracking/update", json={"lat": -1.55, "lng": 37.10}, headers={"X-Device-Token": animal["device_token"]})
            client.post("/api/tracking/update", json={"lat": -1.29, "lng": 36.82}, headers={"X-Device-Token": animal["device_token"]})
        resp = client.get("/api/alerts?limit=3", headers=headers)
        assert len(resp.get_json()) == 3


class TestAcknowledge:
    def test_acknowledge_single_alert(self, client, registered_animal):
        headers, animal = registered_animal
        client.post("/api/tracking/update", json={"lat": -1.55, "lng": 37.10}, headers={"X-Device-Token": animal["device_token"]})
        alert_id = client.get("/api/alerts", headers=headers).get_json()[0]["id"]

        resp = client.post(f"/api/alerts/{alert_id}/acknowledge", headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["acknowledged"] is True

    def test_cannot_acknowledge_other_users_alert(self, client, registered_animal):
        headers, animal = registered_animal
        client.post("/api/tracking/update", json={"lat": -1.55, "lng": 37.10}, headers={"X-Device-Token": animal["device_token"]})
        alert_id = client.get("/api/alerts", headers=headers).get_json()[0]["id"]

        other_resp = client.post("/api/auth/register", json={
            "full_name": "Other", "email": "other3@example.com", "password": "password123",
        })
        other_headers = {"Authorization": f"Bearer {other_resp.get_json()['token']}"}
        resp = client.post(f"/api/alerts/{alert_id}/acknowledge", headers=other_headers)
        assert resp.status_code == 404

    def test_unacknowledged_only_filter(self, client, registered_animal):
        headers, animal = registered_animal
        client.post("/api/tracking/update", json={"lat": -1.55, "lng": 37.10}, headers={"X-Device-Token": animal["device_token"]})
        alert_id = client.get("/api/alerts", headers=headers).get_json()[0]["id"]
        client.post(f"/api/alerts/{alert_id}/acknowledge", headers=headers)

        resp = client.get("/api/alerts?unacknowledged_only=true", headers=headers)
        assert resp.get_json() == []

    def test_acknowledge_all(self, client, registered_animal):
        headers, animal = registered_animal
        client.post("/api/tracking/update", json={"lat": -1.55, "lng": 37.10}, headers={"X-Device-Token": animal["device_token"]})
        client.post("/api/tracking/update", json={"lat": -1.29, "lng": 36.82}, headers={"X-Device-Token": animal["device_token"]})

        resp = client.post("/api/alerts/acknowledge-all", headers=headers)
        assert resp.status_code == 200

        resp = client.get("/api/alerts?unacknowledged_only=true", headers=headers)
        assert resp.get_json() == []


class TestInactivityDetection:
    def test_fresh_animal_not_flagged_inactive(self, client, registered_animal):
        headers, _ = registered_animal
        resp = client.get("/api/alerts", headers=headers)
        assert resp.get_json() == []

    def test_animal_inactive_past_threshold_flagged(self, client, registered_animal, app):
        headers, animal = registered_animal
        with app.app_context():
            a = db.session.get(Animal, animal["id"])
            a.created_at = datetime.now(timezone.utc) - timedelta(hours=10)
            db.session.commit()

        resp = client.get("/api/alerts", headers=headers)
        alerts = resp.get_json()
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "INACTIVE"

    def test_animal_within_threshold_not_flagged(self, client, registered_animal, app):
        headers, animal = registered_animal
        with app.app_context():
            a = db.session.get(Animal, animal["id"])
            a.created_at = datetime.now(timezone.utc) - timedelta(hours=2)  # under default 6h threshold
            db.session.commit()

        resp = client.get("/api/alerts", headers=headers)
        assert resp.get_json() == []

    def test_no_duplicate_inactive_alerts_on_repeated_polling(self, client, registered_animal, app):
        headers, animal = registered_animal
        with app.app_context():
            a = db.session.get(Animal, animal["id"])
            a.created_at = datetime.now(timezone.utc) - timedelta(hours=10)
            db.session.commit()

        first = client.get("/api/alerts", headers=headers).get_json()
        second = client.get("/api/alerts", headers=headers).get_json()
        third = client.get("/api/alerts", headers=headers).get_json()
        assert len(first) == len(second) == len(third) == 1

    def test_movement_resets_inactivity_and_can_refire_later(self, client, registered_animal, app):
        headers, animal = registered_animal
        now = datetime.now(timezone.utc)

        with app.app_context():
            a = db.session.get(Animal, animal["id"])
            # animal was already stale 20h ago
            a.created_at = now - timedelta(hours=20)
            owner_id = a.user_id
            db.session.commit()

            from app.models import Alert
            # simulate a first inactivity alert that fired 14h ago (6h after
            # the 20h-ago staleness point) - explicit timestamp, not relying
            # on real test-execution time, so event ordering is unambiguous
            db.session.add(Alert(
                animal_id=animal["id"], user_id=owner_id,
                alert_type="INACTIVE", message="stale",
                created_at=now - timedelta(hours=14),
            ))
            db.session.commit()

        # animal genuinely moves - this location's timestamp represents
        # real activity 8h ago, which is AFTER the previous alert (14h ago),
        # so it should count as a fresh "last known movement"
        with app.app_context():
            loc = LocationHistory(
                animal_id=animal["id"], lat=-1.29, lng=36.82, status="IN",
                timestamp=now - timedelta(hours=8),
            )
            db.session.add(loc)
            db.session.commit()

        # 8h since that movement is past the 6h threshold again -> should fire a NEW alert
        alerts = client.get("/api/alerts", headers=headers).get_json()
        inactive_alerts = [a for a in alerts if a["alert_type"] == "INACTIVE"]
        assert len(inactive_alerts) == 2, "should fire a second INACTIVE alert after a fresh stillness period"

    def test_custom_inactivity_threshold_respected(self, client, registered_animal, app):
        headers, animal = registered_animal
        client.put("/api/geofence", json={"inactivity_threshold_hours": 24}, headers=headers)

        with app.app_context():
            a = db.session.get(Animal, animal["id"])
            a.created_at = datetime.now(timezone.utc) - timedelta(hours=10)  # under the new 24h threshold
            db.session.commit()

        resp = client.get("/api/alerts", headers=headers)
        assert resp.get_json() == []
