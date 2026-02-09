"""Race day 'RACE DAY!' template with split layout."""

from PIL import Image

from social.config import (
    COLOR_PRIMARY,
    COLOR_WHITE,
    COLOR_MUTED,
    DISCIPLINE_COLORS,
)
from social.font_loader import load_font
from social.renderer import (
    draw_text,
    draw_wrapped_text,
    draw_pills_row,
    draw_accent_line,
)
from social.templates.base import BaseTemplate


class RaceDayTemplate(BaseTemplate):
    """'RACE DAY!' graphic with venue photo split layout."""

    def render(self, event: dict) -> Image.Image:
        y = self.draw_header()

        is_compact = self.fmt in ("facebook", "post")
        spacing = 15 if is_compact else 25

        # "RACE DAY!" title
        title_size = self._scale_font(44 if is_compact else 56)
        title_font = load_font("Bold", title_size)
        h = draw_text(self.draw, "RACE DAY!", self.margin, y, title_font, COLOR_PRIMARY)
        y += h + spacing

        # Accent bar
        draw_accent_line(self.draw, self.margin, y, self.content_width, thickness=4)
        y += spacing

        # Event name (word-wrapped)
        name_size = self._scale_font(28 if is_compact else 38)
        name_font = load_font("Bold", name_size)
        h = draw_wrapped_text(
            self.draw, event["name"], self.margin, y,
            name_font, self.content_width, COLOR_WHITE,
        )
        y += h + spacing

        # Discipline pills in a row
        disciplines = event.get("disciplines", [])
        if disciplines:
            pill_font = load_font("Bold", self._scale_font(18 if is_compact else 22))
            items = [
                (d, DISCIPLINE_COLORS.get(d, COLOR_PRIMARY))
                for d in disciplines
            ]
            _, pill_h = draw_pills_row(
                self.draw, items, self.margin, y, pill_font,
            )
            y += pill_h + spacing

        # Age group pills
        age_groups = event.get("age_groups", [])
        if age_groups:
            age_font = load_font("SemiBold", self._scale_font(14 if is_compact else 16))
            age_items = [(ag, "#475569") for ag in age_groups]
            _, age_h = draw_pills_row(
                self.draw, age_items, self.margin, y, age_font,
                padding_x=12, padding_y=6,
            )
            y += age_h + spacing

        # Venue info line
        detail_font = load_font("SemiBold", self._scale_font(16 if is_compact else 22))
        venue = event.get("venue", "TBD")
        state = event.get("state", "")
        venue_text = f"{venue}, {state}" if state else venue
        draw_text(self.draw, venue_text, self.margin, y, detail_font, COLOR_MUTED)
        bbox = detail_font.getbbox(venue_text)
        y += (bbox[3] - bbox[1]) + (10 if is_compact else 15)

        # "TODAY" in bold primary blue
        today_font = load_font("Bold", self._scale_font(22 if is_compact else 28))
        h = draw_text(self.draw, "TODAY", self.margin, y, today_font, COLOR_PRIMARY)
        y += h

        # Venue photo from below content to bottom
        self.draw_venue_section(venue, y)
        self.draw_footer_section()
        return self.canvas
