# File: app/db/models/__init__.py

# First, import the Base. This is crucial.
from app.db.database import Base

# Now, import all the models that use this Base.
# The order doesn't matter here because we are using back_populates.
from .user import User
from .idea import Idea, IdeaVersion, IdeaStat

# You should also import any other models you have, for example:
# from .refresh_token import RefreshToken
# (Based on the relationship in your User model)

from .token import RefreshToken
