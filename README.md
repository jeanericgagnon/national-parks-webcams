# National Parks Webcams

A modern static rebuild of the original Google Sites version of National Parks Webcams.

The generated site lives in `docs/`, which makes it ready for GitHub Pages using the
`main` branch and `/docs` publishing source.

## Project Structure

- `docs/` - generated static website
- `assets/` - source CSS and JavaScript copied into `docs/assets`
- `scripts/build_site.py` - generator that turns the export into HTML pages
- `nationalparkcam_export/` - preserved crawl/export from the original Google Site

## Build

```bash
python3 scripts/build_site.py
```

## Preview

```bash
python3 -m http.server 8000 --directory docs
```

Then open `http://127.0.0.1:8000`.

## Migration Notes

The export includes page content, images, links, maps, YouTube embeds, and Google
Sites custom embeds. Some old custom embeds are visible only as Google Sites frame
IDs because the published Google Sites HTML does not expose the original inner URL.
Those are flagged on each park page and in `nationalparkcam_export/resources.csv`.
