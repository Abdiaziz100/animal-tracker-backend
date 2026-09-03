import logging
import os

from flask import Flask, jsonify

from app.config import config_by_name
from app.extensions import db, jwt, migrate, cors, limiter


def create_app(env_name=None):
    env_name = env_name or os.environ.get("FLASK_ENV", "production")
    config_cls = config_by_name.get(env_name, config_by_name["production"])

    if env_name != "testing":
        config_cls.validate()

    app = Flask(__name__)
    app.config.from_object(config_cls)

    logging.basicConfig(
        level=logging.INFO if not app.config.get("DEBUG") else logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})
    limiter.init_app(app)

    from app.auth.routes import bp as auth_bp
    from app.animals.routes import bp as animals_bp
    from app.tracking.routes import bp as tracking_bp
    from app.reports.routes import bp as reports_bp
    from app.alerts.routes import bp as alerts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(animals_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(alerts_bp)

    register_error_handlers(app)

    @app.route("/")
    def home():
        return jsonify({"status": "ok", "service": "Livestock Tracker API", "version": "2.1"})

    @app.route("/ping")
    def ping():
        return jsonify({"status": "ok"})

    return app


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request"}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({"error": "Too many attempts. Please wait a moment and try again."}), 429

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Unhandled server error")
        return jsonify({"error": "Internal server error"}), 500
