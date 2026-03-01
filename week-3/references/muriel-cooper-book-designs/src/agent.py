"""AI-powered scraping agent for Muriel Cooper book designs."""

import json
import os
import uuid
import sys

from dotenv import load_dotenv
load_dotenv()

import anthropic

from . import db
from .config import MAX_ITERATIONS, MODEL
from .tools import TOOL_DEFINITIONS, execute_tool

SYSTEM_PROMPT = """\
You are a research assistant specializing in graphic design history.
Your task is to build a comprehensive database of books designed by Muriel Cooper,
the pioneering graphic designer who served as the first design director of MIT Press
from 1967 to 1974, and continued designing for MIT Press and other institutions afterward.

You have access to web search and tools to save books and download cover images.

## Your process:
1. Search for Muriel Cooper's book designs using web search
2. For each book you discover, extract the metadata (title, author, year, publisher, etc.)
3. Save the book to the database using the save_book tool
4. Search for high-quality cover images of each book
5. Download cover images using the download_cover tool
6. Use list_saved_books periodically to check your progress and find books still missing covers
7. Continue searching until you have found as many books as possible

## Known major works (start with these, then search broadly):
- Bauhaus 1919-1928 (1938, reprinted 1975) edited by Herbert Bayer, Walter Gropius, Ise Gropius
- The New Landscape in Art and Science (1956/1967) by Gyorgy Kepes
- Structure in Art and in Science (1965) by Gyorgy Kepes
- The Man-Made Object (1966) by Gyorgy Kepes
- Module, Proportion, Symmetry, Rhythm (1966) by Gyorgy Kepes
- Sign, Image, Symbol (1966) by Gyorgy Kepes
- The Nature and Art of Motion (1965) by Gyorgy Kepes
- Education of Vision (1965) by Gyorgy Kepes
- The Bauhaus: Weimar, Dessau, Berlin, Chicago (1969) by Hans Wingler
- Compendium for Literates (1971) by Karl Gerstner
- Civilia: The End of Sub Urban Man (1971) by Ivor de Wolfe
- Arts of the Environment (1972) by Gyorgy Kepes
- Learning from Las Vegas (1972) by Robert Venturi, Denise Scott Brown, Steven Izenour
- File Under Architecture (1974) by Herbert Muschamp
- All books in the MIT Press "Vision + Value" series by Gyorgy Kepes
- Numerous other MIT Press titles from 1962-1979

## CRITICAL — Source verification:
- EVERY book you save MUST include a source_url — the URL of the web page where you
  confirmed that Muriel Cooper designed it. This is non-negotiable. If you cannot find
  a source URL that explicitly credits Muriel Cooper as the designer, DO NOT save the book.
- After saving books, use list_saved_books to check for any entries missing source URLs.
  For those, search for a verifiable source and update them with save_book (which upserts).
  If you cannot find a source, note that in design_notes.
- Acceptable sources: museum/gallery pages, library catalog records, academic papers,
  design archive pages, exhibition catalogs, credible design history blogs/articles.
- The source_url should point to a page that specifically mentions Muriel Cooper
  as the designer/art director of that particular book.

## Important notes:
- Muriel Cooper designed over 500 books for MIT Press
- She also designed the MIT Press colophon (logo) — the seven vertical bars
- She worked at MIT's Office of Publications before MIT Press was formally established
- Search multiple sources: library catalogs, design archives, museum collections,
  design blogs, academic papers about her work
- When you find a book, save it immediately rather than batching saves
- Try to download at least one cover image per book when available
- For cover images, look for the largest/highest quality version available
- Mark the best cover image as is_primary=true
- Cross-reference information across multiple sources for accuracy
"""


def main():
    print("=" * 60)
    print("Muriel Cooper Book Designs — AI Scraper Agent")
    print(f"Model: {MODEL}")
    print(f"Max iterations: {MAX_ITERATIONS}")
    print("=" * 60)

    db.init_db()

    client = anthropic.Anthropic()
    run_id = str(uuid.uuid4())[:8]

    tools = [
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 25},
        *TOOL_DEFINITIONS,
    ]

    messages = [
        {
            "role": "user",
            "content": (
                "Begin researching and cataloging Muriel Cooper's book designs. "
                "Start by searching for comprehensive lists of her work, then work through "
                "each book systematically — saving metadata and downloading cover images. "
                "Be thorough and search multiple sources."
            ),
        },
    ]

    iteration = 0

    while iteration < MAX_ITERATIONS:
        iteration += 1
        print(f"\n{'─' * 40}")
        print(f"  Iteration {iteration}/{MAX_ITERATIONS}")
        print(f"{'─' * 40}")

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=16384,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
        except anthropic.APIError as e:
            print(f"  API error: {e}")
            db.log_iteration(run_id, iteration, "API_ERROR", None, str(e))
            break

        # Append assistant response to conversation
        messages.append({"role": "assistant", "content": response.content})

        # Process the response
        tool_results = []
        for block in response.content:
            if hasattr(block, "text") and block.text:
                print(f"  Agent: {block.text[:300]}")
                db.log_iteration(run_id, iteration, "text", None, block.text[:500])

            elif block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                print(f"  Tool: {tool_name}({json.dumps(tool_input)[:150]})")

                if tool_name == "web_search":
                    # Server-side tool — results appear in subsequent response
                    # No local execution needed
                    continue

                result = execute_tool(tool_name, tool_input)
                print(f"  Result: {result[:200]}")

                db.log_iteration(
                    run_id, iteration, tool_name,
                    json.dumps(tool_input)[:1000],
                    result[:500],
                )

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            elif block.type == "web_search_tool_result":
                print(f"  Web search results received")
                db.log_iteration(run_id, iteration, "web_search", None, "results received")

        # Handle stop reasons
        if response.stop_reason == "end_turn":
            print(f"\n  Agent finished (end_turn).")
            break

        if response.stop_reason == "pause_turn":
            print(f"  Agent paused, continuing...")
            # Feed the response back to continue
            continue

        if response.stop_reason == "tool_use" and tool_results:
            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "tool_use" and not tool_results:
            # Only server-side tool calls (web_search) — continue the conversation
            # The results are already in the response content
            pass

    # Print summary
    stats = db.get_stats()
    print(f"\n{'=' * 60}")
    print(f"Agent run complete. Run ID: {run_id}")
    print(f"Iterations used: {iteration}/{MAX_ITERATIONS}")
    print(f"Books found: {stats['total_books']}")
    print(f"Covers downloaded: {stats['total_covers']}")
    if stats["year_min"]:
        print(f"Year range: {stats['year_min']}–{stats['year_max']}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
