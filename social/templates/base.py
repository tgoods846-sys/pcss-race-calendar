"""Base template class with shared header/footer/venue rendering."""

from abc import ABC, abstractmethod
from pathlib import Path
from PIL import Image, ImageDraw

from social.config import FORMATS, COLOR_PRIMARY, COLOR_WHITE, COLOR_MUTED
from social.font_loader import load_font
from social.renderer import (
    create_canvas,
    composite_logo,
    composite_venue_photo,
    draw_accent_line,
    draw_footer,
    draw_text,
)


class BaseTemplate(ABC):
    """Base class for all social image templates."""

    def __init__(self, fmt: str):
        self.fmt = fmt
        self.width, self.height = FORMATS[fmt]
        self.canvas = create_canvas(self.width, self.height)
        self.draw = ImageDraw.Draw(self.canvas)
        # Standard margins scale with image width
        self.margin = int(self.width * 0.07)
        self.content_width = self.width - self.margin * 2

    def draw_header(self) -> int:
        """Draw the logo + tagline below + blue accent line. Returns y position after header."""
        is_fb = self.fmt == "facebook"
        y = int(self.margin * 0.35) if is_fb else self.margin

        # Logo sizing based on format
        if is_fb:
            logo_max_w = int(self.width * 0.13)
            logo_max_h = 26
        elif self.fmt == "post":
            logo_max_w = int(self.width * 0.28)
            logo_max_h = 58
        else:  # story, reel
            logo_max_w = int(self.width * 0.33)
            logo_max_h = 68

        # First pass: composite at 0,0 area to get actual size
        logo_w, logo_h = composite_logo(
            self.canvas, 0, y, logo_max_w, logo_max_h
        )
        # Clear that area and re-composite centered
        from social.renderer import hex_to_rgb
        from social.config import COLOR_BG
        self.draw.rectangle([0, y, logo_w, y + logo_h], fill=hex_to_rgb(COLOR_BG))
        logo_x = (self.width - logo_w) // 2
        composite_logo(self.canvas, logo_x, y, logo_max_w, logo_max_h)
        y += logo_h + (4 if is_fb else 10)

        # Tagline below logo — white, bold, centered
        tagline_size = self._scale_font(12 if is_fb else 22)
        tagline_font = load_font("Bold", tagline_size)
        tagline_text = "INDOOR SKI + GOLF"
        tagline_bbox = tagline_font.getbbox(tagline_text)
        tagline_w = tagline_bbox[2] - tagline_bbox[0]
        tagline_x = (self.width - tagline_w) // 2
        draw_text(
            self.draw, tagline_text, tagline_x, y,
            tagline_font, COLOR_WHITE,
        )
        y += (tagline_bbox[3] - tagline_bbox[1]) + (5 if is_fb else 12)

        # Blue accent line
        draw_accent_line(self.draw, self.margin, y, self.content_width)
        y += 10 if is_fb else 25
        return y

    def draw_venue_section(self, venue_name: str, y_start: int = 0) -> None:
        """Composite venue photo from y_start to the bottom of the canvas.

        Args:
            venue_name: Venue name for photo lookup.
            y_start: Y position where venue photo begins (just below content).
        """
        # Add a small gap below content
        gap = 20
        venue_y = y_start + gap
        venue_height = self.height - venue_y
        if venue_height < 50:
            return
        composite_venue_photo(
            self.canvas,
            0, venue_y,
            self.width, venue_height,
            venue_name,
        )

    def draw_footer_section(self) -> None:
        """Draw the footer over the venue photo section."""
        footer_font = load_font("Regular", self._scale_font(14))
        draw_footer(self.draw, self.width, self.height, footer_font)

    def _scale_font(self, base_size: int) -> int:
        """Scale font size relative to story format (1080 width)."""
        return max(10, int(base_size * (self.width / 1080)))

    @abstractmethod
    def render(self, **kwargs) -> Image.Image:
        """Render the template with given data. Returns the PIL Image."""

    def save(self, path: Path) -> None:
        """Save the rendered image to disk."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.canvas.save(str(path), "PNG", quality=95)
