"""SQLAlchemy models. Importing this package registers every table on ``Base.metadata``."""

from app.db.models.access_token import AccessToken
from app.db.models.document import Document
from app.db.models.enums import AccessLevel, MemberRole, member_role_enum
from app.db.models.guest import GuestSession
from app.db.models.invitation import Invitation
from app.db.models.membership import DocumentMember
from app.db.models.share_link import ShareLink
from app.db.models.user import OAuthAccount, User
from app.db.models.yjs_update import YjsUpdate

__all__ = [
    "AccessLevel",
    "AccessToken",
    "Document",
    "DocumentMember",
    "GuestSession",
    "Invitation",
    "MemberRole",
    "OAuthAccount",
    "ShareLink",
    "User",
    "YjsUpdate",
    "member_role_enum",
]
