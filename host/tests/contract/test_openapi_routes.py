import pytest
from cameracommander.api.app import create_app

@pytest.mark.asyncio
async def test_app_creation():
    app = create_app()
    assert app.title == "CameraCommander2"
