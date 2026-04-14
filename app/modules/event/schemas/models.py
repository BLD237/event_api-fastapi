from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class EventObject(BaseModel):
    id: str
    title: str
    imageUrl: Optional[str] = None
    additionalImages: list[str] = []
    description: Optional[str] = None
    date: str
    time: str
    location: str
    price: float
    category: str
    attendees: int


class EventListResponseData(BaseModel):
    events: list[EventObject]
    total: int
    page: int
    limit: int


class CategoryObject(BaseModel):
    id: str
    name: str
    iconUrl: str


class TrendingSearch(BaseModel):
    icon: str
    text: str


class NearbyVenue(BaseModel):
    name: str
    events: int
    distance: str


class ExploreResponseData(BaseModel):
    trendingSearches: list[TrendingSearch]
    nearbyVenues: list[NearbyVenue]
    exploreEvents: list[EventObject]


class EventCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    imageUrl: Optional[str] = None
    additionalImages: list[str] = []
    date: str
    time: str
    location: str
    price: float
    category: str
    total_tickets: int = 100


class EventUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    imageUrl: Optional[str] = None
    additionalImages: Optional[list[str]] = None
    date: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    price: Optional[float] = None
    category: Optional[str] = None
