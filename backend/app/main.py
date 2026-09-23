from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers.account import router as account_router
from app.routers.admin_home import router as admin_home_router
from app.routers.admin_menu import router as admin_menu_router
from app.routers.admin_orders import router as admin_orders_router
from app.routers.auth import router as auth_router
from app.routers.catalog import router as catalog_router
from app.routers.health import router as health_router
from app.routers.media import router as media_router
from app.routers.orders import router as orders_router
from app.routers.reviews import admin_router as admin_reviews_router
from app.routers.reviews import customer_router as customer_reviews_router
from app.routers.reviews import public_router as public_reviews_router

settings = get_settings()

app = FastAPI(
    title="Nosh API",
    summary="Local direct-ordering demo API.",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(account_router)
app.include_router(customer_reviews_router)
app.include_router(admin_home_router)
app.include_router(admin_menu_router)
app.include_router(admin_orders_router)
app.include_router(admin_reviews_router)
app.include_router(catalog_router)
app.include_router(public_reviews_router)
app.include_router(media_router)
app.include_router(orders_router)
