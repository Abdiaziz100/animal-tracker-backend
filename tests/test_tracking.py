class TestTrackingAuth:
    def test_update_without_token_rejected(self, client, registered_animal):
        resp = client.post("/api/tracking/update", json={"lat": -1.29, "lng": 36.82})
        assert resp.status_code == 401

    def test_update_with_wrong_token_rejected(self, client, registered_animal):
        resp = client.post(
            "/api/tracking/update", json={"lat": -1.29, "lng": 36.82},
            headers={"X-Device-Token": "not-a-real-token"},
        )
        assert resp.status_code == 401

    def test_update_with_correct_token_succeeds(self, client, registered_animal):
        _, animal = registered_animal
        resp = client.post(
            "/api/tracking/update", json={"lat": -1.29, "lng": 36.82},
            headers={"X-Device-Token": animal["device_token"]},
        )
        assert resp.status_code == 200

    def test_rotated_token_invalidates_old_one(self, client, registered_animal):
        headers, animal = registered_animal
        old_token = animal["device_token"]
        client.post(f"/api/animals/{animal['id']}/device-token", headers=headers)
        resp = client.post(
            "/api/tracking/update", json={"lat": -1.29, "lng": 36.82},
            headers={"X-Device-Token": old_token},
        )
        assert resp.status_code == 401

    def test_tracking_rate_limited_per_device_token(self, client, registered_animal):
        _, animal = registered_animal
        token = animal["device_token"]
        for _ in range(30):
            resp = client.post(
                "/api/tracking/update", json={"lat": -1.29, "lng": 36.82},
                headers={"X-Device-Token": token},
            )
            assert resp.status_code == 200
        resp = client.post(
            "/api/tracking/update", json={"lat": -1.29, "lng": 36.82},
            headers={"X-Device-Token": token},
        )
        assert resp.status_code == 429


class TestGeofenceLogic:
    def test_animal_inside_radius_marked_in(self, client, registered_animal):
        _, animal = registered_animal
        resp = client.post(
            "/api/tracking/update", json={"lat": -1.29, "lng": 36.82},
            headers={"X-Device-Token": animal["device_token"]},
        )
        assert resp.get_json()["status"] == "IN"

    def test_animal_outside_radius_marked_out(self, client, registered_animal):
        _, animal = registered_animal
        resp = client.post(
            "/api/tracking/update", json={"lat": -1.55, "lng": 37.10},
            headers={"X-Device-Token": animal["device_token"]},
        )
        assert resp.get_json()["status"] == "OUT"

    def test_custom_geofence_respected(self, client, registered_animal):
        headers, animal = registered_animal
        client.put("/api/geofence", json={"radius_km": 50}, headers=headers)
        resp = client.post(
            "/api/tracking/update", json={"lat": -1.55, "lng": 37.10},
            headers={"X-Device-Token": animal["device_token"]},
        )
        assert resp.get_json()["status"] == "IN"

    def test_invalid_coordinates_rejected(self, client, registered_animal):
        _, animal = registered_animal
        resp = client.post(
            "/api/tracking/update", json={"lat": 999, "lng": 36.82},
            headers={"X-Device-Token": animal["device_token"]},
        )
        assert resp.status_code == 400


class TestLocationHistory:
    def test_history_records_updates(self, client, registered_animal):
        headers, animal = registered_animal
        for lat, lng in [(-1.29, 36.82), (-1.30, 36.83), (-1.31, 36.84)]:
            client.post(
                "/api/tracking/update", json={"lat": lat, "lng": lng},
                headers={"X-Device-Token": animal["device_token"]},
            )
        resp = client.get(f"/api/animals/{animal['id']}/history", headers=headers)
        assert resp.status_code == 200
        assert len(resp.get_json()) == 3

    def test_history_requires_owner_auth(self, client, registered_animal):
        _, animal = registered_animal
        resp = client.get(f"/api/animals/{animal['id']}/history")
        assert resp.status_code == 401


class TestGeofenceTransitionAlerts:
    """These verify the new Alert-creation feature that plugs into
    tracking updates."""

    def test_leaving_creates_left_farm_alert(self, client, registered_animal):
        headers, animal = registered_animal
        client.post(
            "/api/tracking/update", json={"lat": -1.55, "lng": 37.10},
            headers={"X-Device-Token": animal["device_token"]},
        )
        resp = client.get("/api/alerts", headers=headers)
        alerts = resp.get_json()
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "LEFT_FARM"
        assert alerts[0]["animal_name"] == "Cow-001"

    def test_returning_creates_returned_alert(self, client, registered_animal):
        headers, animal = registered_animal
        client.post(
            "/api/tracking/update", json={"lat": -1.55, "lng": 37.10},
            headers={"X-Device-Token": animal["device_token"]},
        )
        client.post(
            "/api/tracking/update", json={"lat": -1.29, "lng": 36.82},
            headers={"X-Device-Token": animal["device_token"]},
        )
        resp = client.get("/api/alerts", headers=headers)
        alerts = resp.get_json()
        assert len(alerts) == 2
        assert alerts[0]["alert_type"] == "RETURNED"  # newest first
        assert alerts[1]["alert_type"] == "LEFT_FARM"

    def test_staying_inside_creates_no_alert(self, client, registered_animal):
        headers, animal = registered_animal
        for _ in range(3):
            client.post(
                "/api/tracking/update", json={"lat": -1.29, "lng": 36.82},
                headers={"X-Device-Token": animal["device_token"]},
            )
        resp = client.get("/api/alerts", headers=headers)
        assert resp.get_json() == []

    def test_repeated_exits_create_multiple_alerts(self, client, registered_animal):
        headers, animal = registered_animal
        # leave, return, leave again
        client.post("/api/tracking/update", json={"lat": -1.55, "lng": 37.10}, headers={"X-Device-Token": animal["device_token"]})
        client.post("/api/tracking/update", json={"lat": -1.29, "lng": 36.82}, headers={"X-Device-Token": animal["device_token"]})
        client.post("/api/tracking/update", json={"lat": -1.55, "lng": 37.10}, headers={"X-Device-Token": animal["device_token"]})

        resp = client.get("/api/alerts", headers=headers)
        alerts = resp.get_json()
        assert len(alerts) == 3
        types = [a["alert_type"] for a in alerts]
        assert types == ["LEFT_FARM", "RETURNED", "LEFT_FARM"]
