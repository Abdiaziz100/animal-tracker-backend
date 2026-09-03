from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    full_name = fields.Str(required=True, validate=validate.Length(min=1, max=120))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    phone = fields.Str(load_default="", validate=validate.Length(max=20))
    farm_name = fields.Str(load_default="", validate=validate.Length(max=120))
    farm_location = fields.Str(load_default="", validate=validate.Length(max=200))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)
    expo_push_token = fields.Str(load_default=None)


class ProfileUpdateSchema(Schema):
    full_name = fields.Str(validate=validate.Length(min=1, max=120))
    phone = fields.Str(validate=validate.Length(max=20))
    farm_name = fields.Str(validate=validate.Length(max=120))
    farm_location = fields.Str(validate=validate.Length(max=200))


class PushTokenSchema(Schema):
    expo_push_token = fields.Str(required=True, validate=validate.Length(min=1, max=200))


VALID_SPECIES = ["Cattle", "Goat", "Sheep", "Camel", "Donkey", "Poultry", "Other"]
VALID_GENDER = ["Male", "Female", "Unknown"]
VALID_HEALTH = ["Healthy", "Sick", "Quarantine"]


class AnimalSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=80))
    species = fields.Str(load_default="Cattle", validate=validate.OneOf(VALID_SPECIES))
    breed = fields.Str(load_default="", validate=validate.Length(max=80))
    tag_id = fields.Str(load_default="", validate=validate.Length(max=50))
    age_years = fields.Float(load_default=0, validate=validate.Range(min=0, max=100))
    weight_kg = fields.Float(load_default=0, validate=validate.Range(min=0, max=5000))
    gender = fields.Str(load_default="Unknown", validate=validate.OneOf(VALID_GENDER))
    color = fields.Str(load_default="", validate=validate.Length(max=50))
    health_status = fields.Str(load_default="Healthy", validate=validate.OneOf(VALID_HEALTH))
    lat = fields.Float(load_default=None, validate=validate.Range(min=-90, max=90))
    lng = fields.Float(load_default=None, validate=validate.Range(min=-180, max=180))


class AnimalUpdateSchema(AnimalSchema):
    name = fields.Str(validate=validate.Length(min=1, max=80))
    species = fields.Str(validate=validate.OneOf(VALID_SPECIES))


class HealthRecordSchema(Schema):
    record_type = fields.Str(load_default="Checkup", validate=validate.Length(max=50))
    description = fields.Str(load_default="", validate=validate.Length(max=500))
    vet_name = fields.Str(load_default="", validate=validate.Length(max=120))
    next_due = fields.DateTime(load_default=None)


class LocationUpdateSchema(Schema):
    lat = fields.Float(required=True, validate=validate.Range(min=-90, max=90))
    lng = fields.Float(required=True, validate=validate.Range(min=-180, max=180))


class GeofenceSchema(Schema):
    name = fields.Str(validate=validate.Length(max=120))
    center_lat = fields.Float(validate=validate.Range(min=-90, max=90))
    center_lng = fields.Float(validate=validate.Range(min=-180, max=180))
    radius_km = fields.Float(validate=validate.Range(min=0.1, max=1000))
    inactivity_threshold_hours = fields.Float(validate=validate.Range(min=0.5, max=168))
