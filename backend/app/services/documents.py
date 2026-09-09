from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AccessLevel, Document, DocumentMember, MemberRole, User
from app.services.slugs import unique_document_slug

_ROLE_TO_LEVEL = {
    MemberRole.viewer: AccessLevel.viewer,
    MemberRole.editor: AccessLevel.editor,
}


async def create_document(session: AsyncSession, *, owner: User, title: str) -> Document:
    document = Document(
        title=title or "Untitled",
        owner_id=owner.id,
        slug=await unique_document_slug(session, title),
        markdown_cache="",
    )
    session.add(document)
    await session.flush()
    await session.refresh(document, attribute_names=["owner"])
    return document


async def list_documents_for_user(
    session: AsyncSession, *, user: User
) -> list[tuple[Document, AccessLevel]]:
    stmt = (
        select(Document)
        .options(selectinload(Document.owner), selectinload(Document.members))
        .outerjoin(DocumentMember, DocumentMember.document_id == Document.id)
        .where(or_(Document.owner_id == user.id, DocumentMember.user_id == user.id))
        .order_by(Document.updated_at.desc())
        .distinct()
    )
    documents = (await session.scalars(stmt)).unique().all()

    results: list[tuple[Document, AccessLevel]] = []
    for document in documents:
        if document.owner_id == user.id:
            results.append((document, AccessLevel.owner))
            continue
        member = next((m for m in document.members if m.user_id == user.id), None)
        level = _ROLE_TO_LEVEL[member.role] if member else AccessLevel.viewer
        results.append((document, level))
    return results


async def touch_document(session: AsyncSession, document: Document) -> None:
    document.updated_at = datetime.now(UTC)


async def update_content_cache(
    session: AsyncSession, *, document: Document, markdown: str
) -> Document:
    document.markdown_cache = markdown
    document.updated_at = datetime.now(UTC)
    await session.flush()
    return document
