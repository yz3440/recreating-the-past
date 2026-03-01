from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class BookCreate(BaseModel):
    title: str
    subtitle: Optional[str] = None
    author: Optional[str] = None
    publisher: str = "MIT Press"
    year: Optional[int] = None
    isbn: Optional[str] = None
    pages: Optional[int] = None
    dimensions: Optional[str] = None
    description: Optional[str] = None
    design_notes: Optional[str] = None
    source_url: Optional[str] = None


class CoverResponse(BaseModel):
    id: int
    book_id: int
    filename: str
    original_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    is_primary: bool = False


class BookResponse(BaseModel):
    id: int
    title: str
    subtitle: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    year: Optional[int] = None
    isbn: Optional[str] = None
    pages: Optional[int] = None
    dimensions: Optional[str] = None
    description: Optional[str] = None
    design_notes: Optional[str] = None
    source_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    covers: list[CoverResponse] = []


class BookListResponse(BaseModel):
    books: list[BookResponse]
    total: int
