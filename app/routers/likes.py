from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models.post_likes import PostLike
from app.db.models.idea import Idea
from app.core.dependencies import get_verified_user
from app.db.models.user import User

router = APIRouter(prefix="/posts", tags=["likes"])


@router.post("/{post_id}/like")
async def post_like(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_verified_user)
):
    """
    like on a post. If user already liked it, unlike it. Otherwise, like it.
    """
    # Check if post exists
    post_result = await db.execute(select(Idea).where(Idea.id == post_id))
    post = post_result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    # Check if user already liked this post
    like_result = await db.execute(
        select(PostLike).where(
            PostLike.post_id == post_id,
            PostLike.user_id == current_user.id
        )
    )
    existing_like = like_result.scalar_one_or_none()

    if existing_like:
        # Unlike: Remove the like and decrement count
        await db.delete(existing_like)
        # Prevent negative counts
        post.likes_count = max(0, post.likes_count - 1)
        await db.commit()

        return {
            "message": "disliked",
            "likes_count": post.likes_count
        }
    else:
        # Like: Add new like and increment count
        new_like = PostLike(
            post_id=post_id,
            user_id=current_user.id
        )
        db.add(new_like)
        post.likes_count += 1
        await db.commit()

        return {
            "message": "liked",
            "likes_count": post.likes_count
        }


@router.get("/{post_id}/likes")
async def get_likes_count(
    post_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the total like count for a post.
    """
    # Check if post exists and get likes count
    post_result = await db.execute(
        select(Idea.likes_count).where(Idea.id == post_id)
    )
    likes_count = post_result.scalar_one_or_none()

    if likes_count is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found"
        )

    return {"likes_count": likes_count}
