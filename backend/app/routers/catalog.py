from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import catalog_service
from app.schemas import CategoryResp
from app.utils.response import ok

router = APIRouter(prefix="/api/v1/products", tags=["catalog"])


@router.get("/home")
def home(db: Session = Depends(get_db)):
    return ok(catalog_service.home_data(db))


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    return ok([CategoryResp.model_validate(c).model_dump(mode="json")
               for c in catalog_service.list_categories(db)])


@router.get("")
def list_products(
    keyword: str = None,
    category: str = None,
    category_id: int = None,
    shop_id: int = None,
    sort: str = "default",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    return ok(catalog_service.list_products(
        db, keyword, category, category_id, shop_id, sort, page, page_size
    ))


@router.get("/{product_id}")
def detail(product_id: int, db: Session = Depends(get_db)):
    return ok(catalog_service.get_product(db, product_id).model_dump(mode="json"))
