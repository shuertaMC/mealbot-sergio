import pytest
from httpx import ASGITransport, AsyncClient

from mealbot.main import app


class TestStaticFiles:
    async def test_privacy_html_accessible(self):
        """privacy.html is accessible at /privacy.html."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/privacy.html")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "Privacy Policy" in resp.text

    async def test_sample_csv_accessible(self):
        """sample.csv is accessible at /sample.csv."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            resp = await c.get("/sample.csv")
        assert resp.status_code == 200
        assert "csv" in resp.headers.get("content-type", "")
        assert "Name,Email" in resp.text
