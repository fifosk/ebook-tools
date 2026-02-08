"""SQLAlchemy models — import all to register with Base.metadata."""

from .user import UserModel, SessionModel
from .library import LibraryItemModel, BookModel, LibraryItemGrantModel
from .config import (
    ConfigSnapshotModel,
    ConfigAuditLogModel,
    ConfigSensitiveKeyModel,
    ConfigSecretModel,
    ConfigGroupSettingModel,
    ConfigValidationRuleModel,
    ConfigRestartLogModel,
)
from .bookmark import BookmarkModel
from .resume import ResumePositionModel

__all__ = [
    "UserModel",
    "SessionModel",
    "LibraryItemModel",
    "BookModel",
    "LibraryItemGrantModel",
    "ConfigSnapshotModel",
    "ConfigAuditLogModel",
    "ConfigSensitiveKeyModel",
    "ConfigSecretModel",
    "ConfigGroupSettingModel",
    "ConfigValidationRuleModel",
    "ConfigRestartLogModel",
    "BookmarkModel",
    "ResumePositionModel",
]
