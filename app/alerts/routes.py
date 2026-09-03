from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Animal, Geofence, LocationHistory, Alert, utcnow

bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")


def _check_inactivity(uid):
    """Lazily evaluates every animal for this user and creates an INACTIVE
    alert if it hasn't reported a location in longer than the configured
    threshold. This runs whenever the alerts list is fetched rather than on
    a background schedule - a reasonable approximation for an app that's
    checked periodically, though a real cron/worker would be more precise
    for a large-scale deployment.

    To avoid spamming duplicate alerts, a new INACTIVE alert is only created
    if no INACTIVE alert already exists for this animal since its last
    known movement - so it fires once per "stillness episode," not on every
    poll.
    """
    gf = Geofence.query.filter_by(user_id=uid).first()
    threshold_hours = gf.inactivity_threshold_hours if gf else 6.0
    now = utcnow()

    animals = Animal.query.filter_by(user_id=uid).all()
    for animal in animals:
        last_location = (
            LocationHistory.query.filter_by(animal_id=animal.id)
            .order_by(LocationHistory.timestamp.desc())
            .first()
        )
        reference_time = last_location.timestamp if last_location else animal.created_at
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=now.tzinfo)

        hours_inactive = (now - reference_time).total_seconds() / 3600
        if hours_inactive < threshold_hours:
            continue

        already_alerted = (
            Alert.query.filter_by(animal_id=animal.id, alert_type="INACTIVE")
            .filter(Alert.created_at > reference_time)
            .first()
        )
        if already_alerted:
            continue

        db.session.add(Alert(
            animal_id=animal.id,
            user_id=uid,
            alert_type="INACTIVE",
            message=f"{animal.name} hasn't moved in over {threshold_hours:.0f} hours.",
        ))
    db.session.commit()


@bp.route("", methods=["GET"])
@jwt_required()
def list_alerts():
    uid = int(get_jwt_identity())
    _check_inactivity(uid)

    query = Alert.query.filter_by(user_id=uid)
    if request.args.get("unacknowledged_only") == "true":
        query = query.filter_by(acknowledged=False)

    limit = min(int(request.args.get("limit", 50)), 200)
    alerts = query.order_by(Alert.created_at.desc()).limit(limit).all()
    return jsonify([a.to_dict() for a in alerts])


@bp.route("/<int:alert_id>/acknowledge", methods=["POST"])
@jwt_required()
def acknowledge_alert(alert_id):
    uid = int(get_jwt_identity())
    alert = Alert.query.filter_by(id=alert_id, user_id=uid).first_or_404()
    alert.acknowledged = True
    db.session.commit()
    return jsonify(alert.to_dict())


@bp.route("/acknowledge-all", methods=["POST"])
@jwt_required()
def acknowledge_all():
    uid = int(get_jwt_identity())
    Alert.query.filter_by(user_id=uid, acknowledged=False).update({"acknowledged": True})
    db.session.commit()
    return jsonify({"message": "All alerts acknowledged"})
