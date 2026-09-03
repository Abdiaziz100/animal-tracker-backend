class TestAnimalsCRUD:
    def test_create_animal(self, client, registered_user):
        headers, _ = registered_user
        resp = client.post("/api/animals", json={"name": "Cow-001", "species": "Cattle", "tag_id": "ET-001"}, headers=headers)
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["name"] == "Cow-001"
        assert body["status"] == "IN"
        assert "device_token" in body

    def test_list_animals_scoped_to_owner(self, client, registered_user):
        headers, _ = registered_user
        client.post("/api/animals", json={"name": "Cow-001"}, headers=headers)
        client.post("/api/animals", json={"name": "Cow-002"}, headers=headers)
        resp = client.get("/api/animals", headers=headers)
        assert resp.status_code == 200
        assert len(resp.get_json()) == 2

    def test_device_token_not_leaked_on_list(self, client, registered_animal):
        headers, _ = registered_animal
        resp = client.get("/api/animals", headers=headers)
        assert "device_token" not in resp.get_json()[0]

    def test_get_single_animal_includes_health_records_key(self, client, registered_animal):
        headers, animal = registered_animal
        resp = client.get(f"/api/animals/{animal['id']}", headers=headers)
        assert resp.status_code == 200
        assert "health_records" in resp.get_json()

    def test_update_animal(self, client, registered_animal):
        headers, animal = registered_animal
        resp = client.put(f"/api/animals/{animal['id']}", json={"health_status": "Sick"}, headers=headers)
        assert resp.status_code == 200
        assert resp.get_json()["health_status"] == "Sick"

    def test_delete_animal(self, client, registered_animal):
        headers, animal = registered_animal
        resp = client.delete(f"/api/animals/{animal['id']}", headers=headers)
        assert resp.status_code == 200
        resp = client.get(f"/api/animals/{animal['id']}", headers=headers)
        assert resp.status_code == 404

    def test_invalid_species_rejected(self, client, registered_user):
        headers, _ = registered_user
        resp = client.post("/api/animals", json={"name": "Mystery", "species": "Dragon"}, headers=headers)
        assert resp.status_code == 400


class TestCrossUserIsolation:
    def _second_user_headers(self, client):
        resp = client.post("/api/auth/register", json={
            "full_name": "Other Farmer", "email": "other@example.com", "password": "password123",
        })
        return {"Authorization": f"Bearer {resp.get_json()['token']}"}

    def test_cannot_view_other_users_animal(self, client, registered_animal):
        _, animal = registered_animal
        other_headers = self._second_user_headers(client)
        resp = client.get(f"/api/animals/{animal['id']}", headers=other_headers)
        assert resp.status_code == 404

    def test_cannot_update_other_users_animal(self, client, registered_animal):
        _, animal = registered_animal
        other_headers = self._second_user_headers(client)
        resp = client.put(f"/api/animals/{animal['id']}", json={"name": "Hijacked"}, headers=other_headers)
        assert resp.status_code == 404

    def test_cannot_delete_other_users_animal(self, client, registered_animal):
        _, animal = registered_animal
        other_headers = self._second_user_headers(client)
        resp = client.delete(f"/api/animals/{animal['id']}", headers=other_headers)
        assert resp.status_code == 404


class TestDeviceToken:
    def test_rotate_device_token_changes_it(self, client, registered_animal):
        headers, animal = registered_animal
        resp = client.post(f"/api/animals/{animal['id']}/device-token", headers=headers)
        assert resp.status_code == 200
        new_token = resp.get_json()["device_token"]
        assert new_token != animal["device_token"]


class TestHealthRecords:
    def test_add_and_list_health_record(self, client, registered_animal):
        headers, animal = registered_animal
        resp = client.post(f"/api/animals/{animal['id']}/health", json={
            "record_type": "Vaccination", "description": "Annual FMD vaccine", "vet_name": "Dr. Otieno",
        }, headers=headers)
        assert resp.status_code == 201

        resp = client.get(f"/api/animals/{animal['id']}/health", headers=headers)
        assert resp.status_code == 200
        assert len(resp.get_json()) == 1
        assert resp.get_json()[0]["record_type"] == "Vaccination"
