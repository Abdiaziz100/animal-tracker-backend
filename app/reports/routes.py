import functools
from datetime import datetime, timezone

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models import Animal, User

bp = Blueprint("reports", __name__, url_prefix="/api")


def admin_required(fn):
    @functools.wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = User.query.get_or_404(int(get_jwt_identity()))
        if user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)

    return wrapper


@bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    uid = int(get_jwt_identity())
    animals = Animal.query.filter_by(user_id=uid).all()

    by_species = {}
    for a in animals:
        by_species[a.species] = by_species.get(a.species, 0) + 1

    return jsonify({
        "total_animals": len(animals),
        "inside_farm": sum(1 for a in animals if a.status == "IN"),
        "outside_farm": sum(1 for a in animals if a.status == "OUT"),
        "healthy": sum(1 for a in animals if a.health_status == "Healthy"),
        "sick": sum(1 for a in animals if a.health_status == "Sick"),
        "quarantine": sum(1 for a in animals if a.health_status == "Quarantine"),
        "by_species": by_species,
        "alerts": sum(1 for a in animals if a.status == "OUT"),
    })


@bp.route("/report", methods=["GET"])
@jwt_required()
def generate_report():
    uid = int(get_jwt_identity())
    user = User.query.get_or_404(uid)
    animals = Animal.query.filter_by(user_id=uid).all()
    species_set = {a.species for a in animals}

    return jsonify({
        "report_date": datetime.now(timezone.utc).isoformat(),
        "farmer": {
            "name": user.full_name, "email": user.email, "phone": user.phone,
            "farm_name": user.farm_name, "farm_location": user.farm_location,
        },
        "summary": {
            "total_animals": len(animals),
            "by_species": {s: sum(1 for a in animals if a.species == s) for s in species_set},
            "health_summary": {
                "healthy": sum(1 for a in animals if a.health_status == "Healthy"),
                "sick": sum(1 for a in animals if a.health_status == "Sick"),
                "quarantine": sum(1 for a in animals if a.health_status == "Quarantine"),
            },
            "geofence_status": {
                "inside": sum(1 for a in animals if a.status == "IN"),
                "outside": sum(1 for a in animals if a.status == "OUT"),
            },
        },
        "animals": [a.to_dict() for a in animals],
    })


@bp.route("/admin/users", methods=["GET"])
@admin_required
def admin_users():
    users = User.query.all()
    return jsonify([u.to_dict() for u in users])
