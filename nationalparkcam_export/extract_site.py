#!/usr/bin/env python3
import csv
import html
import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse


BASE = "https://www.nationalparkcam.com"
ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
PAGES = ROOT / "pages"


SKIP_TEXT = {
    "Google Sites",
    "Report abuse",
    "Page updated",
    "Open search bar",
    "Skip to main content",
    "Skip to navigation",
    "Search this site",
    "Embedded Files",
    "Page details",
}


class SiteParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.stack = []
        self.items = []
        self.links = []
        self.images = []
        self.embeds = []
        self.current_href = None
        self.current_img = None
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.stack.append(tag)
        if tag in {"script", "style", "svg", "noscript"}:
            self.skip_depth += 1
        if tag == "a":
            href = attrs.get("href")
            if href:
                self.current_href = href
                self.links.append((href, ""))
        if tag == "img":
            src = attrs.get("src")
            alt = attrs.get("alt", "")
            if src:
                self.images.append((src, alt))
                if alt:
                    self.items.append(("text", f"Image: {alt}"))
        if tag == "iframe":
            self.embeds.append(
                {
                    "src": attrs.get("src", ""),
                    "title": attrs.get("title", ""),
                    "aria_label": attrs.get("aria-label", ""),
                    "id": attrs.get("id", ""),
                    "name": attrs.get("name", ""),
                }
            )
        if tag in {"h1", "h2", "h3", "h4", "p", "li"}:
            self.items.append(("break", tag))
        if tag == "br":
            self.items.append(("break", tag))

    def handle_endtag(self, tag):
        if tag in {"script", "style", "svg", "noscript"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "a":
            self.current_href = None
        if tag in {"h1", "h2", "h3", "h4", "p", "li", "div", "section"}:
            self.items.append(("break", tag))
        if self.stack:
            self.stack.pop()

    def handle_data(self, data):
        if self.skip_depth:
            return
        text = html.unescape(data)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return
        if self.current_href and self.links:
            href, prev = self.links[-1]
            self.links[-1] = (href, (prev + " " + text).strip())
        self.items.append(("text", text))

    def handle_entityref(self, name):
        self.handle_data(f"&{name};")

    def handle_charref(self, name):
        self.handle_data(f"&#{name};")


def slug_for_url(url):
    path = urlparse(url).path.strip("/")
    return path or "national-park-webcam-home"


def safe_filename(slug):
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", slug).strip("-") + ".html"


def fetch(url):
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / safe_filename(slug_for_url(url))
    if out.exists() and out.stat().st_size > 0:
        return out
    subprocess.run(
        ["curl", "-L", url, "-o", str(out)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return out


def parse_file(path):
    parser = SiteParser()
    parser.feed(path.read_text(errors="replace"))
    return parser


def is_internal_page(href):
    if href.startswith("#") or href.startswith("mailto:"):
        return False
    url = urljoin(BASE, href)
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != "www.nationalparkcam.com":
        return False
    if "/_" in parsed.path:
        return False
    if parsed.path in {"", "/"}:
        return True
    return not Path(parsed.path).suffix


def normalize_url(href):
    parsed = urlparse(urljoin(BASE, href))
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/') or '/'}"


def discover(seed_path):
    parser = parse_file(seed_path)
    found = []
    seen = set()
    for href, text in parser.links:
        if is_internal_page(href):
            url = normalize_url(href)
            if url not in seen:
                seen.add(url)
                found.append((url, text))
    home = f"{BASE}/national-park-webcam-home"
    if home not in seen:
        found.insert(0, (home, "National Parks Webcams"))
    return found


def clean_lines(items, nav_titles=None):
    lines = []
    buffer = []

    def flush():
        nonlocal buffer
        if not buffer:
            return
        text = " ".join(buffer)
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\s+'\s+s\b", "'s", text)
        text = re.sub(r"\s+'\s+t\b", "'t", text)
        text = re.sub(r"\s+'\s+ll\b", "'ll", text)
        text = re.sub(r"\s+'\s+re\b", "'re", text)
        text = re.sub(r"\s+'\s+ve\b", "'ve", text)
        text = re.sub(r"\s+'\s+d\b", "'d", text)
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        text = re.sub(r'"\s+', '"', text)
        text = re.sub(r'\s+"', '"', text)
        buffer = []
        if not text or text in SKIP_TEXT:
            return
        if lines and lines[-1] == text:
            return
        lines.append(text)

    for kind, value in items:
        if kind == "break":
            flush()
        else:
            buffer.append(value)
    flush()

    cleaned = []
    for line in lines:
        if line in SKIP_TEXT:
            continue
        if line == "National Parks Webcams" and cleaned and cleaned[0] == line:
            continue
        cleaned.append(line)

    nav_titles = set(nav_titles or [])
    while cleaned and cleaned[0] in SKIP_TEXT:
        cleaned.pop(0)
    if nav_titles:
        last_nav_index = -1
        for index, line in enumerate(cleaned[:120]):
            if line in nav_titles:
                last_nav_index = index
        if last_nav_index >= 0:
            cleaned = cleaned[last_nav_index + 1 :]
    if cleaned and cleaned[0] == "National Parks Webcams" and len(cleaned) > 1:
        cleaned = cleaned[1:]
    return cleaned


def page_title(lines, fallback):
    if fallback == "National Parks Webcams":
        return fallback
    for line in lines:
        if line not in SKIP_TEXT and len(line) < 120:
            return line
    return fallback


def write_markdown(url, nav_text, html_path, nav_titles):
    parser = parse_file(html_path)
    lines = clean_lines(parser.items, nav_titles)
    title = page_title(lines, nav_text or slug_for_url(url))
    slug = slug_for_url(url)
    md_path = PAGES / (safe_filename(slug).replace(".html", ".md"))

    links = []
    seen_links = set()
    for href, text in parser.links:
        abs_url = urljoin(BASE, href)
        if abs_url in seen_links:
            continue
        seen_links.add(abs_url)
        label = text or href
        if label not in SKIP_TEXT:
            links.append((label, abs_url))

    images = []
    seen_images = set()
    for src, alt in parser.images:
        abs_src = urljoin(BASE, src)
        if abs_src in seen_images:
            continue
        seen_images.add(abs_src)
        images.append((alt, abs_src))

    embeds = []
    seen_embeds = set()
    for embed in parser.embeds:
        src = embed.get("src") or ""
        abs_src = urljoin(BASE, src) if src else ""
        key = abs_src or embed.get("id") or embed.get("name")
        if not key or key in seen_embeds:
            continue
        seen_embeds.add(key)
        label = embed.get("aria_label") or embed.get("title") or embed.get("id") or "Embed"
        embeds.append((label, abs_src, embed))

    with md_path.open("w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"Source: {url}\n\n")
        for line in lines:
            if line == title:
                continue
            f.write(line + "\n\n")
        if images:
            f.write("## Images\n\n")
            for alt, src in images:
                f.write(f"- {alt or 'Image'}: {src}\n")
            f.write("\n")
        if embeds:
            f.write("## Embeds\n\n")
            for label, src, embed in embeds:
                if src:
                    f.write(f"- {label}: {src}\n")
                else:
                    identifier = embed.get("id") or embed.get("name") or "no id"
                    f.write(f"- {label}: embedded Google Sites frame ({identifier}); no direct `src` in published HTML\n")
            f.write("\n")
        if links:
            f.write("## Links\n\n")
            for label, href in links:
                f.write(f"- {label}: {href}\n")

    resources = []
    for label, href in links:
        resources.append({"page": title, "page_url": url, "type": "link", "label": label, "url": href})
    for alt, src in images:
        resources.append({"page": title, "page_url": url, "type": "image", "label": alt or "Image", "url": src})
    for label, src, embed in embeds:
        resources.append(
            {
                "page": title,
                "page_url": url,
                "type": "embed",
                "label": label,
                "url": src or f"google-sites-frame:{embed.get('id') or embed.get('name')}",
            }
        )

    return {
        "title": title,
        "url": url,
        "slug": slug,
        "markdown": str(md_path.relative_to(ROOT)),
        "raw_html": str(html_path.relative_to(ROOT)),
        "line_count": len(lines),
        "link_count": len(links),
        "image_count": len(images),
        "embed_count": len(embeds),
    }, resources


def main():
    PAGES.mkdir(parents=True, exist_ok=True)
    seed = RAW / "home.html"
    if not seed.exists():
        seed = fetch(f"{BASE}/national-park-webcam-home")

    pages = discover(seed)
    nav_titles = [text for _, text in pages if text]
    results = []
    resources = []
    for url, nav_text in pages:
        print(f"fetching {url}", file=sys.stderr)
        html_path = fetch(url)
        result, page_resources = write_markdown(url, nav_text, html_path, nav_titles)
        results.append(result)
        resources.extend(page_resources)

    with (ROOT / "index.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "title",
                "url",
                "slug",
                "markdown",
                "raw_html",
                "line_count",
                "link_count",
                "image_count",
                "embed_count",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    with (ROOT / "resources.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["page", "page_url", "type", "label", "url"])
        writer.writeheader()
        writer.writerows(resources)

    with (ROOT / "README.md").open("w", encoding="utf-8") as f:
        f.write("# nationalparkcam.com content export\n\n")
        f.write(f"Exported {len(results)} pages from {BASE}.\n\n")
        f.write("- `pages/`: Markdown content, one file per page\n")
        f.write("- `raw/`: downloaded Google Sites HTML snapshots\n")
        f.write("- `index.csv`: page inventory\n\n")
        f.write("- `resources.csv`: links, image URLs, and iframe embeds by page\n\n")
        f.write("## Pages\n\n")
        for row in results:
            f.write(f"- [{row['title']}]({row['markdown']}) - {row['url']}\n")

    print(f"Exported {len(results)} pages", file=sys.stderr)


if __name__ == "__main__":
    main()
