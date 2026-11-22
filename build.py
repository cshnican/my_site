#!/usr/bin/env python3
"""Build the site from the markdown files in content/."""

from html import escape
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
ALBUMS = ROOT / "old_site" / "assets" / "media" / "albums"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

FONTS = (
    "https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500"
    "&family=Fraunces:ital,opsz,wght@0,9..144,460;0,9..144,560;1,9..144,460"
    "&family=Outfit:wght@400;500;600"
    "&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400"
    "&display=swap"
)
FONTS_EL = (
    "https://fonts.googleapis.com/css2?family=Tinos:ital,wght@0,400;0,700;1,400;1,700&display=swap"
)

DEFAULTS = {
    "lang": "en",
    "selected": "Selected papers",
    "publications_title": "Publications",
    "all": "All",
    "menu": "Menu",
    "dark": "Dark",
    "light": "Light",
    "filters_label": "Filter papers",
    "cv_label": "CV",
    "switch_label": "ΕΛ",
    "footer_note": "",
    "description": "Sihan Chen, cognitive scientist at Universitat Pompeu Fabra.",
}

EL_DEFAULTS = {
    "switch_label": "EN",
    "selected": "Επιλεγμένες Δημοσιεύσεις",
    "publications_title": "Δημοσιεύσεις",
    "all": "Όλα",
    "menu": "Μενού",
    "dark": "Σκούρο",
    "light": "Ανοιχτό",
    "filters_label": "Φίλτρο δημοσιεύσεων",
    "cv_label": "CV",
    "footer_note": "",
    "description": "Ο Sihan Chen, γνωσιακός επιστήμονας στο Πανεπιστήμιο Πομπέου Φάβρα.",
    "filter_efficiency": "Αποδοτικότητα",
    "filter_society": "Κοινωνία",
    "filter_comprehension": "Κατανόηση",
}

BOLD = re.compile(r"\*\*(.+?)\*\*")
ITALIC = re.compile(r"(?<!\*)\*(.+?)\*(?!\*)")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
CAPTION = re.compile(r"^(.+\.(?:jpg|jpeg|png|webp|gif))\s*:\s*(.*)$", re.I)


def inline(text):
    """Turn a small bit of markdown into HTML."""
    pieces = []
    cursor = 0
    for match in LINK.finditer(text):
        pieces.append(emphasis(text[cursor:match.start()]))
        label = emphasis(match.group(1))
        href = escape(match.group(2), quote=True)
        pieces.append(f'<a href="{href}">{label}</a>')
        cursor = match.end()
    pieces.append(emphasis(text[cursor:]))
    return "".join(pieces)


def emphasis(text):
    text = escape(text)
    text = BOLD.sub(r"<strong>\1</strong>", text)
    text = ITALIC.sub(r"<em>\1</em>", text)
    return text


def parse_blocks(text):
    lines = text.splitlines()
    index = 0
    blocks = []
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("### "):
            blocks.append(("h3", line[4:].strip()))
            index += 1
        elif line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
            index += 1
        elif line.startswith("# "):
            blocks.append(("h1", line[2:].strip()))
            index += 1
        elif line.startswith("- "):
            items = []
            while index < len(lines) and lines[index].startswith("- "):
                items.append(lines[index][2:].strip())
                index += 1
            blocks.append(("ul", items))
        else:
            parts = [line.strip()]
            index += 1
            while index < len(lines) and lines[index].strip() and not lines[index].startswith(("#", "- ")):
                parts.append(lines[index].strip())
                index += 1
            blocks.append(("p", " ".join(parts)))
    return blocks


def split_sections(text):
    kept = []
    skipped_title = False
    for line in text.splitlines():
        if not skipped_title and line.startswith("# "):
            skipped_title = True
            continue
        kept.append(line)
    parts = re.split(r"(?m)^## ", "\n".join(kept))
    intro = parts[0]
    sections = []
    for part in parts[1:]:
        heading, _, rest = part.partition("\n")
        sections.append((heading.strip(), rest))
    return intro, sections


def parse_site(text):
    meta = {}
    sections = {}
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("# ") and not line.startswith("## "):
            continue
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
            continue
        if not line:
            continue
        if current:
            match = re.match(r"- \[(.+?)\]\((.+)\)$", line)
            if not match:
                raise SystemExit(f"Could not read a link in site.md: {line}")
            sections[current].append((match.group(1), match.group(2)))
        else:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, sections


def parse_papers(text):
    papers = []
    for chunk in re.split(r"(?m)^## ", text)[1:]:
        paper = {"year": "", "title": "", "authors": "", "venue": "", "pdf": "", "selected": None}
        lines = [line.strip() for line in chunk.splitlines() if line.strip()]
        if not lines:
            continue
        paper["year"] = lines[0]
        for line in lines[1:]:
            key, sep, value = line.partition(":")
            field = key.strip().lower()
            if sep and field in {"title", "authors", "venue", "pdf", "selected"}:
                paper[field] = value.strip()
            else:
                raise SystemExit(f"Unknown line in a paper entry: {line}")
        if paper["title"]:
            papers.append(paper)
    return papers


def parse_year_groups(body):
    groups = []
    year = None
    buffer = []

    def flush():
        if year is None:
            return
        lines = [line.strip() for line in buffer if line.strip()]
        title = lines[0] if lines else ""
        detail = " ".join(lines[1:])
        groups.append((year, title, detail))

    for line in body.splitlines():
        if line.startswith("### "):
            flush()
            year = line[4:].strip()
            buffer = []
        else:
            buffer.append(line)
    flush()
    return groups


def parse_gallery_section(body):
    album = ""
    default_alt = ""
    captions = {}
    prose = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("album:"):
            album = stripped.split(":", 1)[1].strip()
            continue
        if stripped.lower().startswith("alt:"):
            default_alt = stripped.split(":", 1)[1].strip()
            continue
        caption = CAPTION.match(stripped)
        if caption:
            captions[caption.group(1)] = caption.group(2).strip()
            continue
        prose.append(line)
    return album, default_alt, captions, "\n".join(prose)


def depth_of(site):
    return 0 if site.get("lang", "en") == "en" else 1


def content_dir(site):
    return CONTENT / site.get("lang", "en")


def output_dir(site):
    return ROOT if site.get("lang", "en") == "en" else ROOT / "el"


def read_content(site, name, fallback=False):
    path = content_dir(site) / name
    if path.exists():
        return path.read_text()
    if fallback:
        return (CONTENT / "en" / name).read_text()
    raise SystemExit(f"Missing {path}")


def rooted(path, depth):
    """Shift a path written for preview/ so it works from preview/el/ too."""
    if path.startswith(("http://", "https://", "mailto:", "#")):
        return path
    return "../" * depth + path


def pdf_href(path, depth):
    if path.startswith("http://") or path.startswith("https://"):
        return escape(path, quote=True)
    encoded = "/".join(quote(part) for part in rooted(path, depth).split("/"))
    return escape(encoded, quote=True)


def language_menu(site, filename):
    current = site.get("lang", "en")
    if current == "en":
        en_href = filename
        el_href = "el/index.html" if filename == "research.html" else f"el/{filename}"
        button = "English"
    else:
        en_href = "../" + filename
        el_href = filename
        button = "Ελληνικά"
    label = "Γλώσσα" if current == "el" else "Language"

    def option(href, lang, name):
        selected = ' aria-current="true"' if lang == current else ""
        return (
            f'<li><a href="{escape(href, quote=True)}" hreflang="{lang}" lang="{lang}"{selected}>{name}</a></li>'
        )

    items = "\n              ".join([
        option(en_href, "en", "English"),
        option(el_href, "el", "Ελληνικά"),
    ])
    return (
        f'<div class="lang">\n'
        f'          <button class="btn lang-toggle" type="button" lang="{current}" '
        f'aria-expanded="false" aria-haspopup="true" aria-controls="lang-menu">{escape(button)}'
        f'<span class="caret" aria-hidden="true"></span></button>\n'
        f'          <ul class="lang-menu" id="lang-menu" hidden aria-label="{escape(label)}">\n'
        f"              {items}\n"
        f"          </ul>\n"
        f"        </div>"
    )


def paper_article(paper, with_tags, depth):
    tags = ""
    if with_tags:
        tags = f' data-tags="{escape(paper["tags"])}"'
    if paper["pdf"]:
        link = f'<a class="pdf" href="{pdf_href(paper["pdf"], depth)}">PDF</a>'
    else:
        link = "<span></span>"
    authors = inline(paper["authors"])
    venue = f'<i>{escape(paper["venue"])}</i>' if paper["venue"] else ""
    separator = " · " if authors and venue else ""
    return (
        f'<article class="paper"{tags}>\n'
        f'            <span class="year">{escape(paper["year"])}</span>\n'
        f"            <div>\n"
        f'              <span class="paper-title">{escape(paper["title"])}</span>\n'
        f'              <span class="meta">{authors}{separator}{venue}</span>\n'
        f"            </div>\n"
        f"            {link}\n"
        f"          </article>"
    )


def tag_list(value):
    return [tag for tag in re.split(r"[\s,]+", value or "") if tag]


def article_html(blocks):
    parts = ['<section class="copy">']
    first_paragraph = True
    for kind, data in blocks:
        if kind == "h1":
            parts.append(f'<h1 class="page-title">{inline(data)}</h1>')
        elif kind == "h2":
            parts.append(f"<h2>{inline(data)}</h2>")
        elif kind == "h3":
            parts.append(f"<h3>{inline(data)}</h3>")
        elif kind == "ul":
            items = "\n".join(f"          <li>{inline(item)}</li>" for item in data)
            parts.append(f"<ul>\n{items}\n        </ul>")
        elif kind == "p":
            css = ' class="lead"' if first_paragraph else ""
            first_paragraph = False
            parts.append(f"<p{css}>{inline(data)}</p>")
    parts.append("</section>")
    return "\n        ".join(parts)


def media_html(groups):
    articles = []
    for year, title, outlet in groups:
        articles.append(
            '<article class="paper media">\n'
            f'            <span class="year">{escape(year)}</span>\n'
            "            <div>\n"
            f'              <span class="paper-title">{inline(title)}</span>\n'
            f'              <span class="meta">{escape(outlet)}</span>\n'
            "            </div>\n"
            "          </article>"
        )
    return "\n".join(articles)


def cards_html(groups):
    cards = ['<div class="cards">']
    for year, title, detail in groups:
        cards.append(
            "          <div class=\"step\">\n"
            f'            <span class="year">{escape(year)}</span>\n'
            "            <div>\n"
            f"              {inline(title)}\n"
            f"              <small>{inline(detail)}</small>\n"
            "            </div>\n"
            "          </div>"
        )
    cards.append("        </div>")
    return "\n".join(cards)


# Coordinates for the gallery place names, looked up once so the build stays offline.
PLACES = {
    "Acadia National Park, ME, USA": (44.3563, -68.2155),
    "Cape Cod, MA, USA": (41.7988, -69.9961),
    "Death Valley National Park, CA, USA": (36.4702, -117.0884),
    "Eibsee, Bavaria, Germany": (47.4582, 10.9708),
    "Monastery of Agios Nektarios, Aigina, Greece": (37.7480, 23.4841),
    "Aigina, Greece": (37.7467, 23.4306),
    "Lago d'Orta, Piedmont, Italy": (45.8193, 8.3943),
    "Plateau Rosa, Aosta Valley, Italy": (45.9322, 7.6941),
    "Lancaster, CA, USA": (34.6981, -118.1366),
    "Mount Whitney, CA, USA": (36.5786, -118.2921),
    "Badwater Basin, CA, USA": (36.2303, -116.7674),
    "Artist's Palette, CA, USA": (36.3636, -116.8024),
    "Zabriskie Point, CA, USA": (36.4200, -116.8123),
    "Dyrhóley, Iceland": (63.3988, -19.1266),
    "Kötlujökull, Iceland": (63.5922, -18.8538),
    "Svínafellsjökull, Iceland": (64.0227, -16.8027),
    "Jökulsárlón, Iceland": (64.0783, -16.2274),
    "Indjánahöfði, Iceland": (63.9274, -21.9925),
    "Fagradalsfjall, Iceland": (63.8894, -22.2884),
    "Cabo da Roca, Portugal": (38.7809, -9.4994),
    "Ilha Deserta, Portugal": (36.9659, -7.8710),
    "Bönigen, Switzerland": (46.6887, 7.8949),
    "Luzern, Switzerland": (47.0521, 8.3058),
    "Thimari / Θυμάρι, Greece": (37.6985, 23.9452),
    "Sounio / Σούνιο, Greece": (37.6501, 24.0263),
    "Delphi / Δελφοί, Greece": (38.4812, 22.5005),
    "Mykines / Μυκήνες, Greece": (37.7292, 22.7544),
    "Archaia Korinthos / Αρχαία Κόρινθος, Greece": (37.9051, 22.8764),
    "Nesso, Como, Italy": (45.9114, 9.1571),
    "İstanbul, Türkiye": (41.0064, 28.9759),
    "Bratislava, Slovakia": (48.1435, 17.1083),
    "Vienna, Austria": (48.2084, 16.3725),
    "Torino, Italy": (45.0678, 7.6825),
    "Lugano, Ticino, Switzerland": (46.0038, 8.9512),
    "Athens, Greece": (37.9756, 23.7348),
    "Salzburg, Austria": (47.7981, 13.0465),
    "Ljubljana, Slovenia": (46.0500, 14.5069),
    "Venezia, Italy": (45.4372, 12.3346),
    "Lisbon, Portugal": (38.7078, -9.1366),
    "Porto, Portugal": (41.1502, -8.6103),
    "Sevilla, Spain": (37.3886, -5.9953),
    "Carmona, Spain": (37.4718, -5.6413),
    "Fribourg / Freiburg, Switzerland": (46.8056, 7.1613),
    "Grindelwald, Switzerland": (46.6243, 8.0367),
    "Vaduz, Lichtenstein": (47.1393, 9.5228),
    "Arachova, Greece": (38.4801, 22.5842),
    "Budapest, Hungary": (47.4818, 19.1449),
    "Nafplio, Greece": (37.5659, 22.8069),
}


def caption_and_place(text):
    text = text.strip()
    if text.startswith("|"):
        return "", text[1:].strip()
    caption, separator, place = text.partition(" | ")
    if not separator:
        return text, ""
    return caption.strip(), place.strip()


def album_html(folder_name, label, default_alt, captions, depth):
    folder = ALBUMS / folder_name
    if not folder.is_dir():
        raise SystemExit(f"Gallery album not found: {folder}")
    images = sorted(path for path in folder.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)
    tags = []
    for path in images:
        caption, place = caption_and_place(captions.get(path.name, ""))
        alt = caption or default_alt or label
        src = rooted("old_site/assets/media/albums/" + quote(folder_name) + "/" + quote(path.name), depth)
        caption_attr = f' data-caption="{escape(caption, quote=True)}"' if caption else ""
        place_attr = f' data-place="{escape(place, quote=True)}"' if place else ""
        place_html = f'<span class="place">{escape(place)}</span>' if place else ""
        if caption and place:
            label_text = f"{caption}, {place}"
        else:
            label_text = caption or place or alt
        tags.append(
            f'<button type="button" class="shot" aria-label="{escape(label_text, quote=True)}"{caption_attr}{place_attr}>'
            f'<img src="{escape(src, quote=True)}" alt="{escape(alt)}" draggable="false">'
            f"{place_html}</button>"
        )
    body = "\n          ".join(tags)
    return f'<div class="album" aria-label="{escape(label)}">\n          {body}\n        </div>'


def gallery_places(sections):
    found = []
    seen = set()
    for _, body in sections:
        _, _, captions, _ = parse_gallery_section(body)
        for text in captions.values():
            _, place = caption_and_place(text)
            if place and place not in seen:
                seen.add(place)
                found.append(place)
    return found


def map_html(places, lang):
    missing = [place for place in places if place not in PLACES]
    if missing:
        raise SystemExit("No map coordinates for:\n" + "\n".join(missing))
    pins = [
        {"name": place, "lat": PLACES[place][0], "lon": PLACES[place][1]}
        for place in places
    ]
    payload = json.dumps(pins, ensure_ascii=False).replace("<", "\\u003c")
    label = "Τοποθεσίες" if lang == "el" else "Places"
    return (
        f'        <div class="place-map" role="region" aria-label="{escape(label)}"></div>\n'
        f'        <script type="application/json" id="place-map-data">{payload}</script>'
    )


def page_shell(site, filename, title, main, home=False, extra_head="", extra_scripts=""):
    depth = depth_of(site)
    brand_href = "#top" if home else "index.html"
    nav_label = "Κύρια" if site["lang"] == "el" else "Primary"

    def destination(href):
        if href.startswith("#") and not home:
            return "index.html" + href
        return href

    nav_links = []
    drawer_links = []
    for label, href in site["nav"]:
        dest = destination(href)
        current = ' aria-current="page"' if dest == filename else ""
        nav_links.append(f'<a href="{escape(dest, quote=True)}"{current}>{escape(label)}</a>')
        drawer_links.append(f'<a href="{escape(dest, quote=True)}">{escape(label)}</a>')

    footer_note = site["footer_note"] if home else ""
    email = site["email"]
    description = ""
    if home:
        description = (
            '\n  <meta name="description" '
            f'content="{escape(site["description"])}">'
        )
    main_id = ' id="top"' if home else ""
    fonts = FONTS_EL if site["lang"] == "el" else FONTS
    css = escape(rooted("site.css?v=16", depth), quote=True)
    script = escape(rooted("site.js?v=13", depth), quote=True)
    cv = escape(rooted(site["cv"], depth), quote=True)
    languages = language_menu(site, filename)
    return f"""<!DOCTYPE html>
<html lang="{escape(site["lang"])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>{description}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{fonts}" rel="stylesheet">
{extra_head}
  <link rel="stylesheet" href="{css}">
</head>
<body>
  <div class="chrome">
    <header class="nav">
      <a class="brand" href="{brand_href}">{escape(site["name"])}</a>
      <nav class="nav-links" aria-label="{escape(nav_label)}">
        {chr(10).join("        " + link for link in nav_links)}
      </nav>
      <div class="nav-actions">
        {languages}
        <button class="btn" id="theme-toggle" type="button" aria-pressed="false" data-dark="{escape(site["dark"])}" data-light="{escape(site["light"])}">{escape(site["dark"])}</button>
        <a class="btn solid" href="{cv}">{escape(site["cv_label"])}</a>
        <button class="btn menu-toggle" id="menu-toggle" type="button" aria-expanded="false" aria-controls="drawer">{escape(site["menu"])}</button>
      </div>
    </header>
    <div class="drawer" id="drawer">
      {chr(10).join("      " + link for link in drawer_links)}
    </div>
  </div>

  <main{main_id}>
    <div class="wrap">
{main}
    </div>
  </main>

  <footer>
    <div class="wrap foot">
      <span>{escape(site["footer"])}</span>
      <span><a href="mailto:{escape(email, quote=True)}">{escape(email)}</a>{escape(footer_note)}</span>
    </div>
  </footer>
{extra_scripts}
  <script src="{script}"></script>
</body>
</html>
"""


def filter_label(site, tag):
    custom = site.get(f"filter_{tag}")
    if custom:
        return custom
    return tag[:1].upper() + tag[1:] if tag else tag


def selected_section(papers, site):
    depth = depth_of(site)
    chosen = [paper for paper in papers if paper["selected"] is not None]
    for paper in chosen:
        paper["tags"] = " ".join(tag_list(paper["selected"]))
    used = []
    for paper in chosen:
        for tag in paper["tags"].split():
            if tag not in used:
                used.append(tag)
    preferred = ["efficiency", "society", "comprehension"]
    ordered = [tag for tag in preferred if tag in used] + [tag for tag in used if tag not in preferred]
    buttons = [
        f'<button class="btn" type="button" data-filter="all" aria-pressed="true">{escape(site["all"])}</button>'
    ]
    for tag in ordered:
        buttons.append(
            f'<button class="btn" type="button" data-filter="{escape(tag)}" aria-pressed="false">{escape(filter_label(site, tag))}</button>'
        )
    filters = ""
    if ordered:
        filters = (
            f'        <div class="filters" role="group" aria-label="{escape(site["filters_label"])}">\n          '
            + "\n          ".join(buttons)
            + "\n        </div>\n"
        )
    articles = "\n".join(paper_article(paper, True, depth) for paper in chosen)
    return (
        '      <section id="papers">\n'
        '        <div class="section-head">\n'
        f'          <h2>{escape(site["selected"])}</h2>\n'
        "        </div>\n"
        f"{filters}"
        '        <div class="papers" id="papers-list">\n'
        f"{articles}\n"
        "        </div>\n"
        "      </section>"
    )


def section_kind(body):
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if any(line.startswith("### ") for line in lines):
        groups = parse_year_groups(body)
        if groups and all(title.lstrip().startswith("[") for _, title, _ in groups):
            return "media"
        return "cards"
    if lines and all(line.startswith("- ") for line in lines):
        return "interests"
    return "aside"


def build_home(site, papers):
    depth = depth_of(site)
    text = read_content(site, "home.md")
    intro, sections = split_sections(text)
    bio = []
    for kind, data in parse_blocks(intro):
        if kind == "p":
            bio.append(f"          <p class=\"lede\">{inline(data)}</p>")
    links = "\n".join(
        f'            <a href="{escape(href, quote=True)}">{escape(label)}</a>'
        for label, href in site["links"]
    )
    portrait = escape(rooted(site["portrait"], depth), quote=True)
    hero = (
        '      <section class="hero" aria-labelledby="name">\n'
        '        <div class="identity">\n'
        f'          <img class="portrait" src="{portrait}" alt="{escape(site["portrait_alt"])}">\n'
        "          <div>\n"
        f'            <h1 id="name">{escape(site["name"])}</h1>\n'
        f'            <p class="kicker">{escape(site["position"])}</p>\n'
        "          </div>\n"
        "        </div>\n"
        '        <hr class="rule">\n'
        + "\n".join(bio)
        + "\n"
        '          <div class="hero-links">\n'
        f"{links}\n"
        "          </div>\n"
        "      </section>"
    )
    papers_html = selected_section(papers, site)
    placed = False
    card_index = 0
    chunks = [hero]
    for heading, body in sections:
        kind = section_kind(body)
        if kind == "interests":
            items = [
                f"<span>{inline(line.strip()[2:])}</span>"
                for line in body.splitlines()
                if line.strip().startswith("- ")
            ]
            chunks.append(
                f'      <div class="interests" aria-label="{escape(heading)}">\n        '
                + "\n        ".join(items)
                + "\n      </div>"
            )
        elif kind == "cards":
            card_index += 1
            section_id = "education" if card_index == 1 else "experience"
            chunks.append(
                f'      <section id="{section_id}">\n'
                '        <div class="section-head">\n'
                f"          <h2>{escape(heading)}</h2>\n"
                "        </div>\n"
                f"        {cards_html(parse_year_groups(body))}\n"
                "      </section>"
            )
            if section_id == "education":
                chunks.append(papers_html)
                placed = True
            elif not placed:
                chunks.insert(-1, papers_html)
                placed = True
        elif kind == "media":
            chunks.append(
                '      <section id="media">\n'
                '        <div class="section-head">\n'
                f"          <h2>{escape(heading)}</h2>\n"
                "        </div>\n"
                '        <div class="papers">\n'
                f"{media_html(parse_year_groups(body))}\n"
                "        </div>\n"
                "      </section>"
            )
        else:
            paragraphs = []
            for kind_name, data in parse_blocks(body):
                if kind_name == "p":
                    paragraphs.append(f"            <p>{inline(data)}</p>")
            aside = (
                '          <aside class="aside">\n'
                + "\n".join(paragraphs)
                + "\n          </aside>\n"
            )
            chunks[0] = chunks[0].rstrip()
            chunks[0] = chunks[0][: -len("</section>")] + aside + "      </section>"
    if not placed:
        chunks.append(papers_html)
    main = "\n\n".join(chunks)
    title = site["name"]
    return page_shell(site, "index.html", title, main, home=True)


def build_research(site):
    blocks = parse_blocks(read_content(site, "research.md"))
    title = next(data for kind, data in blocks if kind == "h1")
    main = "      " + article_html(blocks)
    return page_shell(site, "research.html", f"{title} — {site['name']}", main)


def build_publications(site, papers):
    depth = depth_of(site)
    articles = "\n".join(paper_article(paper, False, depth) for paper in papers)
    heading = site["publications_title"]
    main = (
        "      <section>\n"
        '        <div class="section-head">\n'
        f'          <h1 class="page-title">{escape(heading)}</h1>\n'
        "        </div>\n"
        '        <div class="papers">\n'
        f"{articles}\n"
        "        </div>\n"
        "      </section>"
    )
    return page_shell(site, "publications.html", f"{heading} — {site['name']}", main)


def build_gallery(site):
    depth = depth_of(site)
    text = read_content(site, "gallery.md")
    intro, sections = split_sections(text)
    title = "Gallery"
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    parts = ['      <section>']
    lead_blocks = parse_blocks(intro)
    lead = ['        <div class="copy">', f'          <h1 class="page-title">{escape(title)}</h1>']
    first = True
    for kind, data in lead_blocks:
        if kind != "p":
            continue
        css = ' class="lead"' if first else ""
        first = False
        lead.append(f"          <p{css}>{inline(data)}</p>")
    lead.append("        </div>")
    parts.append("\n".join(lead))
    places = gallery_places(sections)
    if places:
        parts.append(map_html(places, site.get("lang", "en")))
    for heading, body in sections:
        album, default_alt, captions, prose = parse_gallery_section(body)
        copy = [
            '        <div class="copy">',
            f"          <h2>{inline(heading)}</h2>",
        ]
        for kind, data in parse_blocks(prose):
            if kind == "p":
                copy.append(f"          <p>{inline(data)}</p>")
        copy.append("        </div>")
        parts.append("\n".join(copy))
        if album:
            parts.append("        " + album_html(album, heading, default_alt, captions, depth))
    close = "Κλείσιμο" if site.get("lang") == "el" else "Close"
    parts.append(
        '        <div class="lightbox" hidden>\n'
        f'          <button type="button" class="lightbox-close" data-close aria-label="{escape(close)}">×</button>\n'
        '          <figure>\n'
        '            <img alt="" draggable="false">\n'
        '            <figcaption class="lightbox-caption" hidden>\n'
        '              <span class="lightbox-title" hidden></span>\n'
        '              <span class="lightbox-place" hidden></span>\n'
        "            </figcaption>\n"
        "          </figure>\n"
        "        </div>"
    )
    parts.append("      </section>")
    extra_head = ""
    extra_scripts = ""
    if places:
        extra_head = """  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="">"""
        extra_scripts = """  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>"""
    return page_shell(
        site,
        "gallery.html",
        f"{title} — {site['name']}",
        "\n".join(parts),
        extra_head=extra_head,
        extra_scripts=extra_scripts,
    )


def load_site(path):
    meta, sections = parse_site(path.read_text())
    required = ["name", "position", "email", "footer", "cv", "portrait", "portrait_alt"]
    missing = [key for key in required if not meta.get(key)]
    if missing:
        raise SystemExit(f"{path.name} is missing: " + ", ".join(missing))
    defaults = dict(DEFAULTS)
    if meta.get("lang", "en") == "el":
        defaults.update(EL_DEFAULTS)
    for key, value in defaults.items():
        meta.setdefault(key, value)
    meta["nav"] = sections.get("nav", [])
    meta["links"] = sections.get("links", [])
    if not meta["nav"]:
        raise SystemExit(f"{path.name} needs a Nav list.")
    return meta


def pages_for(site):
    papers = parse_papers(read_content(site, "publications.md", fallback=True))
    pages = {
        "index.html": build_home(site, papers),
        "publications.html": build_publications(site, papers),
        "gallery.html": build_gallery(site),
    }
    if (content_dir(site) / "research.md").exists():
        pages = {
            "index.html": pages["index.html"],
            "research.html": build_research(site),
            "publications.html": pages["publications.html"],
            "gallery.html": pages["gallery.html"],
        }
    return pages, papers


def assemble_publish():
    """Copy the generated site into public/ for Netlify.

    Netlify will not deploy the repository root, and the pages link to photos,
    PDFs, and the CV under old_site/.
    """
    dest = ROOT / "public"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir()
    for name in ("index.html", "research.html", "publications.html", "gallery.html", "site.css", "site.js"):
        shutil.copy2(ROOT / name, dest / name)
    shutil.copytree(ROOT / "el", dest / "el")

    copied = 0
    for html in [dest / "index.html", dest / "research.html", dest / "publications.html", dest / "gallery.html", * (dest / "el").glob("*.html")]:
        for match in re.findall(r'(?:href|src)="([^"]+)"', html.read_text()):
            path = unquote(match.split("?", 1)[0].split("#", 1)[0])
            if path.startswith(("http://", "https://", "mailto:", "#")):
                continue
            while path.startswith("../"):
                path = path[3:]
            if not path.startswith("old_site/"):
                continue
            src = ROOT / path
            target = dest / path
            if target.exists():
                continue
            if not src.is_file():
                raise SystemExit(f"Missing asset for publish: {path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            copied += 1
    print(f"assembled public/ with {copied} assets")


def main():
    sources = [CONTENT / "en" / "site.md", CONTENT / "el" / "site.md"]
    for path in sources:
        site = load_site(path)
        pages, papers = pages_for(site)
        out = output_dir(site)
        out.mkdir(parents=True, exist_ok=True)
        for name, html in pages.items():
            (out / name).write_text(html)
            print(f"wrote {out.relative_to(ROOT) / name}")
        selected = sum(1 for paper in papers if paper["selected"] is not None)
        print(f"{site['lang']}: {len(papers)} publications, {selected} selected on the homepage")
    assemble_publish()


if __name__ == "__main__":
    main()
