import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.api.deps import get_db

from app.core.config import settings

# Route all tests to the separate isolated test database
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DB_URL:
    if settings.DATABASE_URL.endswith("/synapselm"):
        TEST_DB_URL = settings.DATABASE_URL.replace("/synapselm", "/synapselm_test")
    else:
        TEST_DB_URL = settings.DATABASE_URL + "_test"

SQLALCHEMY_DATABASE_URL = TEST_DB_URL

from sqlalchemy.pool import NullPool

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=NullPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# We will not drop all and create all, because migrations are managed by alembic now.
# But for tests, we can keep the tables as they are in the live DB, or clear data.
# For now, let's just use the existing DB schema.


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

from sqlalchemy import text

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # We do not call create_all/drop_all since Alembic manages the schema.
    # We'll just yield.
    yield

@pytest.fixture(scope="module", autouse=True)
def clear_db():
    # Safest isolation strategy: Truncate tables (except alembic_version) before each test.
    # Ensure this is strictly a test database.
    if not str(engine.url).endswith("_test"):
        raise Exception(f"Refusing to clear non-test database: {engine.url}")
        
    with engine.begin() as conn:
        if engine.dialect.name == 'postgresql':
            conn.execute(text("""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema() AND tablename != 'alembic_version') LOOP
                        EXECUTE 'DELETE FROM ' || quote_ident(r.tablename);
                    END LOOP;
                END $$;
            """))
        elif engine.dialect.name == 'sqlite':
            tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name != 'alembic_version'")).fetchall()
            for table in tables:
                conn.execute(text(f"DELETE FROM {table[0]}"))
    yield

@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    yield session
    # Truncation in clear_db handles cleanup, but we still close the session.
    session.rollback()
    session.close()
