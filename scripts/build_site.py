#!/usr/bin/env python3
import csv
import html
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


def text_to_html(body):
    out = []
    opened = False
    for line in body:
        if line.startswith("Image:"):
            continue
        if line in SECTION_TITLES or (len(line) <= 46 and not line.endswith((".", ",")) and len(line.split()) <= 7):
            if opened:
                out.append("</section>")
            out.append(f'<section class="content-section"><h2>{html.escape(line)}</h2>')
            opened = True
        else:
            if not opened:
                out.append('<section class="content-section lead-section">')
                opened = True
            out.append(f"<p>{html.escape(line)}</p>")
    if opened:
        out.append("</section>")
    return "\n".join(out)


def youtube_id(url):
    match = re.search(r"/embed/([^?&/]+)", url)
    return match.group(1) if match else ""


def render_embed_cards(embeds):
    cards = []
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
            cards.append(
                f"""
                <article class="embed-card missing-src">
                  <div class="missing-icon">Embed</div>
                  <div class="embed-meta"><span>Hidden Google Sites embed</span><strong>{label}</strong><p>The published page confirms this embed exists, but Google Sites does not expose its direct source in static HTML.</p></div>
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


def render_nav(pages, current_slug, depth):
    prefix = "" if depth == 0 else "../"
    links = [
        f'<a href="{prefix}index.html">Home</a>',
        f'<a href="{prefix}index.html#parks">Parks</a>',
        f'<a href="{prefix}resources.html">Resources</a>',
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
  <link rel="stylesheet" href="{prefix}assets/styles.css">
</head>
<body>
  <header class="site-header">
    <a class="brand" href="{prefix}index.html"><span class="brand-mark">NP</span><span>National Parks Webcams</span></a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button>
    <nav class="site-nav" id="site-nav">{render_nav(pages, page_slug, depth)}</nav>
  </header>
  {body}
  <footer class="site-footer">
    <p>Remade from the original National Parks Webcams Google Site. Content and links are preserved for migration review.</p>
    <a href="{prefix}resources.html">Resource inventory</a>
  </footer>
  <script src="{prefix}assets/app.js"></script>
</body>
</html>
"""


def build_home(pages, content_by_url, resources_by_url):
    home = next(p for p in pages if p["slug"] == "national-park-webcam-home")
    park_pages = [p for p in pages if p["slug"] != "national-park-webcam-home"]
    cards = []
    for page in park_pages:
        parsed_title, _, body = content_by_url[page["url"]]
        title = display_title(page, parsed_title)
        res = resources_by_url[page["url"]]
        image = first_image(res)
        intro = intro_from_body(body)
        img_html = f'<img src="{html.escape(image)}" alt="" loading="lazy" onerror="this.parentElement.classList.add(\'image-missing\'); this.remove();">' if image else '<div class="image-fallback"></div>'
        cards.append(
            f"""
            <article class="park-card" data-title="{html.escape(title.lower())}">
              <a href="parks/{page['slug']}.html" aria-label="Open {html.escape(title)}">
                <div class="park-card-image">{img_html}</div>
                <div class="park-card-body">
                  <span>{page['embed_count']} embeds · {page['link_count']} links</span>
                  <h2>{html.escape(short_name(title))}</h2>
                  <p>{html.escape(intro[:170])}</p>
                </div>
              </a>
            </article>
            """
        )
    _, _, home_body = content_by_url[home["url"]]
    hero_source = next((p for p in park_pages if p["slug"] == "glacier-webcam"), park_pages[0])
    hero_image = first_image(resources_by_url[hero_source["url"]]) or first_image(resources_by_url[home["url"]])
    description = intro_from_body(home_body)
    body = f"""
  <main>
    <section class="home-hero">
      <div class="hero-copy">
        <span class="eyebrow">Live views, hikes, camping, lodging, and park notes</span>
        <h1>National Parks Webcams</h1>
        <p>{html.escape(description)}</p>
        <div class="hero-actions">
          <a class="button primary" href="#parks">Explore parks</a>
          <a class="button secondary" href="resources.html">View resources</a>
        </div>
      </div>
      <div class="hero-photo">
        <img src="{html.escape(hero_image)}" alt="" loading="eager" onerror="this.parentElement.classList.add('image-missing'); this.remove();">
      </div>
    </section>
    <section class="stats-band" aria-label="Site inventory">
      <div><strong>{len(park_pages)}</strong><span>park pages</span></div>
      <div><strong>{sum(p['embed_count'] for p in pages)}</strong><span>embedded feeds and maps</span></div>
      <div><strong>{sum(p['link_count'] for p in pages)}</strong><span>preserved links</span></div>
    </section>
    <section class="park-browser" id="parks">
      <div class="section-heading">
        <div>
          <span class="eyebrow">Browse the collection</span>
          <h2>Webcam Parks</h2>
        </div>
        <label class="search-box">
          <span>Search</span>
          <input type="search" id="park-search" placeholder="Yellowstone, Acadia, Zion...">
        </label>
      </div>
      <div class="park-grid" id="park-grid">{''.join(cards)}</div>
    </section>
  </main>
"""
    return page_shell("National Parks Webcams", body, home["slug"], pages, description, hero_image, 0)


def build_park_page(page, pages, content, resources, page_urls):
    parsed_title, source, body = content
    title = display_title(page, parsed_title)
    links, embeds, images = resource_groups(resources, page_urls)
    hero = first_image(resources)
    intro = intro_from_body(body)
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
          <span>{len(embeds)} embeds</span>
          <span>{len(links)} useful links</span>
          <span>{len(images)} photos</span>
        </div>
      </div>
    </section>
    <div class="page-layout">
      <article class="page-content">{text_to_html(body)}</article>
      <aside class="resource-panel">
        <div class="panel-card">
          <h2>Live Feeds & Maps</h2>
          <p>Direct videos and maps are embedded below. Hidden Google Sites embeds are flagged for replacement.</p>
          <a href="{html.escape(source)}" target="_blank" rel="noopener">Original page</a>
        </div>
        {f'<div class="photo-strip">{image_strip}</div>' if image_strip else ''}
      </aside>
    </div>
    <section class="resource-section">
      <div class="section-heading">
        <div><span class="eyebrow">Preserved page resources</span><h2>Feeds, Maps, Photos & Links</h2></div>
      </div>
      <div class="embed-grid">{render_embed_cards(embeds)}</div>
      <div class="links-panel">
        <h2>Helpful Links</h2>
        <ul>{render_link_list(links)}</ul>
      </div>
    </section>
  </main>
"""
    return page_shell(title, body_html, page["slug"], pages, intro, hero, 1)


def build_resources_page(pages, resources_by_url, page_urls):
    rows = []
    for page in pages:
        links, embeds, images = resource_groups(resources_by_url[page["url"]], page_urls)
        for kind, group in [("Embed", embeds), ("Image", images), ("Link", links)]:
            for item in group:
                url_cell = (
                    f"<code>{html.escape(item['url'])}</code>"
                    if item["url"].startswith("google-sites-frame:")
                    else f"""<a href="{html.escape(item['url'])}" target="_blank" rel="noopener">{html.escape(item['url'][:90])}</a>"""
                )
                rows.append(
                    f"""
                    <tr>
                      <td><a href="{html.escape(page_href(page))}">{html.escape(short_name(page['title']))}</a></td>
                      <td>{kind}</td>
                      <td>{html.escape(item['label'])}</td>
                      <td>{url_cell}</td>
                    </tr>
                    """
                )
    body = f"""
  <main>
    <section class="inventory-hero">
      <span class="eyebrow">Migration checklist</span>
      <h1>Resource Inventory</h1>
      <p>Every extracted page resource in one place: links, photos, maps, live videos, and hidden Google Sites custom embeds that need replacement.</p>
    </section>
    <section class="inventory-table-wrap">
      <table class="inventory-table">
        <thead><tr><th>Page</th><th>Type</th><th>Label</th><th>URL or ID</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
  </main>
"""
    return page_shell("Resource Inventory", body, "resources", pages, "Resource inventory for the National Parks Webcams migration.", "", 0)


def main():
    pages = load_pages()
    resources_by_url = load_resources()
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

    (DIST / "index.html").write_text(build_home(pages, content_by_url, resources_by_url), encoding="utf-8")
    (DIST / "resources.html").write_text(build_resources_page(pages, resources_by_url, page_urls), encoding="utf-8")
    for page in pages:
        if page["slug"] == "national-park-webcam-home":
            continue
        html_out = build_park_page(
            page,
            pages,
            content_by_url[page["url"]],
            resources_by_url[page["url"]],
            page_urls,
        )
        (PAGES_OUT / f"{page['slug']}.html").write_text(html_out, encoding="utf-8")
    print(f"Built {len(pages)} pages into {DIST}")


if __name__ == "__main__":
    main()
