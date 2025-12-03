from fastapi import UploadFile, status, HTTPException


ALLOWED_IMAGE_TYPES = {
    "image/png": ".png",
    "image/jpg": ".jpg",
    "image/jpeg": ".jpeg",
    "image/webp": ".webp",
    "image/gif": ".gif"
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


async def validate_image(
    file: UploadFile,
    max_size: int = MAX_FILE_SIZE,
    allowed_types: dict = ALLOWED_IMAGE_TYPES
) -> dict:
    """
    Validate uploaded image file.

    Returns:
        dict with file info if valid

    Raises:
        HTTPException if invalid
    """

    # Check if file is empty
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )

    # Check file type
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Allowed: {', '.join(allowed_types.keys())}"
        )

    # Read and check size
    content = await file.read()
    file_size = len(content)

    # Reset pointer for later use
    await file.seek(0)

    if file_size > max_size:
        size_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size ({file_size / (1024*1024):.2f}MB) exceeds {size_mb}MB limit"
        )

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty"
        )

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": file_size,
        "valid": True
    }
