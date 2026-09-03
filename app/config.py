import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()  # reads .env into os.environ


class Config:
    """Base configuration. Values are pulled from environment variables —
    nothing sensitive is hardcoded here."""

    # --- Database ---
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    # --- Auth ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ERROR_MESSAGE_KEY = "error"

    # --- Push notifications ---
    EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

    # --- Misc ---
    DEFAULT_FARM_LAT = float(os.environ.get("DEFAULT_FARM_LAT", "-1.29"))
    DEFAULT_FARM_LNG = float(os.environ.get("DEFAULT_FARM_LNG", "36.82"))
    DEFAULT_GEOFENCE_RADIUS_KM = float(os.environ.get("DEFAULT_GEOFENCE_RADIUS_KM", "5.0"))

    @staticmethod
    def validate():
        missing = []
        if not Config.JWT_SECRET_KEY:
            missing.append("JWT_SECRET_KEY")
        if not Config.SQLALCHEMY_DATABASE_URI:
            missing.append("DATABASE_URL")
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Copy .env.example to .env and fill in real values."
            )


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret-key"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
