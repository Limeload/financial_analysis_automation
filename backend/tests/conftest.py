from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    """FastAPI test client with API key pre-set."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        c.headers["X-API-Key"] = "dev-secret-key-1"
        yield c


@pytest.fixture
def mock_db_session(mocker):
    """Patch get_session to avoid hitting real Postgres."""
    mock_session = AsyncMock()
    mocker.patch("src.storage.database.get_session", return_value=mock_session)
    return mock_session
