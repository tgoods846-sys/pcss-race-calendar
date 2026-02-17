"""Weekly preview 'THIS WEEK IN PC SKI RACING' template."""

from PIL import Image

from social.config import (
    COLOR_PRIMARY,
    COLOR_WHITE,
    COLOR_MUTED,
    DISCIPLINE_COLORS,
)
from social.font_loader import load_font
from social.renderer import (
    composite_venue_photo,
    draw_text,
    draw_wrapped_text,
    draw_pills_row,
    draw_accent_line,
    hex_to_rgb,
)
from social.templates.base import BaseTemplate


class WeeklyPreviewTemplate(BaseTemplate):
    """'THIS WEEK IN PC SKI RACING' multi-event graphic."""

    TITLE_LINE_1 = "THIS WEEK IN"
    TITLE_LINE_2 = "PC SKI RACING"
    MAX_EVENTS = 5

    def render(self, events: list[dict]) -> Image.Image:
        y = self.draw_header()

        is_compact = self.fmt in ("facebook", "post")
        is_facebook = self.fmt == "facebook"
        if is_facebook:
            y -= 15  # Tighten gap between header and title
        spacing = 10 if is_facebook else (15 if is_compact else 20)

        # Title
        title_size = self._scale_font(28 if is_compact else 36)
        title_font = load_font("Bold", title_size)
        h = draw_text(
            self.draw, self.TITLE_LINE_1, self.margin, y,
            title_font, COLOR_PRIMARY,
        )
        y += h + 5
        h = draw_text(
            self.draw, self.TITLE_LINE_2, self.margin, y,
            title_font, COLOR_PRIMARY,
        )
        y += h + spacing

        # Accent bar
        draw_accent_line(self.draw, self.margin, y, self.content_width)
        y += spacing + 5

        # Calculate available space for event cards
        footer_reserved = 40 if is_facebook else 80
        available_height = self.height - y - footer_reserved
        num_events = min(len(events), self.MAX_EVENTS)

        if is_facebook and num_events > 0:
            # Facebook: side-by-side venue photos with text overlay
            y = self._draw_facebook_layout(events[:self.MAX_EVENTS], y, available_height)
        else:
            # Dynamic card height based on event count
            card_height = min(
                available_height // max(num_events, 1),
                700 if not is_compact else 350,
            )

            for i, event in enumerate(events[:self.MAX_EVENTS]):
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

        self.draw_footer_section()
        return self.canvas

    def _draw_facebook_layout(
        self, events: list[dict], y: int, available_height: int
    ) -> int:
        """Draw side-by-side venue photos with event info overlaid. Facebook only."""
        gap = 12
        num = len(events)
        col_width = (self.content_width - gap * (num - 1)) // num
        photo_h = available_height

        name_font = load_font("Bold", self._scale_font(16))
        detail_font = load_font("SemiBold", self._scale_font(13))

        for i, event in enumerate(events):
            x = self.margin + i * (col_width + gap)
            venue_name = event.get("venue", "")
            composite_venue_photo(
                self.canvas, x, y, col_width, photo_h, venue_name,
            )

            # Draw event text at bottom of photo with dark scrim
            text_y = y + photo_h
            venue = event.get("venue", "TBD")
            state = event.get("state", "")
            venue_text = f"{venue}, {state}" if state else venue
            date_display = event.get("dates", {}).get("display", "")
            detail_text = f"{venue_text}  |  {date_display}" if date_display else venue_text

            # Measure text heights
            name_bbox = name_font.getbbox(event["name"])
            name_h = name_bbox[3] - name_bbox[1]
            detail_bbox = detail_font.getbbox(detail_text)
            detail_h = detail_bbox[3] - detail_bbox[1]
            text_block_h = name_h + detail_h + 16  # padding

            # Dark scrim at bottom of photo
            scrim_y = y + photo_h - text_block_h - 8
            for row in range(scrim_y, y + photo_h):
                t = (row - scrim_y) / (text_block_h + 8)
                alpha = int(160 + 60 * t)
                self.draw.line(
                    [(x, row), (x + col_width, row)],
                    fill=(0, 0, 0, min(alpha, 220)),
                )

            # Draw text over scrim
            text_x = x + 10
            text_y = scrim_y + 8
            # Use wrapped text for name in case it's long
            draw_wrapped_text(
                self.draw, event["name"], text_x, text_y,
                name_font, col_width - 20, COLOR_WHITE, line_spacing=2,
            )
            draw_text(
                self.draw, detail_text, text_x, y + photo_h - detail_h - 8,
                detail_font, COLOR_WHITE,
            )

        return y + photo_h

    def _draw_event_card(
        self, event: dict, y: int, max_height: int, is_compact: bool
    ) -> int:
        """Draw a single event card. Returns y position after card."""
        card_start = y
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
        detail_font = load_font("SemiBold", self._scale_font(16 if is_compact else 20))
        venue = event.get("venue", "TBD")
        state = event.get("state", "")
        venue_text = f"{venue}, {state}" if state else venue
        date_display = event.get("dates", {}).get("display", "")

        if is_compact:
            detail_text = f"{venue_text}  |  {date_display}" if date_display else venue_text
            h = draw_text(self.draw, detail_text, self.margin, y, detail_font, COLOR_WHITE)
            y += h + spacing
        else:
            h = draw_text(self.draw, venue_text, self.margin, y, detail_font, COLOR_WHITE)
            y += h + 6
            if date_display:
                h = draw_text(self.draw, date_display, self.margin, y, detail_font, COLOR_WHITE)
                y += h + spacing

        # Discipline pills (skip on facebook to save space)
        disciplines = event.get("disciplines", [])
        if disciplines and self.fmt != "facebook":
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

        # Venue photo strip — fills remaining card space
        text_used = y - card_start
        remaining = max_height - text_used - spacing
        photo_h = remaining if remaining > 30 else 0
        if photo_h > 0:
            venue_name = event.get("venue", "")
            composite_venue_photo(
                self.canvas,
                self.margin, y,
                self.content_width, photo_h,
                venue_name,
            )
            y += photo_h + spacing

        return y
