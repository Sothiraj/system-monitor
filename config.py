"""Centralised configuration for the system-monitor dashboard.

Environment variables override defaults so the same image runs unchanged
on local dev, Render, Docker, or any other host:

    PORT=5000 FLASK_DEBUG=1 python app.py
"""
import os


class Config:
    APP_NAME = "system-monitor"
    APP_VERSION = "2.0.0"

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # How long (seconds) a computed stats payload stays valid.
    STATS_CACHE_TTL = float(os.getenv("STATS_CACHE_TTL", "1.0"))

    # Background sampler that keeps /api/v1/history warm.
    ENABLE_SAMPLER = os.getenv("ENABLE_SAMPLER", "1") == "1"
    SAMPLER_INTERVAL = float(os.getenv("SAMPLER_INTERVAL", "2.0"))
    HISTORY_MAXLEN = int(os.getenv("HISTORY_MAXLEN", "180"))

    # Alert thresholds (percent, or MB/s for network).
    ALERT_CPU = float(os.getenv("ALERT_CPU", "85"))
    ALERT_RAM = float(os.getenv("ALERT_RAM", "90"))
    ALERT_DISK = float(os.getenv("ALERT_DISK", "90"))

    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    ENABLE_SAMPLER = False


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name: str | None = None):
    name = name or os.getenv("FLASK_ENV", "production")
    return CONFIGS.get(name, ProductionConfig)
