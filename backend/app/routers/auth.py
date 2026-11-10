from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User, Shop
from app.schemas import RegisterReq, LoginReq, TokenResp, UserResp
from app.utils.security import hash_password, verify_password, create_token
from app.utils.response import ok, fail

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register")
def register(req: RegisterReq, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        return fail("用户名已存在")
    if req.as_merchant and not req.shop_name:
        return fail("开店需填写店铺名称")
    u = User(
        username=req.username,
        password_hash=hash_password(req.password),
        phone=req.phone,
        nickname=req.nickname,
        role=1 if req.as_merchant else 0,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    if req.as_merchant:
        shop = Shop(
            name=req.shop_name,
            description=req.shop_description,
            logo=req.shop_logo,
            owner_user_id=u.id,
            status=1,
        )
        db.add(shop)
        db.commit()
    return ok(TokenResp(token=create_token(u.id), user_id=u.id,
                        username=u.username, nickname=u.nickname).model_dump(mode="json"))


@router.post("/login")
def login(req: LoginReq, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.username == req.username).first()
    if not u or not verify_password(req.password, u.password_hash):
        return fail("用户名或密码错误")
    return ok(TokenResp(token=create_token(u.id), user_id=u.id,
                        username=u.username, nickname=u.nickname).model_dump(mode="json"))


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return ok(UserResp.model_validate(user).model_dump(mode="json"))
