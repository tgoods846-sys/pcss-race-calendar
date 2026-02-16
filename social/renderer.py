"""Pillow drawing primitives: text wrapping, pill badges, logo compositing, venue photos."""

from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
from social.config import COLOR_BG, COLOR_PRIMARY, COLOR_WHITE, COLOR_MUTED, LOGO_PATH, VENUES_DIR, VENUE_FILENAME_MAP, VENUE_CROP_ALIGN, VENUE_CROP_VALIGN


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def create_canvas(width: int, height: int) -> Image.Image:
    """Create a new image with the dark background."""
    return Image.new("RGB", (width, height), hex_to_rgb(COLOR_BG))


def draw_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    color: str = COLOR_WHITE,
    anchor: str = "lt",
) -> int:
    """Draw text and return the height consumed."""
    draw.text((x, y), text, fill=hex_to_rgb(color), font=font, anchor=anchor)
    bbox = font.getbbox(text)
    return bbox[3] - bbox[1]


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        if bbox[2] > max_width and current_line:
            lines.append(current_line)
            current_line = word
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)
    return lines


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    color: str = COLOR_WHITE,
    line_spacing: int = 8,
) -> int:
    """Draw word-wrapped text. Returns total height consumed."""
    lines = wrap_text(text, font, max_width)
    total_height = 0
    for i, line in enumerate(lines):
        draw_text(draw, line, x, y + total_height, font, color)
        bbox = font.getbbox(line)
        line_h = bbox[3] - bbox[1]
        total_height += line_h + (line_spacing if i < len(lines) - 1 else 0)
    return total_height


def draw_pill(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    bg_color: str,
    text_color: str = COLOR_WHITE,
    padding_x: int = 16,
    padding_y: int = 8,
) -> int:
    """Draw a rounded-rect pill badge. Returns the pill width."""
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    pill_w = text_w + padding_x * 2
    pill_h = text_h + padding_y * 2
    radius = pill_h // 2
    draw.rounded_rectangle(
        [x, y, x + pill_w, y + pill_h],
        radius=radius,
        fill=hex_to_rgb(bg_color),
    )
    # Center text inside pill
    text_x = x + padding_x
    text_y = y + padding_y
    draw.text((text_x, text_y), text, fill=hex_to_rgb(text_color), font=font)
    return pill_w


def draw_pills_row(
    draw: ImageDraw.ImageDraw,
    items: list[tuple[str, str]],
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    gap: int = 10,
    text_color: str = COLOR_WHITE,
    padding_x: int = 16,
    padding_y: int = 8,
) -> tuple[int, int]:
    """Draw a row of pills. Returns (total_width, pill_height)."""
    cursor_x = x
    pill_height = 0
    for label, color in items:
        pw = draw_pill(draw, label, cursor_x, y, font, color, text_color, padding_x, padding_y)
        bbox = font.getbbox(label)
        pill_height = max(pill_height, (bbox[3] - bbox[1]) + padding_y * 2)
        cursor_x += pw + gap
    return cursor_x - x - gap, pill_height


def draw_accent_line(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    thickness: int = 3,
    color: str = COLOR_PRIMARY,
) -> int:
    """Draw a horizontal accent line. Returns height consumed."""
    draw.rectangle(
        [x, y, x + width, y + thickness],
        fill=hex_to_rgb(color),
    )
    return thickness


def composite_logo(
    canvas: Image.Image,
    x: int,
    y: int,
    max_width: int,
    max_height: int,
) -> tuple[int, int]:
    """Composite the horizontal dark logo onto the canvas. Returns (width, height) used."""
    logo = Image.open(LOGO_PATH)
    # Scale to fit within max dimensions while preserving aspect ratio
    ratio = min(max_width / logo.width, max_height / logo.height)
    new_w = int(logo.width * ratio)
    new_h = int(logo.height * ratio)
    logo = logo.resize((new_w, new_h), Image.LANCZOS)
    canvas.paste(logo, (x, y))
    return new_w, new_h


def draw_footer(
    draw: ImageDraw.ImageDraw,
    canvas_width: int,
    canvas_height: int,
    font: ImageFont.FreeTypeFont,
) -> None:
    """Draw the sim.sports URL footer at the bottom center."""
    text = "sim.sports"
    bbox = font.getbbox(text)
    text_w = bbox[2] - bbox[0]
    x = (canvas_width - text_w) // 2
    y = canvas_height - 60
    draw_text(draw, text, x, y, font, COLOR_MUTED)


def _resolve_venue_photo(venue_name: str) -> Optional[Path]:
    """Find the venue photo file by name. Tries .jpg then .png. Returns path or None."""
    if not VENUES_DIR.exists():
        return None
    filename = VENUE_FILENAME_MAP.get(venue_name)
    if filename:
        for ext in (".jpg", ".png", ".webp"):
            path = VENUES_DIR / f"{filename}{ext}"
            if path.exists():
                return path
    # Fallback to default
    for ext in (".jpg", ".png", ".webp"):
        path = VENUES_DIR / f"default{ext}"
        if path.exists():
            return path
    return None


def composite_venue_photo(
    canvas: Image.Image,
    x: int,
    y: int,
    width: int,
    height: int,
    venue_name: str,
) -> None:
    """Composite a venue photo into the given region with center-crop and gradient overlay.

    If no venue photo is found, fills with a subtle dark gradient.
    Adds a dark gradient overlay at the top edge for text readability.
    """
    photo_path = _resolve_venue_photo(venue_name)

    if photo_path:
        photo = Image.open(photo_path).convert("RGB")
        # Crop to fill the target region, with per-venue alignment
        filename = VENUE_FILENAME_MAP.get(venue_name, "")
        h_align = VENUE_CROP_ALIGN.get(filename, 0.5)
        src_ratio = photo.width / photo.height
        dst_ratio = width / height
        if src_ratio > dst_ratio:
            # Photo is wider — crop sides
            new_h = photo.height
            new_w = int(new_h * dst_ratio)
            left = int((photo.width - new_w) * h_align)
            photo = photo.crop((left, 0, left + new_w, new_h))
        else:
            # Photo is taller — crop top/bottom
            new_w = photo.width
            new_h = int(new_w / dst_ratio)
            v_align = VENUE_CROP_VALIGN.get(filename, 0.5)
            top = int((photo.height - new_h) * v_align)
            photo = photo.crop((0, top, new_w, top + new_h))
        photo = photo.resize((width, height), Image.LANCZOS)
    else:
        # No photo at all — generate a subtle dark gradient
        photo = Image.new("RGB", (width, height), hex_to_rgb(COLOR_BG))
        draw = ImageDraw.Draw(photo)
        for row in range(height):
            t = row / height
            r = int(20 + 25 * t)
            g = int(20 + 25 * t)
            b = int(25 + 35 * t)
            draw.line([(0, row), (width, row)], fill=(r, g, b))

    # Add dark gradient overlay at top edge (for readability where info section meets photo)
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    gradient_height = min(height // 3, 200)
    for row in range(gradient_height):
        alpha = int(180 * (1 - row / gradient_height))
        overlay_draw.line([(0, row), (width, row)], fill=(20, 20, 20, alpha))

    # Composite: paste photo, then overlay
    photo_rgba = photo.convert("RGBA")
    composited = Image.alpha_composite(photo_rgba, overlay)
    canvas.paste(composited.convert("RGB"), (x, y))
