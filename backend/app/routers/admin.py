from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import hash_password, require_admin
from ..database import get_db
from ..models import User
from ..schemas import UserCreateIn, UserOut, UserUpdateIn

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    users = db.query(User).order_by(User.id).all()
    return [UserOut.model_validate(u) for u in users]


@router.post("")
def create_user(body: UserCreateIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    if body.role not in ("admin", "member"):
        raise HTTPException(status_code=422, detail="角色只能是 admin 或 member")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    u = User(username=body.username, password_hash=hash_password(body.password),
             display_name=body.display_name or body.username, role=body.role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return UserOut.model_validate(u)


@router.put("/{user_id}")
def update_user(user_id: int, body: UserUpdateIn, db: Session = Depends(get_db),
                admin: User = Depends(require_admin)):
    u = db.get(User, user_id)
    if u is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if body.display_name is not None:
        u.display_name = body.display_name
    if body.role is not None:
        if body.role not in ("admin", "member"):
            raise HTTPException(status_code=422, detail="角色只能是 admin 或 member")
        if u.id == admin.id and body.role != "admin":
            raise HTTPException(status_code=400, detail="不能取消自己的管理员权限")
        u.role = body.role
    if body.is_active is not None:
        if u.id == admin.id and not body.is_active:
            raise HTTPException(status_code=400, detail="不能停用自己的账号")
        u.is_active = body.is_active
    if body.password:
        u.password_hash = hash_password(body.password)
    db.commit()
    db.refresh(u)
    return UserOut.model_validate(u)
