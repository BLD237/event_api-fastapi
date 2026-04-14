from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_motor_client() -> AsyncIOMotorClient:
    settings = get_settings()
    return AsyncIOMotorClient(settings.mongodb_uri)


def get_database():
    client = get_motor_client()
    return client[get_settings().mongodb_db]


def get_users_collection():
    return get_database()["users"]


def get_profiles_collection():
    return get_database()["profiles"]


def get_storage_collection():
    return get_database()["storage_resources"]


def get_events_collection():
    return get_database()["events"]


def get_event_likes_collection():
    return get_database()["event_likes"]


def get_event_favorites_collection():
    return get_database()["event_favorites"]


def get_bookings_collection():
    return get_database()["bookings"]


def get_reviews_collection():
    return get_database()["reviews"]
