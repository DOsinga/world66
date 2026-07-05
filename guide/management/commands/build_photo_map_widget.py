import json
from pathlib import Path

import frontmatter
from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageOps


CONTENT_DIR = Path(settings.BASE_DIR) / "content"
OUT_DIR = Path(settings.BASE_DIR) / "static" / "widgets"


class Command(BaseCommand):
    help = "Build the offline photo-map widget mosaic and metadata."

    def add_arguments(self, parser):
        parser.add_argument("--cols", type=int, default=36)
        parser.add_argument("--rows", type=int, default=18)
        parser.add_argument("--tile-size", type=int, default=64)

    def handle(self, *args, **options):
        cols = options["cols"]
        rows = options["rows"]
        tile_size = options["tile_size"]
        tiles = self.pick_tiles(cols, rows)
        OUT_DIR.mkdir(parents=True, exist_ok=True)

        mosaic = Image.new("RGB", (cols * tile_size, rows * tile_size), "#d6e2e3")
        radius = max(6, tile_size // 5)

        metadata = {
            "cols": cols,
            "rows": rows,
            "tile_size": tile_size,
            "image": "/static/widgets/photo-map.png",
            "tiles": [],
        }
        for key, item in sorted(tiles.items()):
            x, y = key
            tile = self.square_image(item["image_file"], tile_size)
            if tile:
                corners = self.exposed_corners(key, tiles)
                mask = self.corner_mask(tile_size, radius, corners)
                mosaic.paste(tile, (x * tile_size, y * tile_size), mask)
            else:
                corners = []
            metadata["tiles"].append({
                "x": x,
                "y": y,
                "corners": corners,
                "title": item["title"],
                "url": item["url"],
                "image": item["image_url"],
                "snippet": item["snippet"],
                "score": item["score"],
                "type": item["type"],
            })

        mosaic.save(OUT_DIR / "photo-map.png", optimize=True)
        (OUT_DIR / "photo-map.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        self.stdout.write(
            self.style.SUCCESS(f"Wrote {len(metadata['tiles'])} tiles to {OUT_DIR / 'photo-map.png'}")
        )

    def pick_tiles(self, cols, rows):
        tiles = {}
        for md_file in sorted(CONTENT_DIR.rglob("*.md")):
            item = self.item_for_file(md_file)
            if not item:
                continue
            x = int((item["lng"] + 180) / 360 * cols)
            y = int((90 - item["lat"]) / 180 * rows)
            if x < 0 or x >= cols or y < 0 or y >= rows:
                continue
            key = (x, y)
            current = tiles.get(key)
            if not current or item["score"] > current["score"]:
                tiles[key] = item
        return tiles

    def exposed_corners(self, key, tiles):
        x, y = key
        left = (x - 1, y) in tiles
        right = (x + 1, y) in tiles
        up = (x, y - 1) in tiles
        down = (x, y + 1) in tiles
        corners = {
            "tl": not left and not up,
            "tr": not right and not up,
            "br": not right and not down,
            "bl": not left and not down,
        }
        return [name for name, exposed in corners.items() if exposed]

    def corner_mask(self, size, radius, corners):
        scale = 4
        width = size * scale
        height = size * scale
        radius *= scale
        mask = Image.new("L", (width, height), 255)
        draw = ImageDraw.Draw(mask)

        if "tl" in corners:
            draw.rectangle((0, 0, radius, radius), fill=0)
            draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=255)
        if "tr" in corners:
            draw.rectangle((width - radius, 0, width, radius), fill=0)
            draw.pieslice((width - radius * 2, 0, width, radius * 2), 270, 360, fill=255)
        if "br" in corners:
            draw.rectangle((width - radius, height - radius, width, height), fill=0)
            draw.pieslice((width - radius * 2, height - radius * 2, width, height), 0, 90, fill=255)
        if "bl" in corners:
            draw.rectangle((0, height - radius, radius, height), fill=0)
            draw.pieslice((0, height - radius * 2, radius * 2, height), 90, 180, fill=255)

        return mask.resize((size, size), Image.Resampling.LANCZOS)

    def item_for_file(self, md_file):
        post = frontmatter.load(md_file)
        meta = post.metadata
        if meta.get("type") not in {"location", "poi"}:
            return None
        image = meta.get("image")
        if not image:
            return None
        try:
            lat = float(meta.get("latitude"))
            lng = float(meta.get("longitude"))
        except (TypeError, ValueError):
            return None
        try:
            score = float(meta.get("score", 0) or 0)
        except (TypeError, ValueError):
            score = 0
        image_file = md_file.parent / image
        if not image_file.is_file():
            return None
        url_path = self.url_path(md_file)
        image_url = "/content-image/" + str(image_file.relative_to(CONTENT_DIR))
        return {
            "title": meta.get("title") or md_file.stem.replace("_", " ").title(),
            "url": "/" + url_path,
            "image_url": image_url,
            "image_file": image_file,
            "snippet": meta.get("snippet") or self.snippet(post.content),
            "lat": lat,
            "lng": lng,
            "score": score,
            "type": meta.get("type"),
        }

    def square_image(self, image_file, tile_size):
        try:
            image = Image.open(image_file)
            image = ImageOps.exif_transpose(image).convert("RGB")
        except Exception:
            return None
        width, height = image.size
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        image = image.crop((left, top, left + side, top + side))
        return image.resize((tile_size, tile_size), Image.Resampling.LANCZOS)

    def url_path(self, md_file):
        rel = md_file.relative_to(CONTENT_DIR)
        parts = list(rel.parts)
        stem = parts[-1][:-3]
        if len(parts) >= 2 and stem == parts[-2]:
            return "/".join(parts[:-1])
        return "/".join(parts[:-1] + [stem]) if len(parts) > 1 else stem

    def snippet(self, body):
        for paragraph in body.split("\n\n"):
            text = " ".join(paragraph.strip().split())
            if text:
                return text[:180].rsplit(" ", 1)[0] + ("..." if len(text) > 180 else "")
        return ""
