"""FastAPI server for browsing the Muriel Cooper book designs database."""

from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

from . import db
from .config import COVERS_DIR, STATIC_DIR
from .models import BookListResponse, BookResponse

app = FastAPI(title="Muriel Cooper Book Designs")


@app.on_event("startup")
def startup():
    db.init_db()


@app.get("/api/books", response_model=BookListResponse)
def api_list_books(
    search: str = Query(default="", description="Search by title or author"),
    year_from: int = Query(default=0),
    year_to: int = Query(default=9999),
    sort: str = Query(default="year"),
    order: str = Query(default="asc"),
):
    books = db.list_books(search=search, year_from=year_from, year_to=year_to, sort=sort, order=order)
    return BookListResponse(books=books, total=len(books))


@app.get("/api/books/{book_id}", response_model=BookResponse)
def api_get_book(book_id: int):
    book = db.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.get("/api/covers/{cover_id}/image")
def api_cover_image(cover_id: int):
    cover = db.get_cover(cover_id)
    if not cover:
        raise HTTPException(status_code=404, detail="Cover not found")
    filepath = COVERS_DIR / cover.filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Cover file not found")
    return FileResponse(filepath, media_type=cover.mime_type or "image/jpeg")


@app.get("/api/stats")
def api_stats():
    return db.get_stats()


@app.get("/", response_class=HTMLResponse)
def index():
    index_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_path.read_text())


def main():
    import uvicorn
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
