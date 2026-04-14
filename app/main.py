import logging
import time
import uuid
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response as StarletteResponse
from pathlib import Path

from app.core.response import ApiResponse, error_response, success_response
from app.core.config import get_settings
from app.db.session import (
    get_profiles_collection,
    get_event_favorites_collection,
    get_users_collection,
    get_events_collection,
    get_bookings_collection,
    get_reviews_collection,
)

# Import module routers
from app.modules.auth.router import router as auth_router
from app.modules.event.router import router as event_router
from app.modules.booking.router import router as booking_router
from app.modules.favorite.router import router as favorite_router
from app.modules.review.router import router as review_router
from app.modules.profile.router import router as profile_router

from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="Event Application API", version="1.0.0")

# Prefix all routes with /api/v1 as per specs
api_v1 = FastAPI()

api_v1.include_router(auth_router)
api_v1.include_router(event_router)
api_v1.include_router(booking_router)
api_v1.include_router(favorite_router)
api_v1.include_router(review_router)
api_v1.include_router(profile_router)

app.mount("/api/v1", api_v1)

# Serve uploaded files
storage_dir = Path(__file__).resolve().parents[1] / "storage"
app.mount("/storage-files", StaticFiles(directory=storage_dir), name="storage-files")

logger = logging.getLogger("event_api.http")

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled exception (request_id=%s)", request_id)
        raise

    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-ms"] = f"{duration_ms:.2f}"
    
    return response

@app.get("/")
async def root():
    return success_response(message="Event API v1.0.0. Use /api/v1/ endpoints")

@app.post("/db/init", response_model=ApiResponse, status_code=status.HTTP_200_OK)
async def init_db():
    users_collection = get_users_collection()
    profiles_collection = get_profiles_collection()
    events_collection = get_events_collection()
    favorites_collection = get_event_favorites_collection()
    bookings_collection = get_bookings_collection()
    reviews_collection = get_reviews_collection()

    await users_collection.create_index("email", unique=True)
    await profiles_collection.create_index("user_id", unique=True)
    await events_collection.create_index([("geo", "2dsphere")])
    await favorites_collection.create_index([("user_id", 1), ("event_id", 1)], unique=True)
    await bookings_collection.create_index("bookingId", unique=True)
    await reviews_collection.create_index([("user_id", 1), ("event_id", 1)])

    return success_response(message="Database initialized")

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(message=str(exc.detail)).model_dump(mode="json"),
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422, 
        content=error_response(message="Validation error", data={"errors": exc.errors()}).model_dump(mode="json")
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Internal error")
    return JSONResponse(
        status_code=500, 
        content=error_response(message="Internal server error").model_dump(mode="json")
    )
