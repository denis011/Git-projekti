from pathlib import Path
from typing import List, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import EDITIONS, app as api_app


BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

web_app = FastAPI(title="Strip Scraper UI", version="0.1")
web_app.mount("/api", api_app)


def edition_options() -> List[Tuple[str, str]]:
    """
    Returns list of (slug, human_name) pairs for rendering selection inputs.
    """
    return [(slug, cfg["name"]) for slug, cfg in EDITIONS.items()]


@web_app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "edition_options": edition_options(),
        },
    )


@web_app.post("/scrape", response_class=RedirectResponse)
async def trigger_scrape(edition_slug: str = ""):
    """
    HTML form POST helper that redirects back to the main page.
    Actual scrape happens client-side via fetch; this endpoint exists so that
    browsers submitted via standard form POST have a defined behaviour.
    """
    url = "/"
    if edition_slug:
        url += f"?edition={edition_slug}"
    return RedirectResponse(url=url, status_code=303)


__all__ = ["web_app"]
