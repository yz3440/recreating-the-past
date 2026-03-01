import json
import sqlite3
from contextlib import contextmanager

from .config import DB_PATH, COVERS_DIR
from .models import BookCreate, BookResponse, CoverResponse

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    subtitle TEXT,
    author TEXT,
    publisher TEXT DEFAULT 'MIT Press',
    year INTEGER,
    isbn TEXT,
    pages INTEGER,
    dimensions TEXT,
    description TEXT,
    design_notes TEXT,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title, author)
);

CREATE TABLE IF NOT EXISTS covers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    original_url TEXT,
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    mime_type TEXT DEFAULT 'image/jpeg',
    is_primary BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scrape_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    iteration INTEGER NOT NULL,
    tool_name TEXT,
    tool_input TEXT,
    tool_output_summary TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_books_title ON books(title);
CREATE INDEX IF NOT EXISTS idx_books_year ON books(year);
CREATE INDEX IF NOT EXISTS idx_covers_book_id ON covers(book_id);
CREATE INDEX IF NOT EXISTS idx_scrape_log_run_id ON scrape_log(run_id);
"""


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_book(book: BookCreate) -> tuple[int, bool]:
    """Insert or update a book. Returns (book_id, created)."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM books WHERE title = ? AND author = ?",
            (book.title, book.author or ""),
        ).fetchone()

        if existing:
            updates = {}
            for field in [
                "subtitle", "publisher", "year", "isbn", "pages",
                "dimensions", "description", "design_notes", "source_url",
            ]:
                val = getattr(book, field)
                if val is not None and val != "" and val != 0:
                    updates[field] = val
            if updates:
                set_clause = ", ".join(f"{k} = ?" for k in updates)
                set_clause += ", updated_at = CURRENT_TIMESTAMP"
                conn.execute(
                    f"UPDATE books SET {set_clause} WHERE id = ?",
                    [*updates.values(), existing["id"]],
                )
            return existing["id"], False
        else:
            cur = conn.execute(
                """INSERT INTO books (title, subtitle, author, publisher, year, isbn,
                   pages, dimensions, description, design_notes, source_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    book.title, book.subtitle, book.author or "",
                    book.publisher, book.year, book.isbn, book.pages,
                    book.dimensions, book.description, book.design_notes,
                    book.source_url,
                ),
            )
            return cur.lastrowid, True


def get_book(book_id: int) -> BookResponse | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not row:
            return None
        covers = _get_covers_for_book(conn, book_id)
        return BookResponse(**dict(row), covers=covers)


def list_books(
    search: str = "",
    year_from: int = 0,
    year_to: int = 9999,
    sort: str = "year",
    order: str = "asc",
) -> list[BookResponse]:
    valid_sorts = {"year", "title", "author"}
    sort = sort if sort in valid_sorts else "year"
    order = "DESC" if order.lower() == "desc" else "ASC"

    with get_conn() as conn:
        query = "SELECT * FROM books WHERE 1=1"
        params: list = []

        if search:
            query += " AND (title LIKE ? OR author LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        if year_from > 0:
            query += " AND year >= ?"
            params.append(year_from)
        if year_to < 9999:
            query += " AND year <= ?"
            params.append(year_to)

        query += f" ORDER BY {sort} {order}"
        rows = conn.execute(query, params).fetchall()

        books = []
        for row in rows:
            covers = _get_covers_for_book(conn, row["id"])
            books.append(BookResponse(**dict(row), covers=covers))
        return books


def _get_covers_for_book(conn: sqlite3.Connection, book_id: int) -> list[CoverResponse]:
    rows = conn.execute(
        "SELECT * FROM covers WHERE book_id = ? ORDER BY is_primary DESC, id ASC",
        (book_id,),
    ).fetchall()
    return [CoverResponse(**dict(r)) for r in rows]


def add_cover(
    book_id: int,
    filename: str,
    original_url: str | None = None,
    width: int | None = None,
    height: int | None = None,
    file_size: int | None = None,
    mime_type: str = "image/jpeg",
    is_primary: bool = False,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO covers (book_id, filename, original_url, width, height,
               file_size, mime_type, is_primary)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (book_id, filename, original_url, width, height, file_size, mime_type, is_primary),
        )
        return cur.lastrowid


def get_cover(cover_id: int) -> CoverResponse | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM covers WHERE id = ?", (cover_id,)).fetchone()
        return CoverResponse(**dict(row)) if row else None


def get_stats() -> dict:
    with get_conn() as conn:
        total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        total_covers = conn.execute("SELECT COUNT(*) FROM covers").fetchone()[0]
        year_range = conn.execute(
            "SELECT MIN(year), MAX(year) FROM books WHERE year IS NOT NULL AND year > 0"
        ).fetchone()
        return {
            "total_books": total_books,
            "total_covers": total_covers,
            "year_min": year_range[0] if year_range else None,
            "year_max": year_range[1] if year_range else None,
        }


def log_iteration(
    run_id: str,
    iteration: int,
    tool_name: str | None,
    tool_input: str | None,
    tool_output_summary: str | None,
):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO scrape_log (run_id, iteration, tool_name, tool_input, tool_output_summary)
               VALUES (?, ?, ?, ?, ?)""",
            (run_id, iteration, tool_name, tool_input, tool_output_summary),
        )


def find_book_by_title(title: str) -> int | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM books WHERE title LIKE ?", (f"%{title}%",)
        ).fetchone()
        return row["id"] if row else None


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DB_PATH}")
