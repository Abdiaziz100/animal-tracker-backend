from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, limiter
from app.models import User, Geofence
from app.schemas import RegisterSchema, LoginSchema, ProfileUpdateSchema, PushTokenSchema
from app.config import Config

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    try:
        data = RegisterSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify({"error": "Invalid input", "details": err.messages}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        full_name=data["full_name"],
        email=data["email"],
        phone=data["phone"],
        farm_name=data["farm_name"],
        farm_location=data["farm_location"],
        password_hash=generate_password_hash(data["password"]),
    )
    db.session.add(user)
    db.session.flush()

    db.session.add(Geofence(
        user_id=user.id,
        center_lat=Config.DEFAULT_FARM_LAT,
        center_lng=Config.DEFAULT_FARM_LNG,
        radius_km=Config.DEFAULT_GEOFENCE_RADIUS_KM,
    ))
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()}), 201


def _login_email_key():
    data = request.get_json(silent=True) or {}
    return f"login-email:{(data.get('email') or 'unknown').strip().lower()}"


@bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
@limiter.limit("5 per minute", key_func=_login_email_key)
def login():
    try:
        data = LoginSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify({"error": "Invalid input", "details": err.messages}), 400

    user = User.query.filter_by(email=data["email"]).first()
    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    if data.get("expo_push_token"):
        user.expo_push_token = data["expo_push_token"]
        db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({"token": token, "user": user.to_dict()})


@bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    user = User.query.get_or_404(int(get_jwt_identity()))
    return jsonify(user.to_dict())


@bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user = User.query.get_or_404(int(get_jwt_identity()))
    try:
        data = ProfileUpdateSchema().load(request.get_json(silent=True) or {}, partial=True)
    except ValidationError as err:
        return jsonify({"error": "Invalid input", "details": err.messages}), 400

    for field, value in data.items():
        setattr(user, field, value)
    db.session.commit()
    return jsonify(user.to_dict())


@bp.route("/push-token", methods=["PUT"])
@jwt_required()
def update_push_token():
    user = User.query.get_or_404(int(get_jwt_identity()))
    try:
        data = PushTokenSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify({"error": "Invalid input", "details": err.messages}), 400

    user.expo_push_token = data["expo_push_token"]
    db.session.commit()
    return jsonify({"message": "Push token registered"})
