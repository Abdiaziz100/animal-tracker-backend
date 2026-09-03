import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def registered_user(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Test Farmer",
        "email": "farmer@example.com",
        "password": "password123",
        "farm_name": "Test Farm",
        "farm_location": "Nairobi",
    })
    body = resp.get_json()
    headers = {"Authorization": f"Bearer {body['token']}"}
    return headers, body["user"]


@pytest.fixture()
def registered_animal(client, registered_user):
    headers, _ = registered_user
    resp = client.post("/api/animals", json={"name": "Cow-001", "species": "Cattle"}, headers=headers)
    return headers, resp.get_json()
