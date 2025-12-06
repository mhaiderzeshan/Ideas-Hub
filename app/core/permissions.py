from typing import Optional
from app.db.models.enum_json import UserRole
from app.db.models.user import User
from app.db.models.idea import Idea


def get_idea_permissions(idea: "Idea", current_user: Optional["User"]) -> dict:
    """
    Calculate what actions the current user can perform on an idea.

    Returns:
        dict with can_edit and can_delete boolean flags
    """
    # If no user is logged in, no permissions
    if not current_user:
        return {
            "can_edit": False,
            "can_delete": False,
        }

    # Check if user is the owner
    is_owner = str(idea.author_id) == str(current_user.id)

    # Check if user is admin using UserRole enum
    is_admin = current_user.role == UserRole.admin

    return {
        "can_edit": is_owner or is_admin,
        "can_delete": is_owner or is_admin,
    }
