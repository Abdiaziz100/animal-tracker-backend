import logging
from math import radians, sin, cos, sqrt, atan2

import requests
from flask import current_app

logger = logging.getLogger("animal_tracker")


def haversine_km(lat1, lng1, lat2, lng2):
    """Great-circle distance between two lat/lng points, in kilometers."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def send_push_notification(token, title, body):
    """Best-effort push notification via Expo. Never raises."""
    if not token:
        return
    try:
        resp = requests.post(
            current_app.config["EXPO_PUSH_URL"],
            json={"to": token, "title": title, "body": body, "sound": "default", "priority": "high"},
            timeout=5,
        )
        if resp.status_code != 200:
            logger.warning("Push notification failed: %s %s", resp.status_code, resp.text)
    except requests.RequestException as e:
        logger.warning("Push notification error: %s", e)
