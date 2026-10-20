"""
Demo Application Entry Point.
Initializes the HTTP server and coordinates core services.
"""
from api.routes import APIRouter
from core.engine import WorkflowEngine
from config.settings import AppConfig

class Application:
    """Main application lifecycle controller."""
    def __init__(self, config: AppConfig):
        self.config = config
        self.engine = WorkflowEngine()
        self.router = APIRouter(self.engine)

    def start(self):
        print(f"Starting application on port {self.config.port}...")
        self.router.listen()

if __name__ == "__main__":
    cfg = AppConfig()
    app = Application(cfg)
    app.start()
