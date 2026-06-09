import pytest
from fastapi import UploadFile
from io import BytesIO
from app.routers.generate import analyze_pkt_file
import asyncio

@pytest.mark.asyncio
async def test_analyze_pkt_file_size_limit():
    # Create a mock file larger than 10MB
    large_content = b"a" * (10 * 1024 * 1024 + 1)
    mock_file = UploadFile(filename="test.pkt", file=BytesIO(large_content), size=len(large_content))

    with pytest.raises(Exception) as excinfo:
        await analyze_pkt_file(file=mock_file)

    # Check if the right exception is raised.
    # Since api_error returns HTTPException, we check for that.
    assert excinfo.value.status_code == 413
    assert "File size exceeds 10MB limit" in excinfo.value.detail

@pytest.mark.asyncio
async def test_analyze_pkt_file_small_file():
    # Create a small mock file (empty or small)
    # It will fail later on decryption, but it should pass the size check.
    small_content = b"a" * 100
    mock_file = UploadFile(filename="test.pkt", file=BytesIO(small_content), size=len(small_content))

    # We expect it to pass the size check and then fail on pkt_data = await file.read() or decryption
    # If it fails with 400 (Uploaded file is empty) or 200 (if we provide valid-ish data), it means it passed 413.
    try:
        await analyze_pkt_file(file=mock_file)
    except Exception as exc:
        if hasattr(exc, "status_code"):
            assert exc.status_code != 413
