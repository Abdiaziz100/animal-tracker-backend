from datetime import datetime, timezone
from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    farm_name = db.Column(db.String(120))
    farm_location = db.Column(db.String(200))
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="farmer", nullable=False)
    expo_push_token = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    animals = db.relationship(
        "Animal", backref="owner", lazy=True, cascade="all, delete-orphan"
    )
    geofence = db.relationship(
        "Geofence", backref="owner", lazy=True, uselist=False,
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "farm_name": self.farm_name,
            "farm_location": self.farm_location,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
        }


class Animal(db.Model):
    __tablename__ = "animals"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    species = db.Column(db.String(50), default="Cattle", nullable=False)
    breed = db.Column(db.String(80))
    tag_id = db.Column(db.String(50), index=True)
    age_years = db.Column(db.Float, default=0)
    weight_kg = db.Column(db.Float, default=0)
    gender = db.Column(db.String(10), default="Unknown")
    color = db.Column(db.String(50))
    health_status = db.Column(db.String(20), default="Healthy", nullable=False)
    lat = db.Column(db.Float, default=0)
    lng = db.Column(db.Float, default=0)
    status = db.Column(db.String(10), default="IN", nullable=False)
    device_token = db.Column(db.String(64), unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    health_records = db.relationship(
        "HealthRecord", backref="animal", lazy=True, cascade="all, delete-orphan"
    )
    location_history = db.relationship(
        "LocationHistory", backref="animal", lazy=True,
        cascade="all, delete-orphan", order_by="LocationHistory.timestamp.desc()"
    )

    def to_dict(self, include_records=False):
        data = {
            "id": self.id,
            "name": self.name,
            "species": self.species,
            "breed": self.breed,
            "tag_id": self.tag_id,
            "age_years": self.age_years,
            "weight_kg": self.weight_kg,
            "gender": self.gender,
            "color": self.color,
            "health_status": self.health_status,
            "lat": self.lat,
            "lng": self.lng,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
        if include_records:
            data["health_records"] = [r.to_dict() for r in self.health_records]
        return data


class HealthRecord(db.Model):
    __tablename__ = "health_records"

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animals.id"), nullable=False, index=True)
    record_type = db.Column(db.String(50), default="Checkup")
    description = db.Column(db.String(500))
    vet_name = db.Column(db.String(120))
    date = db.Column(db.DateTime, default=utcnow, nullable=False)
    next_due = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "record_type": self.record_type,
            "description": self.description,
            "vet_name": self.vet_name,
            "date": self.date.isoformat(),
            "next_due": self.next_due.isoformat() if self.next_due else None,
        }


class LocationHistory(db.Model):
    __tablename__ = "location_history"

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animals.id"), nullable=False, index=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(10), nullable=False)
    timestamp = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    def to_dict(self):
        return {
            "lat": self.lat,
            "lng": self.lng,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
        }


class Geofence(db.Model):
    __tablename__ = "geofences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    name = db.Column(db.String(120), default="Main Farm")
    center_lat = db.Column(db.Float, nullable=False)
    center_lng = db.Column(db.Float, nullable=False)
    radius_km = db.Column(db.Float, nullable=False, default=5.0)
    inactivity_threshold_hours = db.Column(db.Float, nullable=False, default=6.0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "center_lat": self.center_lat,
            "center_lng": self.center_lng,
            "radius_km": self.radius_km,
            "inactivity_threshold_hours": self.inactivity_threshold_hours,
        }


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    animal_id = db.Column(db.Integer, db.ForeignKey("animals.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    alert_type = db.Column(db.String(20), nullable=False)  # LEFT_FARM, RETURNED, INACTIVE
    message = db.Column(db.String(300), nullable=False)
    acknowledged = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    animal = db.relationship("Animal", backref="alerts")

    def to_dict(self):
        return {
            "id": self.id,
            "animal_id": self.animal_id,
            "animal_name": self.animal.name if self.animal else None,
            "alert_type": self.alert_type,
            "message": self.message,
            "acknowledged": self.acknowledged,
            "created_at": self.created_at.isoformat(),
        }
