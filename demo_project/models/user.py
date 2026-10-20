"""
Data entities and schema definitions for user accounts and security roles.
"""
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"

class UserModel:
    def __init__(self, username: str, role: UserRole = UserRole.MEMBER):
        self.username = username
        self.role = role

    def to_dict(self) -> dict:
        return {"username": self.username, "role": str(self.role)}
