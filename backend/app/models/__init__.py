"""Importing this package registers every model on `Base.metadata`.

Alembic's env.py and the test create_all() both do `import app.models` so the
full schema is known. Keep this list in sync when adding a model.
"""

from app.models.application import Application
from app.models.category import Category
from app.models.job import Job
from app.models.review import Review
from app.models.staff import Staff
from app.models.subscription import Subscription
from app.models.user import User

__all__ = [
    "Application",
    "Category",
    "Job",
    "Review",
    "Staff",
    "Subscription",
    "User",
]
