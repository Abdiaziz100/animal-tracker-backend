import secrets

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.extensions import db
from app.models import Animal, HealthRecord
from app.schemas import AnimalSchema, AnimalUpdateSchema, HealthRecordSchema
from app.config import Config

bp = Blueprint("animals", __name__, url_prefix="/api/animals")


@bp.route("", methods=["GET"])
@jwt_required()
def list_animals():
    uid = int(get_jwt_identity())
    animals = Animal.query.filter_by(user_id=uid).order_by(Animal.created_at.desc()).all()
    return jsonify([a.to_dict() for a in animals])


@bp.route("", methods=["POST"])
@jwt_required()
def create_animal():
    uid = int(get_jwt_identity())
    try:
        data = AnimalSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify({"error": "Invalid input", "details": err.messages}), 400

    animal = Animal(
        user_id=uid,
        name=data["name"],
        species=data["species"],
        breed=data["breed"],
        tag_id=data["tag_id"],
        age_years=data["age_years"],
        weight_kg=data["weight_kg"],
        gender=data["gender"],
        color=data["color"],
        health_status=data["health_status"],
        lat=data["lat"] if data["lat"] is not None else Config.DEFAULT_FARM_LAT,
        lng=data["lng"] if data["lng"] is not None else Config.DEFAULT_FARM_LNG,
        status="IN",
        device_token=secrets.token_hex(16),
    )
    db.session.add(animal)
    db.session.commit()

    response = animal.to_dict()
    response["device_token"] = animal.device_token
    return jsonify(response), 201


@bp.route("/<int:animal_id>", methods=["GET"])
@jwt_required()
def get_animal(animal_id):
    uid = int(get_jwt_identity())
    animal = Animal.query.filter_by(id=animal_id, user_id=uid).first_or_404()
    return jsonify(animal.to_dict(include_records=True))


@bp.route("/<int:animal_id>", methods=["PUT"])
@jwt_required()
def update_animal(animal_id):
    uid = int(get_jwt_identity())
    animal = Animal.query.filter_by(id=animal_id, user_id=uid).first_or_404()
    try:
        data = AnimalUpdateSchema().load(request.get_json(silent=True) or {}, partial=True)
    except ValidationError as err:
        return jsonify({"error": "Invalid input", "details": err.messages}), 400

    for field, value in data.items():
        if value is not None:
            setattr(animal, field, value)
    db.session.commit()
    return jsonify(animal.to_dict())


@bp.route("/<int:animal_id>", methods=["DELETE"])
@jwt_required()
def delete_animal(animal_id):
    uid = int(get_jwt_identity())
    animal = Animal.query.filter_by(id=animal_id, user_id=uid).first_or_404()
    db.session.delete(animal)
    db.session.commit()
    return jsonify({"message": "Animal deleted"})


@bp.route("/<int:animal_id>/device-token", methods=["POST"])
@jwt_required()
def rotate_device_token(animal_id):
    uid = int(get_jwt_identity())
    animal = Animal.query.filter_by(id=animal_id, user_id=uid).first_or_404()
    animal.device_token = secrets.token_hex(16)
    db.session.commit()
    return jsonify({"device_token": animal.device_token})


@bp.route("/<int:animal_id>/health", methods=["GET"])
@jwt_required()
def list_health_records(animal_id):
    uid = int(get_jwt_identity())
    animal = Animal.query.filter_by(id=animal_id, user_id=uid).first_or_404()
    return jsonify([r.to_dict() for r in animal.health_records])


@bp.route("/<int:animal_id>/health", methods=["POST"])
@jwt_required()
def add_health_record(animal_id):
    uid = int(get_jwt_identity())
    animal = Animal.query.filter_by(id=animal_id, user_id=uid).first_or_404()
    try:
        data = HealthRecordSchema().load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify({"error": "Invalid input", "details": err.messages}), 400

    record = HealthRecord(animal_id=animal.id, **data)
    db.session.add(record)
    db.session.commit()
    return jsonify(record.to_dict()), 201
