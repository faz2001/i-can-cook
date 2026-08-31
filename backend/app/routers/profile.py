from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.models.favorite import Favorite
from app.models.pantry import PantryItem
from app.models.user import User
from app.schemas.profile import ChangePasswordIn, ProfileStatsOut, ProfileUpdate
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/stats", response_model=ProfileStatsOut)
def get_profile_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pantry_item_count = db.query(PantryItem).filter(PantryItem.user_id == current_user.id).count()
    favorites_count = db.query(Favorite).filter(Favorite.user_id == current_user.id).count()
    return ProfileStatsOut(pantry_item_count=pantry_item_count, favorites_count=favorites_count)


@router.patch("", response_model=UserOut)
def update_profile(
    payload: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Only fields actually present in the request body are touched --
    exclude_unset means omitting a field leaves it as-is, while explicitly
    sending an empty list (e.g. dietary_preferences: []) does clear it."""
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()
