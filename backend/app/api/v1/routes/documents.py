from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import PlainTextResponse
from slugify import slugify

from app.api.deps import (
    DocumentContextBySlugDep,
    DocumentContextDep,
    EditorContextDep,
    OwnerContextDep,
    SessionDep,
)
from app.auth.backend import current_user
from app.db.models import AccessLevel, Document, User
from app.schemas.common import UserBrief
from app.schemas.document import (
    DocumentContentOut,
    DocumentContentUpdate,
    DocumentCreate,
    DocumentListItem,
    DocumentOut,
    DocumentUpdate,
)
from app.services.documents import (
    create_document,
    list_documents_for_user,
    update_content_cache,
)

router = APIRouter(prefix="/documents", tags=["documents"])

CurrentUser = Annotated[User, Depends(current_user)]


def _to_out(document: Document, level: AccessLevel) -> DocumentOut:
    return DocumentOut(
        id=document.id,
        slug=document.slug,
        title=document.title,
        owner=UserBrief.model_validate(document.owner),
        created_at=document.created_at,
        updated_at=document.updated_at,
        access_level=level,
    )


@router.get("", response_model=list[DocumentListItem])
async def list_documents(session: SessionDep, user: CurrentUser) -> list[DocumentListItem]:
    rows = await list_documents_for_user(session, user=user)
    return [
        DocumentListItem(
            id=doc.id,
            slug=doc.slug,
            title=doc.title,
            updated_at=doc.updated_at,
            access_level=level,
            owner=UserBrief.model_validate(doc.owner),
        )
        for doc, level in rows
    ]


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def create_new_document(
    payload: DocumentCreate, session: SessionDep, user: CurrentUser
) -> DocumentOut:
    document = await create_document(session, owner=user, title=payload.title)
    await session.commit()
    await session.refresh(document, attribute_names=["owner"])
    return _to_out(document, AccessLevel.owner)


@router.get("/by-slug/{slug}", response_model=DocumentOut)
async def get_document_by_slug(ctx: DocumentContextBySlugDep) -> DocumentOut:
    return _to_out(ctx.document, ctx.access_level)


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(ctx: DocumentContextDep) -> DocumentOut:
    return _to_out(ctx.document, ctx.access_level)


@router.patch("/{document_id}", response_model=DocumentOut)
async def update_document(
    payload: DocumentUpdate, ctx: EditorContextDep, session: SessionDep
) -> DocumentOut:
    ctx.document.title = payload.title
    ctx.document.updated_at = datetime.now(UTC)
    out = _to_out(ctx.document, ctx.access_level)
    await session.commit()
    return out


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(ctx: OwnerContextDep, session: SessionDep) -> Response:
    await session.delete(ctx.document)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{document_id}/content", response_model=DocumentContentOut)
async def get_document_content(ctx: DocumentContextDep) -> DocumentContentOut:
    return DocumentContentOut(
        markdown=ctx.document.markdown_cache, updated_at=ctx.document.updated_at
    )


@router.put("/{document_id}/content", response_model=DocumentContentOut)
async def put_document_content(
    payload: DocumentContentUpdate, ctx: EditorContextDep, session: SessionDep
) -> DocumentContentOut:
    document = await update_content_cache(session, document=ctx.document, markdown=payload.markdown)
    await session.commit()
    return DocumentContentOut(markdown=document.markdown_cache, updated_at=document.updated_at)


@router.get("/{document_id}/export", response_class=PlainTextResponse)
async def export_document(ctx: DocumentContextDep) -> PlainTextResponse:
    filename = f"{slugify(ctx.document.title) or 'document'}.md"
    return PlainTextResponse(
        ctx.document.markdown_cache,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
