#!/usr/bin/env python3
import csv
import html
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "nationalparkcam_export"
DIST = ROOT / "docs"
PAGES_OUT = DIST / "parks"
ASSETS_OUT = DIST / "assets"


SECTION_TITLES = {
    "Introduction",
    "Day Hikes",
    "Top Hikes and Climbs",
    "Hiking and Backpacking",
    "Backpacking",
    "Camping and Lodging",
    "Camping",
    "Lodging",
    "Fishing",
    "Wildlife Viewing",
    "Biking",
    "Climbing",
    "Accommodations",
    "Food & Groceries",
    "Getting Around - Transportation",
    "External Links",
    "Short History of the National Park",
}

PARK_NAMES = {
    "acadia-webcam": "Acadia National Park",
    "arches-webcam": "Arches National Park",
    "big-bend-webcam": "Big Bend National Park",
    "black-canyon-of-the-gunnison-webcam": "Black Canyon of the Gunnison National Park",
    "bryce-canyon-webcam": "Bryce Canyon National Park",
    "channel-islands-webcam": "Channel Islands National Park",
    "crater-lake-webcam": "Crater Lake National Park",
    "denali-webcam": "Denali National Park",
    "everglades-webcam": "Everglades National Park",
    "glacier-bay-webcam": "Glacier Bay National Park",
    "glacier-webcam": "Glacier National Park",
    "grand-canyon-webcam": "Grand Canyon National Park",
    "grand-tetons-webcam": "Grand Teton National Park",
    "great-smoky-mountains-webcam": "Great Smoky Mountains National Park",
    "guadalupe-mountains-webcam": "Guadalupe Mountains National Park",
    "haleakala-webcam": "Haleakala National Park",
    "hawaii-volcanoes-webcam": "Hawaii Volcanoes National Park",
    "isle-royale-national-park-webcam": "Isle Royale National Park",
    "joshua-tree-webcam": "Joshua Tree National Park",
    "katmai-webcam": "Katmai National Park",
    "kings-canyon-webcam": "Sequoia and Kings Canyon National Parks",
    "lassen-volcano-webcam": "Lassen Volcanic National Park",
    "mammoth-cave-webcam": "Mammoth Cave National Park",
    "mount-rainier-webcam": "Mount Rainier National Park",
    "new-river-gorge-webcam": "New River Gorge National Park",
    "north-cascades-webcam": "North Cascades National Park",
    "olympic-webcam": "Olympic National Park",
    "petrified-forest-webcam": "Petrified Forest National Park",
    "redwood-national-park": "Redwood National and State Parks",
    "rocky-mountain-webcam": "Rocky Mountain National Park",
    "shenandoah-webcam": "Shenandoah National Park",
    "theodore-roosevelt-webcam": "Theodore Roosevelt National Park",
    "virgin-islands-webcam": "Virgin Islands National Park",
    "wrangell-st-elias-webcam": "Wrangell-St. Elias National Park",
    "yellowstone-webcam": "Yellowstone National Park",
    "yosemite-webcam": "Yosemite National Park",
    "zion-webcam": "Zion National Park",
}

PARK_COORDS = {
    "acadia-webcam": [44.3386, -68.2733],
    "arches-webcam": [38.7331, -109.5925],
    "big-bend-webcam": [29.1275, -103.2425],
    "black-canyon-of-the-gunnison-webcam": [38.5754, -107.7416],
    "bryce-canyon-webcam": [37.593, -112.1871],
    "channel-islands-webcam": [34.0069, -119.7785],
    "crater-lake-webcam": [42.9446, -122.109],
    "denali-webcam": [63.1148, -151.1926],
    "everglades-webcam": [25.2866, -80.8987],
    "glacier-bay-webcam": [58.6658, -136.9002],
    "glacier-webcam": [48.7596, -113.787],
    "grand-canyon-webcam": [36.1069, -112.1129],
    "grand-tetons-webcam": [43.7904, -110.6818],
    "great-smoky-mountains-webcam": [35.6118, -83.4895],
    "guadalupe-mountains-webcam": [31.923, -104.87],
    "haleakala-webcam": [20.7204, -156.1552],
    "hawaii-volcanoes-webcam": [19.4194, -155.2885],
    "isle-royale-national-park-webcam": [48.011, -88.8278],
    "joshua-tree-webcam": [33.8734, -115.901],
    "katmai-webcam": [58.5975, -154.6939],
    "kings-canyon-webcam": [36.8879, -118.5551],
    "lassen-volcano-webcam": [40.4977, -121.4207],
    "mammoth-cave-webcam": [37.1862, -86.1005],
    "mount-rainier-webcam": [46.8523, -121.7603],
    "new-river-gorge-webcam": [37.8683, -80.9996],
    "north-cascades-webcam": [48.7718, -121.2985],
    "olympic-webcam": [47.8021, -123.6044],
    "petrified-forest-webcam": [35.0659, -109.781],
    "redwood-national-park": [41.2132, -124.0046],
    "rocky-mountain-webcam": [40.3428, -105.6836],
    "shenandoah-webcam": [38.5339, -78.35],
    "theodore-roosevelt-webcam": [46.979, -103.5387],
    "virgin-islands-webcam": [18.3424, -64.7486],
    "wrangell-st-elias-webcam": [61.7104, -142.9857],
    "yellowstone-webcam": [44.6, -110.5],
    "yosemite-webcam": [37.8651, -119.5383],
    "zion-webcam": [37.2982, -113.0263],
}


def clean_title(title):
    title = title.replace("Liv e", "Live").replace("Glacie r", "Glacier")
    title = title.replace("G rand", "Grand").replace("Gr eat", "Great")
    title = title.replace("G uadalupe", "Guadalupe").replace("H awaii", "Hawaii")
    title = title.replace("Y osemite", "Yosemite")
    title = re.sub(r"\s+", " ", title).strip()
    return title


def decode_url(url):
    parsed = urlparse(url)
    if parsed.netloc == "www.google.com" and parsed.path == "/url":
        q = parse_qs(parsed.query).get("q")
        if q:
            return q[0]
    return url


def page_href(row):
    if row["slug"] == "national-park-webcam-home":
        return "index.html"
    return f"parks/{row['slug']}.html"


def rel_from_page(target, page_slug):
    if page_slug == "national-park-webcam-home":
        return target
    if target.startswith("parks/"):
        return target.split("/", 1)[1]
    return f"../{target}"


def load_pages():
    pages = []
    with (EXPORT / "index.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row = dict(row)
            row["title"] = clean_title(row["title"])
            row["line_count"] = int(row["line_count"])
            row["link_count"] = int(row["link_count"])
            row["image_count"] = int(row["image_count"])
            row["embed_count"] = int(row.get("embed_count") or 0)
            if row["slug"] in PARK_NAMES:
                row["title"] = f"{PARK_NAMES[row['slug']]} Webcams"
            pages.append(row)
    return pages


def load_resources():
    resources = defaultdict(list)
    with (EXPORT / "resources.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row = dict(row)
            row["page"] = clean_title(row["page"])
            row["url"] = decode_url(row["url"])
            resources[row["page_url"]].append(row)
    return resources


def load_webcam_sources():
    path = EXPORT / "webcam_sources.csv"
    sources = defaultdict(list)
    if not path.exists():
        return sources
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sources[row["slug"]].append(dict(row))
    return sources


def parse_markdown(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    title = lines[0].lstrip("# ").strip()
    source = ""
    body = []
    in_resource = False
    for line in lines[1:]:
        if line.startswith("Source:"):
            source = line.replace("Source:", "", 1).strip()
            continue
        if line.startswith("## Images") or line.startswith("## Embeds") or line.startswith("## Links"):
            in_resource = True
        if in_resource:
            continue
        text = line.strip()
        if text:
            body.append(text)
    return clean_title(title), source, body


def display_title(page, parsed_title):
    if page["slug"] in PARK_NAMES:
        return f"{PARK_NAMES[page['slug']]} Webcams"
    return parsed_title


def first_image(resources):
    candidates = []
    for item in resources:
        if item["type"] != "image":
            continue
        url = item["url"]
        label = item["label"].lower()
        if "email" in label or "sociallinks" in url or "sheets_32dp" in url:
            continue
        candidates.append(url)
    return candidates[0] if candidates else ""


def intro_from_body(body):
    for line in body:
        if len(line) > 90 and not line.startswith("Image:"):
            return line
    return body[0] if body else ""


def is_internal_nav_link(url, page_urls):
    parsed = urlparse(url)
    if parsed.netloc != "www.nationalparkcam.com":
        return False
    normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    return normalized in page_urls


def resource_groups(resources, page_urls):
    links, embeds, images = [], [], []
    seen = set()
    for item in resources:
        url = item["url"]
        label = clean_title(item["label"]).strip() or item["type"].title()
        key = (item["type"], label, url)
        if key in seen:
            continue
        seen.add(key)
        if item["type"] == "link":
            if is_internal_nav_link(url, page_urls):
                continue
            if url.startswith("mailto:"):
                continue
            links.append({**item, "label": label})
        elif item["type"] == "embed":
            embeds.append({**item, "label": label})
        elif item["type"] == "image":
            if "email" in label.lower() or "sociallinks" in url or "sheets_32dp" in url:
                continue
            images.append({**item, "label": label})
    return links, embeds, images


def is_map_embed(embed):
    return "maps-api-ssl.google.com" in embed["url"]


def live_embed_count(embeds):
    return sum(1 for embed in embeds if not is_map_embed(embed))


def section_has_body(section):
    return any(not line.startswith("Image:") for line in section["paragraphs"])


def text_to_html(body):
    sections = []
    current = {"title": "", "paragraphs": []}
    for line in body:
        if line.startswith("Image:"):
            continue
        if line in SECTION_TITLES or (len(line) <= 46 and not line.endswith((".", ",")) and len(line.split()) <= 7):
            if current["title"] or section_has_body(current):
                sections.append(current)
            current = {"title": line, "paragraphs": []}
        else:
            current["paragraphs"].append(line)
    if current["title"] or section_has_body(current):
        sections.append(current)

    out = []
    for section in sections:
        if not section_has_body(section):
            continue
        heading = f"<h2>{html.escape(section['title'])}</h2>" if section["title"] else ""
        paragraphs = "".join(f"<p>{html.escape(line)}</p>" for line in section["paragraphs"])
        out.append(f'<section class="content-section">{heading}{paragraphs}</section>')
    return "\n".join(out)


def youtube_id(url):
    match = re.search(r"/embed/([^?&/]+)", url)
    return match.group(1) if match else ""


def render_webcam_source_cards(webcam_sources):
    cards = []
    for source in webcam_sources:
        title = html.escape(source["title"])
        url = html.escape(source["url"])
        page_url = html.escape(source["page_url"])
        provider = html.escape(source["provider"])
        status = html.escape(source["status"])
        cards.append(
            f"""
            <article class="embed-card webcam-image-card">
              <a class="webcam-image-link" href="{page_url}" target="_blank" rel="noopener">
                <img src="{url}" data-refresh-src="{url}" alt="{title}" loading="lazy" onerror="this.closest('.webcam-image-card').classList.add('image-missing'); this.remove();">
              </a>
              <div class="embed-meta"><span>{provider}</span><strong>{title}</strong><p>{status}</p></div>
            </article>
            """
        )
    return cards


def render_embed_cards(embeds, webcam_sources=None):
    webcam_sources = webcam_sources or []
    cards = []
    missing = []
    for embed in embeds:
        url = embed["url"]
        label = html.escape(embed["label"])
        if "youtube.com/embed/" in url:
            src = html.escape(url)
            cards.append(
                f"""
                <article class="embed-card video-card">
                  <div class="embed-frame"><iframe src="{src}" title="{label}" loading="lazy" allowfullscreen></iframe></div>
                  <div class="embed-meta"><span>Live video</span><strong>{label.replace('YouTube Video, ', '')}</strong></div>
                </article>
                """
            )
        elif "maps-api-ssl.google.com" in url:
            src = html.escape(url)
            cards.append(
                f"""
                <article class="embed-card">
                  <div class="embed-frame map"><iframe src="{src}" title="{label}" loading="lazy" allowfullscreen></iframe></div>
                  <div class="embed-meta"><span>Map</span><strong>Park location</strong></div>
                </article>
                """
            )
        elif url.startswith("google-sites-frame:"):
            missing.append((label, html.escape(url.replace("google-sites-frame:", ""))))
    cards.extend(render_webcam_source_cards(webcam_sources))
    missing = missing[len(webcam_sources):]
    if missing:
        items = "".join(f"<li><strong>{label}</strong><code>{identifier}</code></li>" for label, identifier in missing)
        cards.append(
            f"""
            <article class="source-needed-card">
              <span class="eyebrow">Source needed</span>
              <h3>{len(missing)} Google Sites embed{'' if len(missing) == 1 else 's'} to replace</h3>
              <p>These existed on the original page, but Google Sites only exposes them through a non-portable runtime wrapper. They should be replaced with direct NPS, YouTube, weather, or camera-provider URLs.</p>
              <details>
                <summary>Show captured embed IDs</summary>
                <ul>{items}</ul>
              </details>
            </article>
            """
        )
    return "\n".join(cards)


def render_link_list(links):
    useful = links[:28]
    items = []
    for link in useful:
        items.append(
            f'<li><a href="{html.escape(link["url"])}" target="_blank" rel="noopener">{html.escape(link["label"])}</a></li>'
        )
    return "\n".join(items)


def clean_embed_label(label):
    return label.replace("YouTube Video, ", "").strip()


def popular_streams(resources_by_url, pages):
    preferred = [
        "katmai-webcam",
        "yellowstone-webcam",
        "yosemite-webcam",
        "grand-tetons-webcam",
    ]
    by_slug = {page["slug"]: page for page in pages}
    streams = []
    for slug in preferred:
        page = by_slug.get(slug)
        if not page:
            continue
        for item in resources_by_url[page["url"]]:
            if item["type"] == "embed" and "youtube.com/embed/" in item["url"]:
                streams.append(
                    {
                        "park": short_name(page["title"]),
                        "label": clean_embed_label(clean_title(item["label"])),
                        "url": item["url"],
                        "href": f"parks/{page['slug']}.html",
                    }
                )
                break
    return streams


def render_popular_streams(streams):
    cards = []
    for stream in streams[:4]:
        video_id = youtube_id(stream["url"])
        thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else ""
        image = (
            f'<img src="{html.escape(thumbnail)}" alt="" loading="eager" onerror="this.closest(\'.hero-stream-card\').classList.add(\'image-missing\'); this.remove();">'
            if thumbnail
            else ""
        )
        cards.append(
            f"""
            <article class="hero-stream-card">
              <a href="{html.escape(stream['href'])}">
                <div class="hero-stream-thumb">{image}<span class="play-badge">Live</span></div>
                <span>{html.escape(stream['park'])}</span>
                <strong>{html.escape(stream['label'])}</strong>
              </a>
            </article>
            """
        )
    return "\n".join(cards)


def render_nav(pages, current_slug, depth):
    prefix = "" if depth == 0 else "../"
    links = [
        f'<a href="{prefix}index.html">Home</a>',
        f'<a href="{prefix}index.html#parks">Parks</a>',
    ]
    if current_slug not in {"national-park-webcam-home", "resources"}:
        current = next((p for p in pages if p["slug"] == current_slug), None)
        if current:
            links.append(f'<a aria-current="page" href="{prefix}parks/{current["slug"]}.html">{html.escape(short_name(current["title"]))}</a>')
    return "\n".join(links)


def short_name(title):
    title = title.replace("National and State Parks Webcams", "")
    title = title.replace("National Parks Webcams", "")
    title = title.replace("National Park Webcams", "")
    title = title.replace("National Park", "")
    title = title.replace("Webcams", "")
    return re.sub(r"\s+", " ", title).strip(" -.") or title


def page_shell(title, body, page_slug, pages, description, image="", depth=0):
    prefix = "" if depth == 0 else "../"
    image_meta = f'<meta property="og:image" content="{html.escape(image)}">' if image else ""
    data_attrs = f' data-page-slug="{html.escape(page_slug)}" data-page-title="{html.escape(title)}" data-page-depth="{depth}"'
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} | National Parks Webcams</title>
  <meta name="description" content="{html.escape(description[:155])}">
  <meta property="og:title" content="{html.escape(title)}">
  <meta property="og:description" content="{html.escape(description[:180])}">
  {image_meta}
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <link rel="stylesheet" href="{prefix}assets/styles.css">
</head>
<body{data_attrs}>
  <header class="site-header">
    <a class="brand" href="{prefix}index.html"><span class="brand-mark">NP</span><span>National Parks Webcams</span></a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button>
    <div class="header-nav-group">
      <nav class="recent-parks" id="recent-parks" aria-label="Recently viewed parks"></nav>
      <nav class="site-nav" id="site-nav">{render_nav(pages, page_slug, depth)}</nav>
    </div>
  </header>
  {body}
  <footer class="site-footer">
    <p>Remade from the original National Parks Webcams Google Site. Content and links are preserved for migration review.</p>
  </footer>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="{prefix}assets/app.js"></script>
</body>
</html>
"""


def build_home(pages, content_by_url, resources_by_url, webcam_sources_by_slug):
    home = next(p for p in pages if p["slug"] == "national-park-webcam-home")
    park_pages = [p for p in pages if p["slug"] != "national-park-webcam-home"]
    cards = []
    for page in park_pages:
        parsed_title, _, body = content_by_url[page["url"]]
        title = display_title(page, parsed_title)
        res = resources_by_url[page["url"]]
        links, embeds, images = resource_groups(res, {p["url"].rstrip("/") for p in pages})
        cam_count = live_embed_count(embeds) + len(webcam_sources_by_slug.get(page["slug"], []))
        image = first_image(res)
        intro = intro_from_body(body)
        img_html = f'<img src="{html.escape(image)}" alt="" loading="lazy" onerror="this.parentElement.classList.add(\'image-missing\'); this.remove();">' if image else '<div class="image-fallback"></div>'
        cards.append(
            f"""
            <article class="park-card" data-title="{html.escape(title.lower())}">
              <a href="parks/{page['slug']}.html" aria-label="Open {html.escape(title)}">
                <div class="park-card-image">{img_html}</div>
                <div class="park-card-body">
                  <span>{cam_count} live cam sources · {len(embeds) - cam_count} maps</span>
                  <h2>{html.escape(short_name(title))}</h2>
                  <p>{html.escape(intro[:170])}</p>
                  <strong class="card-action">View live cams</strong>
                </div>
              </a>
            </article>
            """
        )
    _, _, home_body = content_by_url[home["url"]]
    hero_source = next((p for p in park_pages if p["slug"] == "glacier-webcam"), park_pages[0])
    hero_image = first_image(resources_by_url[hero_source["url"]]) or first_image(resources_by_url[home["url"]])
    description = intro_from_body(home_body)
    page_urls = {p["url"].rstrip("/") for p in pages}
    hero_streams = popular_streams(resources_by_url, park_pages)
    map_points = []
    for page in park_pages:
        links, embeds, _ = resource_groups(resources_by_url[page["url"]], page_urls)
        cam_count = live_embed_count(embeds) + len(webcam_sources_by_slug.get(page["slug"], []))
        coords = PARK_COORDS.get(page["slug"])
        if not coords:
            continue
        map_points.append(
            {
                "slug": page["slug"],
                "title": short_name(page["title"]),
                "fullTitle": page["title"],
                "href": f"parks/{page['slug']}.html",
                "lat": coords[0],
                "lng": coords[1],
                "cams": cam_count,
                "embeds": len(embeds),
                "links": len(links),
            }
        )
    map_json = html.escape(json.dumps(map_points), quote=False)
    body = f"""
  <main>
    <section class="home-hero">
      <div class="hero-copy">
        <span class="eyebrow">Live views, hikes, camping, lodging, and park notes</span>
        <h1>National Parks Webcams</h1>
        <p>{html.escape(description)}</p>
        <div class="hero-actions">
          <a class="button primary" href="#parks">Find live cams</a>
        </div>
      </div>
      <div class="hero-streams" aria-label="Popular live streams">
        {render_popular_streams(hero_streams)}
      </div>
    </section>
    <section class="stats-band" aria-label="Site inventory">
      <div><strong>{len(park_pages)}</strong><span>park pages</span></div>
      <div><strong>{sum(live_embed_count(resource_groups(resources_by_url[p['url']], page_urls)[1]) + len(webcam_sources_by_slug.get(p['slug'], [])) for p in park_pages)}</strong><span>live cam sources</span></div>
      <div><strong>1</strong><span>interactive park map</span></div>
    </section>
    <section class="park-browser" id="parks">
      <div class="section-heading">
        <div>
          <span class="eyebrow">Browse by location</span>
          <h2>Live Cam Map</h2>
        </div>
        <label class="search-box">
          <span>Search</span>
          <input type="search" id="park-search" placeholder="Yellowstone, Acadia, Zion...">
        </label>
      </div>
      <div class="map-explorer">
        <div id="webcam-map" class="webcam-map" aria-label="Interactive national park webcam map"></div>
        <aside class="map-side">
          <span class="eyebrow">Featured live cams</span>
          <h3 id="map-active-title">Select a park</h3>
          <p id="map-active-meta">Choose a marker or a park below to jump straight to its webcam page.</p>
          <a id="map-active-link" class="button primary" href="#parks">Open park cams</a>
          <div class="map-list" id="map-list"></div>
        </aside>
      </div>
      <script type="application/json" id="park-map-data">{map_json}</script>
      <div class="section-heading park-grid-heading">
        <div>
          <span class="eyebrow">All webcam pages</span>
          <h2>Park Directory</h2>
        </div>
      </div>
      <div class="park-grid" id="park-grid">{''.join(cards)}</div>
    </section>
  </main>
"""
    return page_shell("National Parks Webcams", body, home["slug"], pages, description, hero_image, 0)


def build_park_page(page, pages, content, resources, page_urls, webcam_sources):
    parsed_title, source, body = content
    title = display_title(page, parsed_title)
    links, embeds, images = resource_groups(resources, page_urls)
    cam_count = live_embed_count(embeds) + len(webcam_sources)
    hero = first_image(resources)
    intro = intro_from_body(body)
    coords = PARK_COORDS.get(page["slug"], ["", ""])
    weather_attrs = f'data-lat="{coords[0]}" data-lng="{coords[1]}"' if coords[0] != "" else ""
    hero_img_html = (
        f"""<img src="{html.escape(hero)}" alt="" loading="eager" onerror="this.parentElement.classList.add('image-missing'); this.remove();">"""
        if hero
        else ""
    )
    image_strip = "\n".join(
        f"""<a href="{html.escape(img['url'])}" target="_blank" rel="noopener"><img src="{html.escape(img['url'])}" alt="{html.escape(img['label'])}" loading="lazy" onerror="this.closest('a').remove();"></a>"""
        for img in images[:4]
    )
    body_html = f"""
  <main>
    <section class="page-hero">
      <div class="page-hero-media">{hero_img_html}</div>
      <div class="page-hero-copy">
        <a class="back-link" href="../index.html">All parks</a>
        <h1>{html.escape(title)}</h1>
        <p>{html.escape(intro)}</p>
        <div class="page-metrics">
          <span>{cam_count} live cam sources</span>
          <span>{len(embeds) - cam_count} maps</span>
          <span>{len(links)} useful links</span>
          <span>{len(images)} photos</span>
        </div>
      </div>
    </section>
    <section class="resource-section live-first" id="live-cams">
      <div class="section-heading">
        <div><span class="eyebrow">Watch first</span><h2>Live Cams & Maps</h2></div>
        <a class="button secondary" href="{html.escape(source)}" target="_blank" rel="noopener">Original page</a>
      </div>
      <div class="embed-grid">{render_embed_cards(embeds, webcam_sources)}</div>
    </section>
    <section class="weather-section" {weather_attrs}>
      <div class="section-heading">
        <div><span class="eyebrow">Current conditions</span><h2>Weather</h2></div>
      </div>
      <div class="weather-layout">
        <article class="weather-card">
          <h3>Next 12 hours</h3>
          <div class="hourly-weather" data-weather-hourly>Loading hourly forecast...</div>
        </article>
        <article class="weather-card">
          <h3>7 day outlook</h3>
          <div class="daily-weather" data-weather-daily>Loading forecast...</div>
        </article>
      </div>
    </section>
    <div class="page-layout">
      <article class="page-content">{text_to_html(body)}</article>
      <aside class="resource-panel">
        <div class="panel-card">
          <h2>Webcam Migration Notes</h2>
          <p>Direct videos and maps are featured above. Hidden Google Sites embeds are flagged for replacement with direct webcam sources.</p>
          <a href="{html.escape(source)}" target="_blank" rel="noopener">Original page</a>
        </div>
        {f'<div class="photo-strip">{image_strip}</div>' if image_strip else ''}
      </aside>
    </div>
    <section class="resource-section">
      <div class="section-heading">
        <div><span class="eyebrow">Planning resources</span><h2>Helpful Links</h2></div>
      </div>
      <div class="links-panel">
        <ul>{render_link_list(links)}</ul>
      </div>
    </section>
  </main>
"""
    return page_shell(title, body_html, page["slug"], pages, intro, hero, 1)


def main():
    pages = load_pages()
    resources_by_url = load_resources()
    webcam_sources_by_slug = load_webcam_sources()
    page_urls = {p["url"].rstrip("/") for p in pages}
    content_by_url = {}
    for page in pages:
        content_by_url[page["url"]] = parse_markdown(EXPORT / page["markdown"])

    if DIST.exists():
        shutil.rmtree(DIST)
    PAGES_OUT.mkdir(parents=True)
    ASSETS_OUT.mkdir(parents=True)
    shutil.copy(ROOT / "assets" / "styles.css", ASSETS_OUT / "styles.css")
    shutil.copy(ROOT / "assets" / "app.js", ASSETS_OUT / "app.js")

    (DIST / "index.html").write_text(build_home(pages, content_by_url, resources_by_url, webcam_sources_by_slug), encoding="utf-8")
    for page in pages:
        if page["slug"] == "national-park-webcam-home":
            continue
        html_out = build_park_page(
            page,
            pages,
            content_by_url[page["url"]],
            resources_by_url[page["url"]],
            page_urls,
            webcam_sources_by_slug.get(page["slug"], []),
        )
        (PAGES_OUT / f"{page['slug']}.html").write_text(html_out, encoding="utf-8")
    print(f"Built {len(pages)} pages into {DIST}")


if __name__ == "__main__":
    main()
