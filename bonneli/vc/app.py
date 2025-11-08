import re
import time
import io
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode
from fastapi import FastAPI, Response, HTTPException, Query, Body
from fastapi.responses import StreamingResponse, JSONResponse

from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, Date, Text, select, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import delete
import pandas as pd
from slugify import slugify


BASE_URL = "https://veselicetvrtak.com"
EDITIONS = {
    "zagor-redovna-serija": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=zagor-redovna-serija&per_page=12",
        "name": "Zagor - redovna serija",
    },
    "zagor-odabrane-price": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=zagor-odabrane-price&per_page=12",
        "name": "Zagor - odabrane price",
    },
    "zagor-specijal": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=zagor-specijal&per_page=12",
        "name": "Zagor - specijal",
    },
    "zagor-biblioteka": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=biblioteka-zagor&per_page=12",
        "name": "Zagor - biblioteka",
    },
    "zagor-ciko": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=ciko&per_page=12",
        "name": "Zagor - Ciko",
    },
    "marti-redovna-serija": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=marti-misterija-redovna-serija&per_page=12",
        "name": "Marti Misterija - redovna serija",
    },
    "marti-biblioteka": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=biblioteka-marti-misterija&per_page=12",
        "name": "Marti Misterija - biblioteka",
    },
    "dilan-dog-redovna-serija": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=dilan-dog-redovna-serija&per_page=12",
        "name": "Dilan Dog - redovna serija",
    },
    "dilan-dog-super-book": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=dilan-dog-super-book&per_page=12",
        "name": "Dilan Dog - Super Book",
    },
    "dilan-dog-planeta-mrtvih": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=dilan-dog-planeta-mrtvih&per_page=12",
        "name": "Dilan Dog - Planeta mrtvih",
    },
    "dilan-dog-biblioteka": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=biblioteka-dilan-dog&per_page=12",
        "name": "Dilan Dog - Biblioteka",
    },
    "dilan-dog-predstavlja": {
        "list_url": "https://veselicetvrtak.com/katalog/dilan-dog/dilan-dog-predstavlja-price-iz-nekog-drugog-sutra?per_page=12",
        "name": "Dilan Dog predstavlja - Price iz nekog drugog sutra",
    },
    "biblioteka-obojeni-program": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=biblioteka-obojeni-program&per_page=12",
        "name": "Biblioteka - Obojeni program",
    },
    "zlatna-serija": {
        "list_url": "https://veselicetvrtak.com/izdanja/?filter_edicija=zlatna-serija&per_page=12",
        "name": "Nova Zlatna Serija",
    },
}
DEFAULT_EDITION_SLUG = "zagor-redovna-serija"
DEFAULT_EDICIJA = EDITIONS[DEFAULT_EDITION_SLUG]["name"]
DEFAULT_IZDAVAC = "Veseli Četvrtak"  # fallback ako ne nađemo na stranici

# --- DB setup ---
Base = declarative_base()
engine = create_engine("sqlite:///comics.db", future=True)
SessionLocal = sessionmaker(bind=engine, future=True)

class Comic(Base):
    __tablename__ = "comics"
    id = Column(Integer, primary_key=True)
    edicija = Column(String(255), nullable=False)
    naslov = Column(String(512), nullable=False)
    broj = Column(String(128), nullable=True)
    url = Column(String(1024), nullable=False)
    datum_objavljivanja = Column(Date, nullable=True)
    broj_originala = Column(String(128), nullable=True)
    naslov_originala = Column(String(512), nullable=True)
    opis = Column(Text, nullable=True)
    izdavac = Column(String(255), nullable=True)

    __table_args__ = (UniqueConstraint("url", name="uq_comic_url"),)

Base.metadata.create_all(engine)

app = FastAPI(title="Strip Scraper", version="0.1")

# --- Helpers ---

def get_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; StripScraper/0.1; +https://example.local)"
    })
    return s



def match_edition(value: str) -> Optional[Tuple[str, dict]]:
    value = (value or "").strip()
    if not value:
        return None
    if value in EDITIONS:
        return value, EDITIONS[value]
    value_cf = value.casefold()
    for slug, cfg in EDITIONS.items():
        if cfg["name"].casefold() == value_cf:
            return slug, cfg
    return None


def resolve_edition_with_default(value: Optional[str]) -> Tuple[str, dict]:
    if value is None or not value.strip():
        return DEFAULT_EDITION_SLUG, EDITIONS[DEFAULT_EDITION_SLUG]
    match = match_edition(value)
    if match:
        return match
    raise HTTPException(400, f"Nepoznata edicija: {value}")


def resolve_optional_edition(value: Optional[str]) -> Optional[Tuple[str, dict]]:
    if value is None:
        return None
    match = match_edition(value)
    if match:
        return match
    if value.strip():
        raise HTTPException(400, f"Nepoznata edicija: {value}")
    return None


def casefold_equals(a: Optional[str], b: Optional[str]) -> bool:
    return (a or "").casefold() == (b or "").casefold()


def with_per_page(url: str, per_page: Optional[int]) -> str:
    if not per_page:
        return url
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["per_page"] = str(per_page)
    new_query = urlencode(query, doseq=True)
    return parsed._replace(query=new_query).geturl()

def extract_labeled_value(full_text: str, label_regex: str, next_labels: list[str]) -> Optional[str]:
   
    followers = r"|".join([rf"(?:{lbl})\s*:" for lbl in next_labels])
    pattern = rf"(?i)\b(?:{label_regex})\s*:\s*(.+?)(?=\s*(?:{followers})|\n|$)"
    m = re.search(pattern, full_text)
    if not m:
        return None
    return clean_text(m.group(1))

def is_issue_detail_url(u: str) -> bool:
    """
    Prihvata samo URL-ove tipa /izdanja/<slug>/ (ne i /izdanja/?filter_...)
    """
    try:
        p = urlparse(u)
        # radimo sa path-om (bez domena); npr. '/izdanja/xxx/'
        path = p.path or ""
        parts = [seg for seg in path.split("/") if seg]
        # minimum: ['izdanja', '<slug>']
        if len(parts) < 2 or parts[0] != "izdanja":
            return False
        if p.query:
            return False
        if parts[1].lower() == "page":
            return False
        return True
    except Exception:
        return False


def normalize_issue_number(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    if value.isdigit():
        try:
            number = int(value)
        except ValueError:
            return value
        if number == 0:
            return None
        return str(number)
    return value


def parse_title_and_broj(raw_title: str) -> Tuple[str, Optional[str]]:
    """
    Pokušava da izdvoji broj iz naslova, npr:
    'Zagor 100: Naslov' -> broj='100', naslov='Zagor 100: Naslov' (ili očistiti po želji)
    Ako je format 'Zagor #25 – ' i sl., hvata najčešće slučajeve.
    """
    if not raw_title:
        return "", None
    # Traži sekvencu broja uz reči 'br', '#', ili nakon imena serije
    m = re.search(r'(?:(?:br\.?|#)\s*)?(\d{1,4})(?=[^\d]|$)', raw_title, flags=re.IGNORECASE)
    # ignorisi "-30%" i slične badge-ove; izbegni brojeve odmah posle % ili '-'
    # dozvoli formate: "Zagor 123", "Zagor #123", "br. 123", "Zagor 123: Naslov"
    m = re.search(
        r'(?<![%\-])\s*(?:br\.?|#)?\s*(\d{1,4})(?=[^\d]|$)',
        raw_title,
        flags=re.IGNORECASE
    )

    broj = normalize_issue_number(m.group(1)) if m else None
    return raw_title.strip(), broj

def clean_text(x: Optional[str]) -> Optional[str]:
    if x is None:
        return None
    return re.sub(r'\s+', ' ', x).strip()

def try_parse_date(s: str) -> Optional[datetime.date]:
    s = (s or "").strip().strip(".")
    s = re.sub(r"\s+", "", s)  # "23. 10. 2025." -> "23.10.2025."
    for fmt in ("%d.%m.%Y", "%d.%m.%Y.", "%Y-%m-%d", "%d.%m.%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def extract_field_by_label(soup: BeautifulSoup, labels: List[str]) -> Optional[str]:
    """
    Na mnogo WP tema detalji su u listama (dt/dd) ili tabelama.
    Pokuša razne obrasce: <th>Label</th><td>vrednost</td>, 'Label:' bold pa tekst itd.
    """
    text = soup.get_text(" ", strip=True)
    # fallback pretraga celog teksta za "Label: vrednost"
    for lbl in labels:
        m = re.search(rf"{re.escape(lbl)}\s*[:\-]\s*(.+?)\s{1,3}(?:[A-ZĆČŠĐŽ]|Datum|Broj|Naslov|Opis|Izdava|Edic|Autor|Scenar|Crt|$)", text, flags=re.IGNORECASE)
        if m:
            return clean_text(m.group(1))
    # strukturalno: dt/dd
    for dt in soup.select("dt, th, b, strong"):
        label_text = clean_text(dt.get_text())
        if not label_text:
            continue
        for lbl in labels:
            if lbl.lower() in label_text.lower():
                # pogledaj sledećeg brata/suseda
                dd = dt.find_next("dd") or dt.find_next("td") or dt.parent.find_next("td")
                if dd:
                    return clean_text(dd.get_text())
    return None

def scrape_list_urls(session: requests.Session, list_url: str) -> List[Tuple[str, str]]:
    """
    Vraća listu (title, url) sa strane edicije.
    Selektori su namerno "široki" ali ograničeni na grid sa izdanjima.
    """
    r = session.get(list_url, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    seen: Dict[str, str] = {}
    order: List[str] = []
    # Traži karte izdanja – često su <article>, <li> ili grid <div> sa linkom ka detaljima
    for a in soup.select("a[href]"):
        raw = a.get("href")
        if not raw:
            continue
        href = urljoin(BASE_URL, raw)          # <-- apsolutni URL
        if not is_issue_detail_url(href):      # <-- filtriraj samo detalje
            continue
        title = clean_text(a.get_text())
        if not title or len(title) < 3 or not any(ch.isalpha() for ch in title):
            # probaj iz title/aria-label atributa ako nema lep tekst
            title = clean_text(a.get("title") or a.get("aria-label") or "")
        if title and not any(ch.isalpha() for ch in title):
            title = ""

        if href not in seen:
            seen[href] = title
            order.append(href)
        elif title and len(title) > len(seen.get(href, "")):
            seen[href] = title

    return [(seen[u], u) for u in order]

def scrape_detail(session, url: str, default_edition_name: str) -> dict:
    r = session.get(url, timeout=30)
    soup = BeautifulSoup(r.text, "html.parser")

    # ---------- NASLOV + BROJ ----------
    # Uzmemo <h1> i odsečemo "Zagor <broj>" deo iz njega.
    h1 = soup.select_one("h1.entry-title, h1.elementor-heading-title, article h1, h1") or soup.title
    page_title_raw = clean_text(h1.get_text() if h1 else "")

    broj = None
    page_title = page_title_raw
    primary_match = re.match(
        r"^\s*Zagor\s+(?:[^\d]*?)?(\d{1,4})\s*[:\-–]?\s*(.+)$",
        page_title_raw,
        flags=re.IGNORECASE,
    )
    if primary_match:
        broj = primary_match.group(1)
        page_title = primary_match.group(2)  # npr. "Osveta bez kraja"
    else:
        inline_match = re.search(r"(\d{1,4})\s*[:\-–]\s*(.+)$", page_title_raw)
        if inline_match:
            broj = inline_match.group(1)
            page_title = inline_match.group(2).strip()
        else:
            _, broj_candidate = parse_title_and_broj(page_title_raw)
            broj = broj_candidate
            if broj_candidate:
                idx = page_title_raw.find(broj_candidate)
                if idx != -1:
                    potential = page_title_raw[idx + len(broj_candidate):]
                    potential = potential.lstrip(" :–-")
                    if potential:
                        page_title = potential.strip()

    broj = normalize_issue_number(broj)
    if not page_title:
        page_title = page_title_raw


    # ---------- OPIS ----------
    opis_block = soup.select_one(
        ".entry-content, .post-content, article .content, .post-entry, .elementor-widget-theme-post-content"
    )
    opis = clean_text(opis_block.get_text(" ")) if opis_block else None

    # ---------- METAPODACI (labela: vrednost) ----------
    full_text = soup.get_text("\n", strip=True)

    FOLLOWERS = [
        r"datum\s+objavljivanja",
        r"naslovna\s+strana",
        r"tekst",
        r"crtež",
        r"broj\s+originala",
        r"naslov\s+originala",
        r"edicija",
        r"izdavač",
    ]

    datum_raw = extract_labeled_value(full_text, r"datum\s+objavljivanja|datum\s+izdavanja|datum\s+objave", FOLLOWERS)
    broj_originala = extract_labeled_value(full_text, r"broj(?:evi)?\s+originala|original\s*#|original\s+broj", FOLLOWERS)
    naslov_originala = extract_labeled_value(full_text, r"naslov(?:i)?\s+originala|original\s+naslov|original\s+title", FOLLOWERS)

    # ---------- Dodatna polja ----------
    izdavac = extract_field_by_label(soup, ["Izdavač", "Publisher"]) or DEFAULT_IZDAVAC
    edicija = extract_field_by_label(soup, ["Edicija", "Serija"]) or default_edition_name

    # Datum parsiranje (skidamo razmake tipa "23. 10. 2025.")
    datum = try_parse_date(datum_raw) if datum_raw else None

    return {
        "page_title": page_title,                 # čisti naslov (bez "Zagor 231")
        "broj": broj,                             # npr. "231"
        "opis": opis,
        "datum_objavljivanja": datum.isoformat() if datum else None,
        "broj_originala": broj_originala,
        "naslov_originala": naslov_originala,
        "izdavac": izdavac,
        "edicija": edicija or default_edition_name
    }

def upsert_comic(db, data: dict):
    # upsert po URL-u
    url = data["url"]
    stmt = select(Comic).where(Comic.url == url)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        obj = Comic(
            edicija=data.get("edicija") or DEFAULT_EDICIJA,
            naslov=data.get("naslov") or "",
            broj=data.get("broj"),
            url=url,
            datum_objavljivanja=datetime.fromisoformat(data["datum_objavljivanja"]).date() if data.get("datum_objavljivanja") else None,
            broj_originala=data.get("broj_originala"),
            naslov_originala=data.get("naslov_originala"),
            opis=data.get("opis"),
            izdavac=data.get("izdavac") or DEFAULT_IZDAVAC
        )
        db.add(obj)
    else:
        obj.edicija = data.get("edicija") or obj.edicija
        obj.naslov = data.get("naslov") or obj.naslov
        obj.broj = data.get("broj") or obj.broj
        obj.datum_objavljivanja = datetime.fromisoformat(data["datum_objavljivanja"]).date() if data.get("datum_objavljivanja") else obj.datum_objavljivanja
        obj.broj_originala = data.get("broj_originala") or obj.broj_originala
        obj.naslov_originala = data.get("naslov_originala") or obj.naslov_originala
        obj.opis = data.get("opis") or obj.opis
        obj.izdavac = data.get("izdavac") or obj.izdavac

    db.commit()

# --- API ---

@app.post("/scrape")
def run_scrape(payload: Optional[dict] = Body(default=None)):
    edition_param = None
    per_page_raw: Optional[str] = None
    if payload:
        edition_param = (
            payload.get("edition_slug")
            or payload.get("slug")
            or payload.get("edicija")
        )
        per_page_raw = payload.get("per_page") or payload.get("perPage")
    edition_slug, edition_cfg = resolve_edition_with_default(edition_param)
    per_page_value: Optional[int] = None
    if per_page_raw not in (None, ""):
        try:
            per_page_value = int(per_page_raw)
        except (TypeError, ValueError):
            raise HTTPException(400, "Parametar per_page mora biti ceo broj.")
        if per_page_value <= 0:
            raise HTTPException(400, "Parametar per_page mora biti veći od nule.")

    session = get_session()
    list_url = with_per_page(edition_cfg["list_url"], per_page_value)
    pairs = scrape_list_urls(session, list_url)  # [(title, url)]
    per_page_effective: Optional[int] = per_page_value
    if per_page_effective is None:
        query_params = dict(parse_qsl(urlparse(list_url).query, keep_blank_values=True))
        candidate = query_params.get("per_page")
        if candidate and candidate.isdigit():
            per_page_effective = int(candidate)
    if not pairs:
        raise HTTPException(502, "Nisam prona\u0161ao nijedan strip na list stranici (promenjen HTML?).")

    imported = 0
    details = []
    with SessionLocal() as db:
        for title_from_list, url in pairs:
            time.sleep(0.6)
            detail = scrape_detail(session, url, edition_cfg["name"])
            fallback_title, fallback_broj = parse_title_and_broj(title_from_list or "")
            if fallback_title and not any(ch.isalpha() for ch in fallback_title):
                fallback_title = ""
            detail_broj = normalize_issue_number(detail.get("broj"))
            fallback_broj = normalize_issue_number(fallback_broj)
            broj = detail_broj or fallback_broj
            naslov = detail.get("page_title") or fallback_title or ""
            row = {
                "edicija": detail.get("edicija") or edition_cfg["name"],
                "naslov": naslov,
                "broj": broj,
                "url": url,
                "datum_objavljivanja": detail.get("datum_objavljivanja"),
                "broj_originala": detail.get("broj_originala"),
                "naslov_originala": detail.get("naslov_originala"),
                "opis": detail.get("opis"),
                "izdavac": detail.get("izdavac") or DEFAULT_IZDAVAC,
            }
            upsert_comic(db, row)
            imported += 1
            details.append({"naslov": row["naslov"], "url": url})
    return {
        "edition_slug": edition_slug,
        "edition_name": edition_cfg["name"],
        "per_page": per_page_effective,
        "list_url": list_url,
        "found": len(pairs),
        "imported_or_updated": imported,
        "sample": details[:5],
    }


@app.get("/comics")
def list_comics(edition_param: Optional[str] = Query(None, alias="edicija")):
    edition_filter = resolve_optional_edition(edition_param)
    edition_name = edition_filter[1]["name"] if edition_filter else None

    with SessionLocal() as db:
        rows = db.execute(select(Comic)).scalars().all()
        comics = []
        for r in rows:
            if not is_issue_detail_url(r.url or ""):
                continue
            if edition_name and not casefold_equals(r.edicija, edition_name):
                continue
            comics.append({
                "edicija": r.edicija,
                "naslov": r.naslov,
                "broj": r.broj,
                "url": r.url,
                "datum_objavljivanja": r.datum_objavljivanja.isoformat() if r.datum_objavljivanja else None,
                "broj_originala": r.broj_originala,
                "naslov_originala": r.naslov_originala,
                "opis": r.opis,
                "izdavac": r.izdavac,
            })
        return comics


@app.get("/export.xlsx")
def export_excel(edition_param: Optional[str] = Query(None, alias="edicija")):
    edition_filter = resolve_optional_edition(edition_param)
    edition_name = edition_filter[1]["name"] if edition_filter else None

    with SessionLocal() as db:
        rows = db.execute(select(Comic)).scalars().all()
        if not rows:
            return JSONResponse({"detail": "Baza je prazna. Prvo pokreni /scrape."}, status_code=400)

        data = []
        for r in rows:
            if not is_issue_detail_url(r.url or ""):
                continue
            if edition_name and not casefold_equals(r.edicija, edition_name):
                continue
            data.append({
                "izdavacka kuca": r.izdavac,
                "edicija": r.edicija,
                "broj": r.broj,
                "naslov": r.naslov,
                "broj originala": r.broj_originala,
                "naslov originala": r.naslov_originala,
                "datum objavljivanja": r.datum_objavljivanja.isoformat() if r.datum_objavljivanja else "",
                "url": r.url,
                "opis": r.opis or "",
            })
        if not data:
            return JSONResponse({"detail": "Za tra\u017eenu ediciju nema zapisa u bazi."}, status_code=404)

        df = pd.DataFrame(
            data,
            columns=[
                "izdavacka kuca",
                "edicija",
                "broj",
                "naslov",
                "broj originala",
                "naslov originala",
                "datum objavljivanja",
                "url",
                "opis",
            ],
        )

        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        buf.seek(0)
        filename = f"veseli_cetvrtak_{slugify(datetime.now().isoformat(timespec='seconds'))}.xlsx"
        return StreamingResponse(buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                 headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.delete("/comics")
def delete_comic(
    edition_param: str = Query(..., alias="edicija"),
    broj: str = Query(..., description="Broj izdanja veselog Četvrtka (ili * za sva izdanja)"),
):
    if not broj:
        raise HTTPException(400, "Parametar broj je obavezan.")

    edition_filter = resolve_optional_edition(edition_param)
    if not edition_filter:
        raise HTTPException(400, "Nepoznata edicija.")
    edition_name = edition_filter[1]["name"]

    delete_all = broj.strip() == "*"
    if delete_all:
        broj_normalized = None
    else:
        broj_normalized = normalize_issue_number(broj)
        if not broj_normalized:
            raise HTTPException(400, "Broj mora biti pozitivan ceo broj.")

    with SessionLocal() as db:
        stmt = (
            delete(Comic)
            .where(Comic.edicija == edition_name)
        )
        if not delete_all:
            stmt = stmt.where(Comic.broj == broj_normalized)

        result = db.execute(stmt)
        deleted_count = result.rowcount or 0
        db.commit()

    if deleted_count == 0:
        raise HTTPException(404, "Nije pronađen strip za zadate parametre.")

    return {
        "deleted": deleted_count,
        "edicija": edition_name,
        "broj": "*" if delete_all else broj_normalized,
    }
