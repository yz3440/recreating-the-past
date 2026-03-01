# Muriel Cooper — Book Designs

A local database of books designed by [Muriel Cooper](https://en.wikipedia.org/wiki/Muriel_Cooper) (1925–1994), the first design director of MIT Press. An AI-powered scraping agent discovers books, verifies attribution, downloads cover images, and stores everything in SQLite. A FastAPI server presents the collection through a Swiss-grid styled frontend.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue) ![uv](https://img.shields.io/badge/pkg-uv-blueviolet)

## Setup

```bash
# Clone and install
git clone https://github.com/yz3440/muriel-cooper-book-designs.git
cd muriel-cooper-book-designs
uv sync

# Add your Anthropic API key
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
```

## Usage

### 1. Run the scraper

```bash
uv run python -m src.agent
```

The agent uses Claude Sonnet 4.6 with Anthropic's built-in web search to discover Muriel Cooper's book designs. It runs for up to 50 iterations (configurable in `src/config.py`), saving book metadata and cover images to a local SQLite database.

Every book saved must include a `source_url` — the page that credits Cooper as the designer — so results are verifiable.

### 2. Browse the collection

```bash
uv run python -m src.server
```

Open [http://localhost:8000](http://localhost:8000). The frontend provides:

- Grid and list views of all cataloged books
- Search by title or author
- Filter by year range
- Click any book for full metadata and all downloaded cover images

## Project Structure

```
src/
  config.py      Constants (MAX_ITERATIONS, DB path, model)
  models.py      Pydantic models
  db.py          SQLite schema and CRUD
  tools.py       Agent tool implementations (fetch_page, save_book, download_cover, list_saved_books)
  agent.py       Agentic scraping loop (Claude + web search)
  server.py      FastAPI app (API + frontend)

static/
  index.html     Single-file frontend (Tailwind CSS, Swiss grid)

data/
  books.db       SQLite database (created on first run)
  covers/        Downloaded cover images
```

## Configuration

Edit `src/config.py`:

| Variable | Default | Description |
|---|---|---|
| `MAX_ITERATIONS` | `50` | Agent loop stop count |
| `MODEL` | `claude-sonnet-4-6` | Claude model for scraping |

## API

| Endpoint | Description |
|---|---|
| `GET /api/books` | List books (query params: `search`, `year_from`, `year_to`, `sort`, `order`) |
| `GET /api/books/{id}` | Single book with covers |
| `GET /api/covers/{id}/image` | Serve a cover image |
| `GET /api/stats` | Total books, covers, year range |

## License

MIT
