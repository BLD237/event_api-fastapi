from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from app.core.response import ApiResponse, success_response
from app.db.session import (
    get_event_favorites_collection,
    get_events_collection,
)
from app.modules.auth.router import get_current_user
from app.modules.event.crud.events import (
    find_event_by_id,
    list_events,
)
from app.modules.event.schemas.models import (
    EventObject,
    EventListResponseData,
    CategoryObject,
    ExploreResponseData,
    TrendingSearch,
    NearbyVenue
)

router = APIRouter(prefix="/events", tags=["events"])


def map_db_to_event(doc: dict) -> EventObject:
    # Handle date/time formatting if they are datetime objects
    date_str = doc.get("date")
    time_str = doc.get("time")
    
    if not date_str and "event_start_datetime" in doc:
        dt = doc["event_start_datetime"]
        if hasattr(dt, "strftime"):
            date_str = dt.strftime("%b %d, %Y")
    
    if not time_str and "event_start_datetime" in doc:
        dt = doc["event_start_datetime"]
        if hasattr(dt, "strftime"):
            time_str = dt.strftime("%I:%M %p")

    return EventObject(
        id=str(doc["_id"]),
        title=doc.get("title", ""),
        imageUrl=doc.get("imageUrl") or doc.get("cover_image_url"),
        additionalImages=doc.get("additionalImages") or doc.get("gallery_urls") or [],
        description=doc.get("description"),
        date=date_str or "Jan 1, 2025",
        time=time_str or "12:00 PM",
        location=doc.get("location") or doc.get("location_name") or "TBD",
        price=float(doc.get("price", 0)),
        category=doc.get("category", "General"),
        attendees=doc.get("attendees", 0)
    )


@router.get("", response_model=ApiResponse)
async def get_all_events(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    events_collection=Depends(get_events_collection),
):
    filter_doc = {}
    if search:
        filter_doc["title"] = {"$regex": search, "$options": "i"}
    if category:
        filter_doc["category"] = category

    items, total = await list_events(
        filter_doc=filter_doc,
        page=page,
        limit=limit,
        events_collection=events_collection,
    )

    events = [map_db_to_event(doc) for doc in items]

    return success_response(
        data=EventListResponseData(
            events=events,
            total=total,
            page=page,
            limit=limit
        ).model_dump()
    )


@router.get("/featured", response_model=ApiResponse)
async def get_featured_events(
    events_collection=Depends(get_events_collection),
):
    # For now, just take top 5 events as featured
    items, _ = await list_events(
        filter_doc={"is_featured": True},
        page=1,
        limit=5,
        events_collection=events_collection,
    )
    
    if not items:
        # Fallback to any 5 events if none are featured
        items, _ = await list_events(
            filter_doc={},
            page=1,
            limit=5,
            events_collection=events_collection,
        )

    events = [map_db_to_event(doc) for doc in items]
    return success_response(data={"featuredEvents": events})


@router.get("/popular", response_model=ApiResponse)
async def get_popular_events(
    events_collection=Depends(get_events_collection),
):
    # Sort by attendees descending
    cursor = events_collection.find({}).sort("attendees", -1).limit(5)
    items = await cursor.to_list(length=5)
    
    events = [map_db_to_event(doc) for doc in items]
    return success_response(data={"popularEvents": events})


@router.get("/categories", response_model=ApiResponse)
async def get_categories():
    categories = [
        CategoryObject(id="cat-1", name="Art", iconUrl="https://example.com/icons/art.png"),
        CategoryObject(id="cat-2", name="Music", iconUrl="https://example.com/icons/music.png"),
        CategoryObject(id="cat-3", name="Food", iconUrl="https://example.com/icons/food.png"),
        CategoryObject(id="cat-4", name="Tech", iconUrl="https://example.com/icons/tech.png"),
    ]
    return success_response(data={"categories": [c.model_dump() for c in categories]})


@router.get("/explore", response_model=ApiResponse)
async def get_explore_data(
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    events_collection=Depends(get_events_collection),
):
    # Aggregates data for explore page
    trending = [
        TrendingSearch(icon="trending_up", text="Music Festival"),
        TrendingSearch(icon="trending_up", text="Food Events"),
    ]
    
    nearby_venues = [
        NearbyVenue(name="Central Park", events=12, distance="2.5 km"),
        NearbyVenue(name="Convention Center", events=8, distance="5.0 km"),
    ]
    
    # Get some recommended events
    items, _ = await list_events(
        filter_doc={},
        page=1,
        limit=5,
        events_collection=events_collection,
    )
    explore_events = [map_db_to_event(doc) for doc in items]

    data = ExploreResponseData(
        trendingSearches=trending,
        nearbyVenues=nearby_venues,
        exploreEvents=explore_events
    )
    return success_response(data=data.model_dump())


@router.get("/{id}", response_model=ApiResponse)
async def get_event_details(
    id: str,
    events_collection=Depends(get_events_collection),
):
    try:
        oid = ObjectId(id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid event id")

    doc = await find_event_by_id(event_id=oid, events_collection=events_collection)
    if not doc:
        raise HTTPException(status_code=404, detail="Event not found")

    return success_response(data={"event": map_db_to_event(doc).model_dump()})
