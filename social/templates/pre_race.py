"""Pre-race announcement template with split layout."""

from PIL import Image

from social.captions import display_title
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


class PreRaceTemplate(BaseTemplate):
    """Pre-race announcement with venue photo split layout."""

    def render(self, event: dict) -> Image.Image:
        y = self.draw_header()

        is_compact = self.fmt in ("facebook", "post")
        spacing = 15 if is_compact else 25

        # Event name as main title (word-wrapped)
        name_size = self._scale_font(28 if is_compact else 38)
        name_font = load_font("Bold", name_size)
        h = draw_wrapped_text(
            self.draw, display_title(event), self.margin, y,
            name_font, self.content_width, COLOR_WHITE,
        )
        y += h + spacing

        # Discipline + age group pills
        disciplines = event.get("disciplines", [])
        age_groups = event.get("age_groups", [])

        if self.fmt == "facebook":
            # Combined single row for facebook
            all_items = [
                (d, DISCIPLINE_COLORS.get(d, COLOR_PRIMARY))
                for d in disciplines
            ] + [(ag, "#475569") for ag in age_groups]
            if all_items:
                pill_font = load_font("Bold", self._scale_font(16))
                _, pill_h = draw_pills_row(
                    self.draw, all_items, self.margin, y, pill_font,
                    padding_x=12, padding_y=5,
                )
                y += pill_h + spacing
        else:
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

            if age_groups:
                age_font = load_font("SemiBold", self._scale_font(14 if is_compact else 16))
                age_items = [(ag, "#475569") for ag in age_groups]
                _, age_h = draw_pills_row(
                    self.draw, age_items, self.margin, y, age_font,
                    padding_x=12, padding_y=6,
                )
                y += age_h + spacing

        # Date + venue on one line (or two short lines for compact)
        detail_font = load_font("SemiBold", self._scale_font(16 if is_compact else 22))
        venue = event.get("venue", "TBD")
        state = event.get("state", "")
        venue_text = f"{venue}, {state}" if state else venue
        date_display = event.get("dates", {}).get("display", "")

        if date_display:
            detail_line = f"{date_display}  \u2022  {venue_text}"
        else:
            detail_line = venue_text
        h = draw_text(self.draw, detail_line, self.margin, y, detail_font, COLOR_MUTED)
        y += h

        # Venue photo from below content to bottom
        self.draw_venue_section(venue, y)
        self.draw_footer_section()
        return self.canvas
