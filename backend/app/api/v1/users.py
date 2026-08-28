from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.v1.auth import get_current_user, require_role
from app.models.models import User, UserRole
from app.schemas.schemas import UserResponse, UserCreate, UserBase

router = APIRouter(prefix="/users", tags=["Users Management"])

@router.get("/", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    return db.query(User).all()

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db.delete(user)
    db.commit()
    return None
