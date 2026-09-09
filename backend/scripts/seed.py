"""Create a demo account and a starter document. Idempotent."""

from __future__ import annotations

import asyncio
import contextlib

from app.auth.users import UserManager
from app.db.models import OAuthAccount, User
from app.db.session import async_session_maker
from app.schemas.user import UserCreate
from app.services.documents import create_document
from fastapi_users.exceptions import UserAlreadyExists
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase

DEMO_EMAIL = "demo@comark.app"
DEMO_PASSWORD = "comark-demo"

WELCOME_MD = """# Welcome to CoMark

This document is **live**. Open it in another browser — or send someone a share
link — and watch edits and cursors appear in real time.

## Try it

- Type here and see it sync
- Move your mouse over the page; others see your pointer
- Use the *Share* button to invite people with or without an account
"""


async def main() -> None:
    async with async_session_maker() as session:
        user_db = SQLAlchemyUserDatabase(session, User, OAuthAccount)
        manager = UserManager(user_db)

        user = await user_db.get_by_email(DEMO_EMAIL)
        if user is None:
            with contextlib.suppress(UserAlreadyExists):
                user = await manager.create(
                    UserCreate(
                        email=DEMO_EMAIL,
                        password=DEMO_PASSWORD,
                        display_name="Demo",
                    )
                )
            user = user or await user_db.get_by_email(DEMO_EMAIL)

        assert user is not None
        document = await create_document(session, owner=user, title="Welcome to CoMark")
        document.markdown_cache = WELCOME_MD
        await session.commit()

        print(f"✓ demo account: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"✓ document:     /d/{document.slug}")


if __name__ == "__main__":
    asyncio.run(main())
