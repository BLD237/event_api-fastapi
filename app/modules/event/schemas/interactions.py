from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class LikeFavoriteCounts(BaseModel):
    likes_count: int
    favorites_count: int


class LikeResponseData(BaseModel):
    event_id: str
    liked: bool
    likes_count: int


class FavoriteResponseData(BaseModel):
    event_id: str
    favorited: bool
    favorites_count: int


class FavoritesListItem(BaseModel):
    # Reuse event shape in list endpoint later if needed.
    event_id: str
    title: str
    description: Optional[str] = None
    price: str

