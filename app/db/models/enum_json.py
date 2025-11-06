from sqlalchemy import Enum, JSON
import enum


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class VisibilityEnum(str, enum.Enum):
    public = "public"
    private = "private"


class StageEnum(str, enum.Enum):
    seed = "seed"
    prototype = "prototype"
    growth = "growth"
