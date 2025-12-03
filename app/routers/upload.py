from fastapi import UploadFile, File, APIRouter, HTTPException, status, Depends
from cloudinary.uploader import upload
from typing import Optional, List

from app.core.image_validator import validate_image
from app.db.models.user import User
from app.core.dependencies import get_verified_user
from app.core.config import settings


router = APIRouter(prefix="/upload", tags=["Upload Image"])


@router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_images(
    files: Optional[List[UploadFile]] = File(None),
    current_user: User = Depends(get_verified_user)
):
    """
    Upload images to Cloudinary.
    Returns list of secure URLs.
    """

    uploaded_urls = []

    # Handle no files case
    if not files:
        return {
            "uploaded_urls": uploaded_urls,
            "total_uploaded": len(uploaded_urls)
        }
    if len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 5 images can be uploaded at once"
        )

    for file in files:
        try:
            # Validate the file
            await validate_image(file)

            # Upload to Cloudinary
            upload_result = upload(
                file.file,
                folder=settings.CLOUDINARY_FOLDER
            )
            secure_url = upload_result.get("secure_url")
            uploaded_urls.append(secure_url)

        except HTTPException as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{file.filename}' validation failed: {e.detail}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload '{file.filename}': {str(e)}"
            )
        finally:
            await file.close()

    return uploaded_urls
