from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter.util import get_remote_address
from marshmallow import ValidationError

from app.extensions import db, limiter
from app.models import Animal, Geofence, LocationHistory, Alert
from app.schemas import LocationUpdateSchema, GeofenceSchema
from app.utils import haversine_km, send_push_notification

bp = Blueprint("tracking", __name__, url_prefix="/api")


def _device_token_key():
    token = request.headers.get("X-Device-Token")
    return f"device-token:{token}" if token else get_remote_address()


@bp.route("/tracking/update", methods=["POST"])
@limiter.limit("30 per minute", key_func=_device_token_key)
def update_location():
    device_token = request.headers.get("X-Device-Token", "")
    if not device_token:
        return jsonify({"error": "Missing X-Device-Token header"}), 401

    animal = Animal.query.filter_by(device_token=device_token).first()
    if not animal:
        return jsonify({"error": "Invalid device token"}), 401

    try:
        data = LocationUpdateSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify({"error": "Invalid input", "details": err.messages}), 400

    old_status = animal.status
    animal.lat = data["lat"]
    animal.lng = data["lng"]

    gf = Geofence.query.filter_by(user_id=animal.user_id).first()
    center_lat = gf.center_lat if gf else animal.lat
    center_lng = gf.center_lng if gf else animal.lng
    radius_km = gf.radius_km if gf else 5.0

    distance = haversine_km(animal.lat, animal.lng, center_lat, center_lng)
    animal.status = "OUT" if distance > radius_km else "IN"

    db.session.add(LocationHistory(
        animal_id=animal.id, lat=animal.lat, lng=animal.lng, status=animal.status
    ))

    owner = animal.owner

    if animal.status == "OUT" and old_status == "IN":
        db.session.add(Alert(
            animal_id=animal.id, user_id=animal.user_id, alert_type="LEFT_FARM",
            message=f"{animal.name} left the farm boundary.",
        ))
        send_push_notification(
            owner.expo_push_token,
            f"⚠️ {animal.name} left the farm!",
            f"Last seen at {animal.lat:.4f}, {animal.lng:.4f}",
        )
    elif animal.status == "IN" and old_status == "OUT":
        db.session.add(Alert(
            animal_id=animal.id, user_id=animal.user_id, alert_type="RETURNED",
            message=f"{animal.name} returned to the farm.",
        ))

    db.session.commit()

    return jsonify({"status": animal.status, "animal_id": animal.id, "distance_km": round(distance, 3)})


@bp.route("/animals/<int:animal_id>/history", methods=["GET"])
@jwt_required()
def location_history(animal_id):
    uid = int(get_jwt_identity())
    Animal.query.filter_by(id=animal_id, user_id=uid).first_or_404()
    history = (
        LocationHistory.query.filter_by(animal_id=animal_id)
        .order_by(LocationHistory.timestamp.desc())
        .limit(50)
        .all()
    )
    return jsonify([h.to_dict() for h in history])


@bp.route("/geofence", methods=["GET"])
@jwt_required()
def get_geofence():
    uid = int(get_jwt_identity())
    gf = Geofence.query.filter_by(user_id=uid).first_or_404()
    return jsonify(gf.to_dict())


@bp.route("/geofence", methods=["PUT"])
@jwt_required()
def update_geofence():
    uid = int(get_jwt_identity())
    gf = Geofence.query.filter_by(user_id=uid).first()
    if not gf:
        gf = Geofence(user_id=uid, center_lat=-1.29, center_lng=36.82, radius_km=5.0)
        db.session.add(gf)

    try:
        data = GeofenceSchema().load(request.get_json(silent=True) or {}, partial=True)
    except ValidationError as err:
        return jsonify({"error": "Invalid input", "details": err.messages}), 400

    for field, value in data.items():
        setattr(gf, field, value)
    db.session.commit()
    return jsonify(gf.to_dict())
