"""Weekly preview 'THIS WEEK IN YOUTH SKI RACING' template."""

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
    hex_to_rgb,
)
from social.templates.base import BaseTemplate


class WeeklyPreviewTemplate(BaseTemplate):
    """'THIS WEEK IN YOUTH SKI RACING' multi-event graphic."""

    def render(self, events: list[dict]) -> Image.Image:
        y = self.draw_header()

        is_compact = self.fmt in ("facebook", "post")
        spacing = 15 if is_compact else 20

        # Title
        title_size = self._scale_font(28 if is_compact else 36)
        title_font = load_font("Bold", title_size)
        h = draw_text(
            self.draw, "THIS WEEK IN", self.margin, y,
            title_font, COLOR_PRIMARY,
        )
        y += h + 5
        h = draw_text(
            self.draw, "YOUTH SKI RACING", self.margin, y,
            title_font, COLOR_PRIMARY,
        )
        y += h + spacing

        # Accent bar
        draw_accent_line(self.draw, self.margin, y, self.content_width)
        y += spacing + 5

        # Calculate available space for event cards
        footer_reserved = 80
        available_height = self.height - y - footer_reserved
        num_events = min(len(events), 5)

        # Dynamic card height based on event count
        card_height = min(
            available_height // max(num_events, 1),
            280 if not is_compact else 160,
        )

        for i, event in enumerate(events[:5]):
            y = self._draw_event_card(event, y, card_height, is_compact)
            if i < num_events - 1:
                # Separator line
                sep_y = y + 5
                self.draw.line(
                    [(self.margin, sep_y), (self.margin + self.content_width, sep_y)],
                    fill=hex_to_rgb("#333333"),
                    width=1,
                )
                y = sep_y + 10

        # Use default venue photo for background
        self.draw_venue_section("", y)
        self.draw_footer_section()
        return self.canvas

    def _draw_event_card(
        self, event: dict, y: int, max_height: int, is_compact: bool
    ) -> int:
        """Draw a single event card. Returns y position after card."""
        spacing = 8 if is_compact else 12

        # Event name
        name_size = self._scale_font(18 if is_compact else 24)
        name_font = load_font("Bold", name_size)
        h = draw_wrapped_text(
            self.draw, event["name"], self.margin, y,
            name_font, self.content_width, COLOR_WHITE,
            line_spacing=4,
        )
        y += h + spacing

        # Venue + date on one line for compact, separate for tall
        detail_font = load_font("Regular", self._scale_font(13 if is_compact else 16))
        venue = event.get("venue", "TBD")
        state = event.get("state", "")
        venue_text = f"{venue}, {state}" if state else venue
        date_display = event.get("dates", {}).get("display", "")

        if is_compact:
            detail_text = f"{venue_text}  |  {date_display}" if date_display else venue_text
            h = draw_text(self.draw, detail_text, self.margin, y, detail_font, COLOR_MUTED)
            y += h + spacing
        else:
            h = draw_text(self.draw, venue_text, self.margin, y, detail_font, COLOR_WHITE)
            y += h + 6
            if date_display:
                h = draw_text(self.draw, date_display, self.margin, y, detail_font, COLOR_MUTED)
                y += h + spacing

        # Discipline pills (smaller)
        disciplines = event.get("disciplines", [])
        if disciplines:
            pill_font = load_font("Bold", self._scale_font(12 if is_compact else 15))
            items = [
                (d, DISCIPLINE_COLORS.get(d, COLOR_PRIMARY))
                for d in disciplines
            ]
            _, pill_h = draw_pills_row(
                self.draw, items, self.margin, y, pill_font,
                padding_x=10, padding_y=5,
            )
            y += pill_h + spacing

        return y
