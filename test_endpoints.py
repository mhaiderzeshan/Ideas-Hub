import httpx
import asyncio
from app.db.database import AsyncSessionLocal, engine, Base
from app.db.models.user import User, UserRole
from app.core.security import create_access_token
from app.core.config import settings
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

# Configuration
BASE_URL = "http://127.0.0.1:8000"
REGULAR_USER_EMAIL = "testuser@example.com"
REGULAR_USER_PASSWORD = "testpassword"
REGULAR_USER_NAME = "Test User"

ADMIN_USER_EMAIL = "adminuser@example.com"
ADMIN_USER_PASSWORD = "adminpassword"
ADMIN_USER_NAME = "Admin User"


async def delete_all_users(db: AsyncSession):
    await db.execute(User.__table__.delete())
    await db.commit()
    print("All users deleted from the database.")

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def override_get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def signup_user(client: httpx.AsyncClient, email, password, name):
    response = await client.post(
        f"{BASE_URL}/signup",
        json={"email": email, "password": password, "name": name}
    )
    response.raise_for_status()
    print(f"Signed up user: {email}")
    return response.json()


async def login_user(client: httpx.AsyncClient, email, password):
    response = await client.post(
        f"{BASE_URL}/login",
        data={"email": email, "password": password}
    )
    response.raise_for_status()
    print(f"Logged in user: {email}")
    return response.json()["access_token"]


async def get_me(client: httpx.AsyncClient, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(f"{BASE_URL}/me", headers=headers)
    return response


async def get_admin(client: httpx.AsyncClient, token: str):
    headers = {"Authorization": f"Bearer {token}"}
    response = await client.get(f"{BASE_URL}/admin", headers=headers)
    return response


async def update_user_role_to_admin(db: AsyncSession, email: str):
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        user.role = UserRole.admin
        await db.commit()
        await db.refresh(user)
        print(f"Updated user {email} to admin role.")
    else:
        raise ValueError(f"User with email {email} not found.")


async def main():
    await create_tables() # Ensure tables are created for direct DB interaction
    async with AsyncSessionLocal() as db:
        await delete_all_users(db)

    async with httpx.AsyncClient() as client:
        # 1. Create and login regular user
        await signup_user(client, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD, REGULAR_USER_NAME)
        regular_user_token = await login_user(client, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD)

        # 2. Test /me with regular user
        print("\nTesting /me with regular user...")
        me_response = await get_me(client, regular_user_token)
        print(f"/me response (regular user): {me_response.status_code} - {me_response.json()}")
        assert me_response.status_code == 200
        assert me_response.json()["email"] == REGULAR_USER_EMAIL
        assert me_response.json()["role"] == UserRole.user.value

        # 3. Attempt to access /admin with regular user (should fail)
        print("\nTesting /admin with regular user (expected to fail)...")
        admin_response_fail = await get_admin(client, regular_user_token)
        print(f"/admin response (regular user): {admin_response_fail.status_code} - {admin_response_fail.json()}")
        assert admin_response_fail.status_code == 403

        # 4. Update regular user to admin role in DB
        async with AsyncSessionLocal() as db:
            await update_user_role_to_admin(db, REGULAR_USER_EMAIL)

        # 5. Login the now-admin user (need a new token as role is in token payload)
        admin_user_token = await login_user(client, REGULAR_USER_EMAIL, REGULAR_USER_PASSWORD)

        # 6. Test /me with admin user
        print("\nTesting /me with admin user...")
        me_admin_response = await get_me(client, admin_user_token)
        print(f"/me response (admin user): {me_admin_response.status_code} - {me_admin_response.json()}")
        assert me_admin_response.status_code == 200
        assert me_admin_response.json()["email"] == REGULAR_USER_EMAIL
        assert me_admin_response.json()["role"] == UserRole.admin.value

        # 7. Test /admin with admin user
        print("\nTesting /admin with admin user...")
        admin_response_success = await get_admin(client, admin_user_token)
        print(f"/admin response (admin user): {admin_response_success.status_code} - {admin_response_success.json()}")
        assert admin_response_success.status_code == 200
        assert admin_response_success.json()["email"] == REGULAR_USER_EMAIL
        assert admin_response_success.json()["role"] == UserRole.admin.value

    print("\nAll tests passed!")


if __name__ == "__main__":
    asyncio.run(main())
