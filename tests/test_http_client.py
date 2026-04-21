import pytest
import asyncio
from aioresponses import aioresponses
from aiohttp import ClientSession
from src.http_client import ShowdownHTTPClient


@pytest.mark.asyncio
async def test_fetch_json_success(mock_aioresponse: aioresponses) -> None:
    url = "https://example.com/success.json"
    mock_aioresponse.get(url, payload={"status": "ok"})
    async with ClientSession() as session:
        client = ShowdownHTTPClient(
            max_retries=1, base_backoff_sec=0.01, timeout_sec=1.0, session=session
        )
        result = await client.fetch_json(url)
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_fetch_json_retry_on_500(mock_aioresponse: aioresponses) -> None:
    url = "https://example.com/retry.json"
    mock_aioresponse.get(url, status=500)
    mock_aioresponse.get(url, status=500)
    mock_aioresponse.get(url, payload={"recovered": True})
    async with ClientSession() as session:
        client = ShowdownHTTPClient(
            max_retries=3, base_backoff_sec=0.01, timeout_sec=1.0, session=session
        )
        result = await client.fetch_json(url)
    assert result == {"recovered": True}
