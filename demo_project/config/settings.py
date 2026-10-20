"""
Environment configuration management and defaults.
"""
import os

class AppConfig:
    def __init__(self):
        self.app_name = os.getenv("APP_NAME", "DemoProject")
        self.port = int(os.getenv("PORT", "8000"))
        self.debug = os.getenv("DEBUG", "true").lower() == "true"
