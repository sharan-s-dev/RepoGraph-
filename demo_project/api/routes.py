"""
API Routing & Request Handlers.
Exposes endpoints for user authentication and transaction processing.
"""
from core.engine import WorkflowEngine
from models.user import UserModel, UserRole

class APIRouter:
    def __init__(self, engine: WorkflowEngine):
        self.engine = engine

    def get_user_profile(self, user_id: str) -> dict:
        return self.engine.fetch_profile(user_id)

    def register_endpoint(self, payload: dict) -> dict:
        user = UserModel(username=payload.get("username"), role=UserRole.MEMBER)
        return self.engine.register_user(user)

    def listen(self):
        print("API Router listening for requests...")
