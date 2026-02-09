"""Load Montserrat TTF fonts from the fonts/ directory."""

from PIL import ImageFont
from social.config import FONTS_DIR


def load_font(weight: str = "Regular", size: int = 32) -> ImageFont.FreeTypeFont:
    """Load a Montserrat font at the given weight and size.

    Args:
        weight: "Regular", "Bold", or "SemiBold"
        size: Font size in pixels
    """
    path = FONTS_DIR / f"Montserrat-{weight}.ttf"
    if not path.exists():
        raise FileNotFoundError(f"Font not found: {path}")
    return ImageFont.truetype(str(path), size)
