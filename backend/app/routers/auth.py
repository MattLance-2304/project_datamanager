from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import create_token, get_current_user, hash_password, verify_password
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, PasswordIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已停用，请联系管理员")
    return {"token": create_token(user), "user": UserOut.model_validate(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.put("/password")
def change_password(body: PasswordIn, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    db_user = db.get(User, user.id)
    if not verify_password(body.old_password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    db_user.password_hash = hash_password(body.new_password)
    db.commit()
    return {"ok": True}
