"""Agent tool implementations for the Muriel Cooper book scraper."""

import hashlib
import json
import re
from io import BytesIO

import httpx
from bs4 import BeautifulSoup
from PIL import Image

from . import db
from .config import COVERS_DIR
from .models import BookCreate

TOOL_DEFINITIONS = [
    {
        "name": "fetch_page",
        "description": (
            "Fetch and parse the text content of a web page. Use this to read the full "
            "content of a page found via web search. Returns the main text content of "
            "the page, stripped of HTML tags and navigation elements. Maximum 50,000 "
            "characters returned."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the web page to fetch (must start with http:// or https://)",
                },
            },
            "required": ["url"],
        },
    },
    {
        "name": "save_book",
        "description": (
            "Save a book designed by Muriel Cooper to the database. If a book with the "
            "same title and author already exists, the existing record is updated with "
            "any new non-empty fields. Returns the book ID and whether it was created or updated. "
            "IMPORTANT: source_url is required — it must be the URL of a page that credits "
            "Muriel Cooper as the designer. The tool will warn if source_url is missing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "The full title of the book"},
                "author": {
                    "type": "string",
                    "description": "The book's author(s), not the designer. Comma-separated for multiple.",
                    "default": "",
                },
                "publisher": {
                    "type": "string",
                    "description": "Publisher name, usually 'MIT Press'",
                    "default": "MIT Press",
                },
                "year": {
                    "type": "integer",
                    "description": "Publication year as a 4-digit integer (e.g. 1969)",
                    "default": 0,
                },
                "isbn": {"type": "string", "description": "ISBN-10 or ISBN-13 if known", "default": ""},
                "pages": {"type": "integer", "description": "Number of pages if known", "default": 0},
                "dimensions": {
                    "type": "string",
                    "description": "Physical dimensions, e.g. '8.5 x 11 inches'",
                    "default": "",
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of the book's content",
                    "default": "",
                },
                "design_notes": {
                    "type": "string",
                    "description": "Notes about Muriel Cooper's design choices for this book",
                    "default": "",
                },
                "source_url": {
                    "type": "string",
                    "description": "REQUIRED. The URL of the page that confirms Muriel Cooper designed this book. Must be a real, verifiable URL.",
                },
            },
            "required": ["title", "source_url"],
        },
    },
    {
        "name": "download_cover",
        "description": (
            "Download a cover image for a book and save it to the local database. "
            "The image is downloaded, validated, and stored locally. The metadata "
            "is recorded in the covers table. The book must already exist in the database "
            "(save it first with save_book)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "book_title": {
                    "type": "string",
                    "description": "The exact title of the book (must match a book already in the database)",
                },
                "image_url": {
                    "type": "string",
                    "description": "The direct URL to the cover image file",
                },
                "is_primary": {
                    "type": "boolean",
                    "description": "Set to true if this is the main/best cover image for this book",
                    "default": False,
                },
            },
            "required": ["book_title", "image_url"],
        },
    },
    {
        "name": "list_saved_books",
        "description": (
            "List all books currently saved in the database. Returns a JSON array of "
            "objects with id, title, author, year, and cover_count fields. Use this to "
            "check what has already been saved and avoid duplicates, and to identify "
            "books that still need cover images."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


def _sanitize_filename(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower())
    return re.sub(r"[\s]+", "_", s).strip("_")[:60]


def execute_tool(name: str, input_data: dict) -> str:
    """Dispatch a tool call to its implementation. Returns the result as a string."""
    if name == "fetch_page":
        return _fetch_page(input_data["url"])
    elif name == "save_book":
        return _save_book(input_data)
    elif name == "download_cover":
        return _download_cover(
            input_data["book_title"],
            input_data["image_url"],
            input_data.get("is_primary", False),
        )
    elif name == "list_saved_books":
        return _list_saved_books()
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


def _fetch_page(url: str) -> str:
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Collapse blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text[:50000]
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch {url}: {str(e)}"})


def _save_book(data: dict) -> str:
    try:
        source_url = data.get("source_url", "").strip()
        if not source_url:
            return json.dumps({
                "error": "source_url is required. Please provide the URL of a page that "
                "confirms Muriel Cooper designed this book before saving.",
            })

        book = BookCreate(
            title=data["title"],
            subtitle=data.get("subtitle"),
            author=data.get("author", ""),
            publisher=data.get("publisher", "MIT Press"),
            year=data.get("year") if data.get("year") else None,
            isbn=data.get("isbn", ""),
            pages=data.get("pages") if data.get("pages") else None,
            dimensions=data.get("dimensions", ""),
            description=data.get("description", ""),
            design_notes=data.get("design_notes", ""),
            source_url=source_url,
        )
        book_id, created = db.upsert_book(book)
        return json.dumps({
            "book_id": book_id,
            "status": "created" if created else "updated",
            "title": book.title,
        })
    except Exception as e:
        return json.dumps({"error": f"Failed to save book: {str(e)}"})


def _download_cover(book_title: str, image_url: str, is_primary: bool = False) -> str:
    try:
        book_id = db.find_book_by_title(book_title)
        if book_id is None:
            return json.dumps({
                "error": f"Book not found in database: '{book_title}'. Save the book first with save_book.",
            })

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "image/*,*/*",
        }
        with httpx.Client(follow_redirects=True, timeout=30) as client:
            resp = client.get(image_url, headers=headers)
            resp.raise_for_status()

        img_data = resp.content
        img = Image.open(BytesIO(img_data))
        width, height = img.size

        # Skip very small images (likely thumbnails/icons)
        if width < 50 or height < 50:
            return json.dumps({"error": "Image too small (likely a thumbnail/icon), skipping."})

        # Resize if too large
        max_dim = 2000
        if width > max_dim or height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            width, height = img.size

        # Determine format
        fmt = img.format or "JPEG"
        ext = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}.get(fmt, "jpg")
        mime = f"image/{ext}" if ext != "jpg" else "image/jpeg"

        # Generate filename
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        filename = f"{book_id}_{_sanitize_filename(book_title)}_{url_hash}.{ext}"
        filepath = COVERS_DIR / filename

        # Save image
        if fmt == "JPEG" or ext == "jpg":
            img = img.convert("RGB")
            img.save(filepath, "JPEG", quality=90)
        else:
            img.save(filepath, fmt)

        file_size = filepath.stat().st_size
        cover_id = db.add_cover(
            book_id=book_id,
            filename=filename,
            original_url=image_url,
            width=width,
            height=height,
            file_size=file_size,
            mime_type=mime,
            is_primary=is_primary,
        )
        return json.dumps({
            "cover_id": cover_id,
            "book_id": book_id,
            "filename": filename,
            "width": width,
            "height": height,
            "file_size": file_size,
        })
    except Exception as e:
        return json.dumps({"error": f"Failed to download cover: {str(e)}"})


def _list_saved_books() -> str:
    try:
        with db.get_conn() as conn:
            rows = conn.execute(
                """SELECT b.id, b.title, b.author, b.year,
                          (SELECT COUNT(*) FROM covers c WHERE c.book_id = b.id) as cover_count
                   FROM books b ORDER BY b.year ASC, b.title ASC"""
            ).fetchall()
            books = [dict(r) for r in rows]
            return json.dumps({"books": books, "total": len(books)})
    except Exception as e:
        return json.dumps({"error": f"Failed to list books: {str(e)}"})
