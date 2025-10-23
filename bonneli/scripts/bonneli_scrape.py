import time
import csv
import re
import sys
import unicodedata
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

import requests
from bs4 import BeautifulSoup

SERIES_SOURCES = [
    {"name": "Dylan Dog - Redovna serija", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Dylan%20Dog"},
    {"name": "Dylan Dog - Super Book", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Serie%20Super%20Book"},
    {"name": "Dylan Dog - Color Fest", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Dylan%20Dog%20Color%20Fest"},
    {"name": "Dylan Dog - Speciale", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Speciale%20Dylan%20Dog"},
    {"name": "Dylan Dog - Maxi", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Maxi%20Dylan%20Dog"},
    {"name": "Dylan Dog - Old Boy", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Dylan%20Dog%20Oldboy"},
    {"name": "Dylan Dog - Il Dylan Dog di Tiziano Sclavi", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Il%20Dylan%20Dog%20di%20Tiziano%20Sclavi"},
    {"name": "Dylan Dog - Almanacco della Paura", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Almanacco%20della%20Paura"},
    {"name": "Dylan Dog - Gigante", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Dylan%20Dog%20Gigante"},
    {"name": "Dylan Dog - Magazine", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Dylan%20Dog%20Magazine"},
    {"name": "Dylan Dog - I racconti di domani", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=I%20racconti%20di%20domani"},
    {"name": "Dylan Dog - Batman", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Dylan%20Dog%20Batman"},
    {"name": "Dylan Dog - Old Boy Seconda Serie", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Dylan%20Dog%20Oldboy%20Seconda%20Serie"},
    {"name": "Dylan Dog - L'Enciclopedia della Paura", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=L%E2%80%99Enciclopedia%20della%20Paura"},
    {"name": "Dylan Dog - Dylan Dog presenta Daryl Zed", "url": "https://www.sergiobonelli.it/sezioni/43/fumetti?tag_0=1&noinit=true&sortDefault=false&sortElement=tag_2,true&exact_match.tag_64=Dylan%20Dog&exact_match.tag_92=Dylan%20Dog%20presenta:%20Daryl%20Zed"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (personal-use scraper; github.com/example)",
    "Accept-Language": "en-US,en;q=0.9,hr;q=0.8,sr;q=0.7,it;q=0.6",
}
REQUEST_TIMEOUT = 25
REQUEST_DELAY = 0.6
MAX_EMPTY_PAGES = 2
FETCH_DETAIL = False

session = requests.Session()
session.headers.update(HEADERS)

def build_series_url(base_url: str, page: int) -> str:
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query, keep_blank_values=True)
    query["page"] = [str(page)]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

def get_soup(url: str) -> BeautifulSoup:
    for attempt in range(3):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1.5 + attempt)
    return BeautifulSoup("", "html.parser")

def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()

def extract_issue_number(text: str):
    text = text or ""
    match = re.search(r"(?:\bn\.\s*|\#)\s*(\d+)\b", text, flags=re.I)
    if match:
        return match.group(1)
    numbers = re.findall(r"\b(\d{1,4})\b", text)
    if numbers:
        return numbers[-1]
    return None

def extract_cards_from_list(soup: BeautifulSoup):
    cards = []
    for container in soup.select("div.cont_anteprima_ricerca_archivio div.anteprima_ricerca_archivio"):
        link = container.find("a", href=True)
        if not link:
            continue
        href = link.get("href", "").strip()
        if not href:
            continue
        if not href.startswith("http"):
            href = requests.compat.urljoin("https://www.sergiobonelli.it/", href)
        img = link.find("img")
        title = ""
        if img:
            title = img.get("title") or img.get("alt") or ""
        if not title:
            title = link.get("title") or link.get_text(" ", strip=True)
        title = normalize_space(title)
        if not title:
            continue
        tags = {}
        for tag in container.select("p.vc_tag"):
            tag_cls = next((cls for cls in tag.get("class", []) if cls.startswith("tag_")), None)
            if not tag_cls:
                continue
            name_node = tag.select_one(".nome")
            value_node = tag.select_one(".valore")
            nome = normalize_space(name_node.get_text(" ", strip=True) if name_node else "")
            valore = normalize_space(value_node.get_text(" ", strip=True) if value_node else "")
            data_value = value_node.get("data-tag_value", valore) if value_node else valore
            tags[tag_cls] = {"nome": nome, "valore": valore, "data": data_value}
        cards.append({"url": href, "title_guess": title, "tags": tags})
    if not cards:
        for container in soup.select("div.article_cont"):
            article = container.find("article")
            if not article:
                continue
            link = article.find("a", href=True)
            if not link:
                continue
            href = link.get("href", "").strip()
            if not href:
                continue
            if not href.startswith("http"):
                href = requests.compat.urljoin("https://www.sergiobonelli.it/", href)
            title_node = article.find(["h2", "h3"])
            title = normalize_space(title_node.get_text(" ", strip=True) if title_node else link.get_text(" ", strip=True))
            if len(title) < 3:
                continue
            cards.append({"url": href, "title_guess": title, "tags": {}})
    if not cards:
        for link in soup.select("a[href*='/scheda/']"):
            href = link.get("href", "")
            if not href:
                continue
            if not href.startswith("http"):
                href = requests.compat.urljoin("https://www.sergiobonelli.it/", href)
            title = normalize_space(link.get_text(" ", strip=True))
            if len(title) < 3:
                continue
            cards.append({"url": href, "title_guess": title, "tags": {}})
    unique = {}
    for card in cards:
        unique[card["url"]] = card
    return list(unique.values())

def extract_series_from_breadcrumb(soup: BeautifulSoup):
    known = [
        "Dylan Dog", "Dylan Dog Oldboy", "Old Boy", "Oldboy",
        "Maxi Dylan Dog", "Dylan Dog Maxi",
        "Color Fest", "Dylan Dog Color Fest",
        "Gigante", "Dylan Dog Gigante",
        "Granderistampa", "Dylan Dog Magazine", "Magazine",
        "Cartonati", "Speciale", "SuperBook", "I Nuovi Incubi",
        "Caccia all'Invisibile", "Collezione Book", "Collezione",
    ]
    crumbs = [normalize_space(node.get_text(strip=True)) for node in soup.select(".breadcrumb a, nav a, .breadcrumbs a")]
    header = soup.find(["h1", "h2"])
    if header:
        crumbs.append(normalize_space(header.get_text(strip=True)))
    meta_sections = soup.find("meta", attrs={"name": "sections"})
    if meta_sections:
        parts = [normalize_space(part) for part in meta_sections.get("content", "").split(",")]
        crumbs.extend([part for part in parts if part])
    best = None
    for crumb in crumbs:
        for candidate in known:
            if candidate.lower() in crumb.lower():
                if not best or len(candidate) > len(best):
                    best = candidate
    fallback = next((crumb for crumb in crumbs if crumb), None)
    return best or fallback or "Dylan Dog"

def extract_release_date(soup: BeautifulSoup):
    block = soup.get_text(" ", strip=True)
    match = re.search(r"(?:Release|Uscita)\s*:\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{2,4})", block, flags=re.I)
    if match:
        return match.group(1)
    return None

def extract_from_detail(url: str):
    soup = get_soup(url)
    header = soup.find(["h1", "h2"])
    page_title = normalize_space(header.get_text(strip=True) if header else "")
    series = extract_series_from_breadcrumb(soup)
    issue_no = extract_issue_number(page_title)
    release = extract_release_date(soup)
    return series, issue_no, page_title, release

def normalize_tag_label(raw_label: str):
    label = normalize_space(raw_label).strip(" :")
    if not label:
        return None
    label = label.replace("°", "").replace("º", "")
    label = "".join(ch for ch in unicodedata.normalize("NFKD", label) if not unicodedata.combining(ch))
    label = normalize_space(label)
    lower = label.lower()
    if lower in {"n", "no", "numero", "num"}:
        return "Broj"
    if lower == "uscita":
        return "Uscita"
    if lower == "periodicita":
        return "Periodicita"
    if lower == "prezzo":
        return "Prezzo"
    return label

def process_card(series_name: str, card: dict):
    issue_no = extract_issue_number(card.get("title_guess", ""))
    page_title = card.get("title_guess", "")
    release = ""
    if FETCH_DETAIL:
        try:
            detail_series, detail_issue, detail_title, detail_release = extract_from_detail(card["url"])
            if detail_title:
                page_title = detail_title
            if detail_issue:
                issue_no = detail_issue
            if detail_release:
                release = detail_release
            time.sleep(REQUEST_DELAY)
        except Exception as exc:
            print(f"  [WARN] Problem sa detaljem: {card['url']} -> {exc}", file=sys.stderr)
    tag_values = {}
    for info in card.get("tags", {}).values():
        label = normalize_tag_label(info.get("nome", ""))
        if not label:
            continue
        raw_value = info.get("data") or info.get("valore") or ""
        value = normalize_space(raw_value)
        if not value:
            continue
        tag_values.setdefault(label, value)
    if "Broj" not in tag_values and issue_no:
        tag_values["Broj"] = issue_no
    if "Uscita" not in tag_values and release:
        tag_values["Uscita"] = release
    row = {
        "series": series_name,
        "title": page_title,
        "url": card["url"],
    }
    row.update(tag_values)
    return row, set(tag_values.keys())

def collect_series(series_name: str, base_url: str):
    rows = []
    tag_labels = set()
    seen_urls = set()
    page = 1
    empty_pages = 0
    while True:
        page_url = build_series_url(base_url, page)
        print(f"[{series_name}] [PAGE {page}] {page_url}")
        soup = get_soup(page_url)
        cards = extract_cards_from_list(soup)
        cards = [card for card in cards if card["url"] not in seen_urls]
        for card in cards:
            seen_urls.add(card["url"])
        if not cards:
            empty_pages += 1
            if empty_pages >= MAX_EMPTY_PAGES:
                print(f"[{series_name}] nema vise rezultata. Prelazim dalje.")
                break
            page += 1
            time.sleep(REQUEST_DELAY)
            continue
        empty_pages = 0
        for idx, card in enumerate(cards, 1):
            row, used_tags = process_card(series_name, card)
            rows.append(row)
            tag_labels.update(used_tags)
            if idx % 10 == 0:
                print(f"  ... obrada {idx}/{len(cards)} na strani {page}")
        page += 1
        time.sleep(REQUEST_DELAY)
    print(f"[{series_name}] ukupno {len(rows)} stavki")
    return rows, tag_labels

def build_tag_columns(all_tags):
    preferred = ["Broj", "Uscita", "Periodicita", "Prezzo"]
    ordered = [tag for tag in preferred if tag in all_tags]
    remaining = sorted(tag for tag in all_tags if tag not in ordered)
    ordered.extend(remaining)
    return ordered

def main():
    out_csv = "bonelli_dylan_dog_all.csv"
    all_rows = []
    all_tags = set()
    total = 0
    for entry in SERIES_SOURCES:
        series_rows, series_tags = collect_series(entry["name"], entry["url"])
        all_rows.extend(series_rows)
        all_tags.update(series_tags)
        total += len(series_rows)
    if not all_rows:
        print("Nisam pronasao stavke - proveri filtere/URL/selektore.")
        return
    fieldnames = ["series", "title", "url"] + build_tag_columns(all_tags)
    with open(out_csv, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)
    print(f"\nSacuvan CSV: {out_csv} (ukupno {total} stavki)")

if __name__ == "__main__":
    main()
