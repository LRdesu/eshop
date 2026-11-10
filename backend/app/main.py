from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    auth, catalog, cart, orders, payments, shipments, aftersales, reviews, members, addresses,
    admin, shops, favorites, follows, coupons, activities, shop_ai,
)

app = FastAPI(title="模拟电商平台", version="0.2")

app.add_middleware(
    CORSMiddleware,
    # 演示环境只用具体开发源；`*` 与 allow_credentials=True 互斥，浏览器会拒绝带凭据的 `*`
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, catalog, cart, orders, payments, shipments, aftersales, reviews, members, addresses, admin, shops, favorites, follows, coupons, activities, shop_ai):
    app.include_router(r.router)


@app.get("/health")
def health():
    return {"code": 0, "msg": "ok", "data": None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
