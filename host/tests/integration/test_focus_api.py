import pytest
from httpx import AsyncClient
from cameracommander.api.app import create_app
from cameracommander.hardware.camera.mock import MockCameraAdapter

@pytest.mark.asyncio
async def test_focus_nudge_endpoint():
    camera = MockCameraAdapter()
    await camera.open()
    app = create_app(camera=camera)
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post("/api/camera/focus", json={"step_size": 2})
        assert response.status_code == 204
