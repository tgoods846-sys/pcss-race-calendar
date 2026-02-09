"""Monthly calendar grid template showing all events as venue-colored bars."""

from __future__ import annotations

import calendar
from datetime import date

from PIL import Image

from social.config import (
    COLOR_PRIMARY,
    COLOR_WHITE,
    COLOR_MUTED,
    COLOR_BG,
)
from social.font_loader import load_font
from social.renderer import (
    composite_logo,
    draw_text,
    draw_accent_line,
    hex_to_rgb,
)
from social.templates.base import BaseTemplate


# Format-adaptive constants keyed by format name
_FORMAT_CONSTANTS = {
    "story": {
        "bar_height": 28,
        "day_num_font": 16,
        "bar_label_font": 14,
        "dow_header_font": 16,
        "title_font": 36,
        "cell_gap": 2,
        "max_lanes": 4,
    },
    "reel": {
        "bar_height": 28,
        "day_num_font": 16,
        "bar_label_font": 14,
        "dow_header_font": 16,
        "title_font": 36,
        "cell_gap": 2,
        "max_lanes": 4,
    },
    "post": {
        "bar_height": 22,
        "day_num_font": 14,
        "bar_label_font": 12,
        "dow_header_font": 14,
        "title_font": 28,
        "cell_gap": 2,
        "max_lanes": 3,
    },
    "facebook": {
        "bar_height": 18,
        "day_num_font": 12,
        "bar_label_font": 10,
        "dow_header_font": 12,
        "title_font": 22,
        "cell_gap": 1,
        "max_lanes": 2,
    },
}

_DOW_HEADERS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

_GRID_LINE_COLOR = "#333333"
_CELL_BG_COLOR = "#1E1E1E"

# Venue colors — visually distinct on dark backgrounds
VENUE_COLORS = {
    "Park City": "#2563EB",       # blue
    "Snowbird": "#06B6D4",        # cyan
    "Snowbasin": "#8B5CF6",       # violet
    "Sun Valley": "#F59E0B",      # amber
    "Grand Targhee": "#10B981",   # emerald
    "Jackson Hole": "#EF4444",    # red
    "JHMR": "#EF4444",            # red (same as Jackson Hole)
    "Palisades": "#EC4899",       # pink
    "Palisades Tahoe": "#EC4899", # pink
    "Mission Ridge": "#F97316",   # orange
    "Mt. Bachelor": "#14B8A6",    # teal
    "Bogus Basin": "#A855F7",     # purple
    "Snow King": "#F43F5E",       # rose
    "Schweitzer": "#6366F1",      # indigo
    "Brighton": "#0EA5E9",        # sky blue
    "Deer Valley": "#22D3EE",     # light cyan
    "Sundance": "#84CC16",        # lime
    "Mammoth Mtn.": "#D946EF",    # fuchsia
    "Utah Olympic Park": "#3B82F6",  # blue-500
    "Tamarack": "#059669",        # green
    "Sugarbowl": "#FB923C",       # light orange
    "Rotarun": "#A78BFA",         # light violet
    "Big Sky": "#38BDF8",         # light blue
}


class MonthlyCalendarTemplate(BaseTemplate):
    """Visual monthly calendar grid with venue-colored event bars."""

    def draw_header(self) -> int:
        """Draw header: logo + tagline left-aligned, 'Youth Ski Race Calendar' right-aligned."""
        y = self.margin

        # Logo sizing
        if self.fmt == "facebook":
            logo_max_w = int(self.width * 0.15)
            logo_max_h = 36
        elif self.fmt == "post":
            logo_max_w = int(self.width * 0.22)
            logo_max_h = 48
        else:  # story, reel
            logo_max_w = int(self.width * 0.25)
            logo_max_h = 56

        # Logo left-aligned
        logo_w, logo_h = composite_logo(
            self.canvas, self.margin, y, logo_max_w, logo_max_h
        )

        # Tagline below logo, left-aligned
        tagline_size = self._scale_font(14 if self.fmt == "facebook" else 18)
        tagline_font = load_font("Bold", tagline_size)
        tagline_text = "INDOOR SKI + GOLF"
        tagline_y = y + logo_h + 6
        draw_text(self.draw, tagline_text, self.margin, tagline_y, tagline_font, COLOR_WHITE)
        tagline_bbox = tagline_font.getbbox(tagline_text)
        left_bottom = tagline_y + (tagline_bbox[3] - tagline_bbox[1])

        # "Youth Ski Race Calendar" right-aligned, vertically centered with logo block
        cal_title_size = self._scale_font(18 if self.fmt == "facebook" else 24)
        cal_title_font = load_font("Bold", cal_title_size)
        cal_title_text = "Youth Ski Race Calendar"
        cal_bbox = cal_title_font.getbbox(cal_title_text)
        cal_w = cal_bbox[2] - cal_bbox[0]
        cal_h = cal_bbox[3] - cal_bbox[1]
        cal_x = self.margin + self.content_width - cal_w
        # Vertically center within the logo+tagline block
        block_h = left_bottom - y
        cal_y = y + (block_h - cal_h) // 2
        draw_text(self.draw, cal_title_text, cal_x, cal_y, cal_title_font, COLOR_PRIMARY)

        y = left_bottom + 12

        # Blue accent line
        draw_accent_line(self.draw, self.margin, y, self.content_width)
        y += 20
        return y

    def render(self, events: list[dict], year: int, month: int) -> Image.Image:
        consts = _FORMAT_CONSTANTS[self.fmt]
        self._consts = consts

        # Draw header
        y = self.draw_header()

        # Month title
        title_font = load_font("Bold", self._scale_font(consts["title_font"]))
        month_name = calendar.month_name[month].upper()
        title_text = f"{month_name} {year}"
        title_bbox = title_font.getbbox(title_text)
        title_w = title_bbox[2] - title_bbox[0]
        title_x = (self.width - title_w) // 2
        draw_text(self.draw, title_text, title_x, y, title_font, COLOR_WHITE)
        y += (title_bbox[3] - title_bbox[1]) + 12

        # Accent line below title
        draw_accent_line(self.draw, self.margin, y, self.content_width)
        y += 18

        # Build calendar data
        weeks = self._build_calendar_grid(year, month)
        month_events = self._filter_month_events(events, year, month)
        events_with_lanes = self._allocate_lanes(month_events, weeks, year, month)

        # Draw the grid
        y = self._draw_grid(y, weeks, events_with_lanes, consts)

        # Color key legend
        y = self._draw_legend(y, month_events, consts)

        # Footer
        self.draw_footer_section()
        return self.canvas

    def _filter_month_events(
        self, events: list[dict], year: int, month: int
    ) -> list[dict]:
        """Filter to events whose date range overlaps the target month."""
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)
        # month_end is exclusive (first day of next month)

        filtered = []
        for event in events:
            dates = event.get("dates", {})
            start_str = dates.get("start", "")
            end_str = dates.get("end", "")
            if not start_str or not end_str:
                continue
            try:
                ev_start = date.fromisoformat(start_str)
                ev_end = date.fromisoformat(end_str)
            except ValueError:
                continue
            # Overlaps if event starts before month ends AND event ends on/after month start
            if ev_start < month_end and ev_end >= month_start:
                filtered.append(event)
        return filtered

    def _build_calendar_grid(
        self, year: int, month: int
    ) -> list[list[int | None]]:
        """Build list of week rows, each containing 7 day slots (day number or None)."""
        cal = calendar.Calendar(firstweekday=0)  # Monday first
        weeks = []
        current_week = []
        for day in cal.itermonthdays(year, month):
            current_week.append(day if day != 0 else None)
            if len(current_week) == 7:
                weeks.append(current_week)
                current_week = []
        if current_week:
            # Pad to 7 days
            while len(current_week) < 7:
                current_week.append(None)
            weeks.append(current_week)
        return weeks

    def _allocate_lanes(
        self,
        events: list[dict],
        weeks: list[list[int | None]],
        year: int,
        month: int,
    ) -> list[dict]:
        """Assign each event a lane within each week row it spans.

        Returns a list of segment dicts:
        {
            "event": original event dict,
            "week_idx": week row index,
            "start_col": start column (0-6),
            "end_col": end column (0-6),
            "lane": lane number (0-based),
            "color": hex color for the bar,
            "label": display label,
        }
        """
        max_lanes = self._consts["max_lanes"]
        segments = []

        for event in events:
            dates = event.get("dates", {})
            ev_start = date.fromisoformat(dates["start"])
            ev_end = date.fromisoformat(dates["end"])
            venue = event.get("venue", "")
            color = VENUE_COLORS.get(venue, COLOR_PRIMARY)

            # Build a short label
            label = self._short_label(event)

            for week_idx, week in enumerate(weeks):
                # Find columns this event spans in this week
                start_col = None
                end_col = None
                for col, day in enumerate(week):
                    if day is None:
                        continue
                    cell_date = date(year, month, day)
                    if ev_start <= cell_date <= ev_end:
                        if start_col is None:
                            start_col = col
                        end_col = col

                if start_col is not None:
                    segments.append({
                        "event": event,
                        "week_idx": week_idx,
                        "start_col": start_col,
                        "end_col": end_col,
                        "lane": -1,  # assigned below
                        "color": color,
                        "label": label,
                    })

        # Assign lanes per week row
        for week_idx in range(len(weeks)):
            week_segs = [s for s in segments if s["week_idx"] == week_idx]
            # Sort by start column, then by span width (wider first)
            week_segs.sort(key=lambda s: (s["start_col"], -(s["end_col"] - s["start_col"])))
            # Track which columns are occupied per lane
            lane_occupancy: list[list[bool]] = []  # lane -> [col occupied]
            for seg in week_segs:
                placed = False
                for lane_idx in range(max_lanes):
                    if lane_idx >= len(lane_occupancy):
                        lane_occupancy.append([False] * 7)
                    # Check if this lane has room
                    conflict = False
                    for col in range(seg["start_col"], seg["end_col"] + 1):
                        if lane_occupancy[lane_idx][col]:
                            conflict = True
                            break
                    if not conflict:
                        # Place in this lane
                        for col in range(seg["start_col"], seg["end_col"] + 1):
                            lane_occupancy[lane_idx][col] = True
                        seg["lane"] = lane_idx
                        placed = True
                        break
                if not placed:
                    # Overflow — place in last lane (may overlap)
                    seg["lane"] = max_lanes - 1

        return segments

    def _short_label(self, event: dict) -> str:
        """Create a short label for event bars."""
        disciplines = event.get("disciplines", [])
        venue = event.get("venue", "")
        age_groups = event.get("age_groups", [])
        disc_str = "/".join(disciplines) if disciplines else ""
        age_str = " ".join(age_groups) if age_groups else ""

        parts = []
        if disc_str:
            parts.append(disc_str)
        if venue:
            parts.append(venue)
        if age_str:
            parts.append(age_str)

        if parts:
            return " ".join(parts)
        # Fallback: use event name (strip venue suffix if present)
        name = event.get("name", "Event")
        return name[:30]

    def _draw_grid(
        self,
        y_start: int,
        weeks: list[list[int | None]],
        segments: list[dict],
        consts: dict,
    ) -> int:
        """Draw day-of-week headers, cells, day numbers, and event bars."""
        cell_gap = consts["cell_gap"]
        bar_height = consts["bar_height"]
        max_lanes = consts["max_lanes"]
        dow_font_size = self._scale_font(consts["dow_header_font"])
        day_font_size = self._scale_font(consts["day_num_font"])
        bar_font_size = self._scale_font(consts["bar_label_font"])

        dow_font = load_font("Bold", dow_font_size)
        day_font = load_font("Regular", day_font_size)
        bar_font = load_font("Regular", bar_font_size)

        grid_left = self.margin
        grid_width = self.content_width
        col_width = grid_width // 7

        y = y_start

        # Day-of-week headers
        for col, dow in enumerate(_DOW_HEADERS):
            x = grid_left + col * col_width
            bbox = dow_font.getbbox(dow)
            text_w = bbox[2] - bbox[0]
            text_x = x + (col_width - text_w) // 2
            draw_text(self.draw, dow, text_x, y, dow_font, COLOR_MUTED)

        dow_bbox = dow_font.getbbox("MON")
        y += (dow_bbox[3] - dow_bbox[1]) + 8

        # Calculate row height: day number + lanes area + padding
        day_num_h = day_font.getbbox("31")[3] - day_font.getbbox("31")[1]
        row_content_h = day_num_h + 4 + max_lanes * (bar_height + 2)
        row_height = row_content_h + cell_gap * 2

        # Reserve space for footer
        footer_reserved = 70
        available = self.height - y - footer_reserved
        # If rows don't fit, shrink row height
        total_needed = len(weeks) * row_height
        if total_needed > available and len(weeks) > 0:
            row_height = available // len(weeks)
            row_content_h = row_height - cell_gap * 2
            # Recalculate bar height to fit
            bar_area = row_content_h - day_num_h - 4
            bar_height = max(10, (bar_area // max_lanes) - 2)

        grid_line_rgb = hex_to_rgb(_GRID_LINE_COLOR)
        cell_bg_rgb = hex_to_rgb(_CELL_BG_COLOR)

        for week_idx, week in enumerate(weeks):
            row_y = y + week_idx * row_height

            # Draw cell backgrounds and day numbers
            for col, day in enumerate(week):
                cell_x = grid_left + col * col_width
                cell_y = row_y
                cell_w = col_width - cell_gap
                cell_h = row_height - cell_gap

                # Cell background
                self.draw.rectangle(
                    [cell_x, cell_y, cell_x + cell_w, cell_y + cell_h],
                    fill=cell_bg_rgb,
                )

                if day is not None:
                    # Day number in top-right of cell
                    day_str = str(day)
                    day_bbox = day_font.getbbox(day_str)
                    day_text_w = day_bbox[2] - day_bbox[0]
                    day_x = cell_x + cell_w - day_text_w - 4
                    day_y = cell_y + 3
                    draw_text(
                        self.draw, day_str, day_x, day_y,
                        day_font, COLOR_MUTED,
                    )

            # Draw grid lines between rows
            line_y = row_y + row_height - cell_gap
            self.draw.line(
                [(grid_left, line_y), (grid_left + grid_width, line_y)],
                fill=grid_line_rgb,
                width=1,
            )

            # Draw event bars for this week
            week_segments = [s for s in segments if s["week_idx"] == week_idx]
            bar_area_y = row_y + day_num_h + 6  # below day numbers

            for seg in week_segments:
                lane = seg["lane"]
                bar_y = bar_area_y + lane * (bar_height + 2)

                # Ensure bar stays within row
                if bar_y + bar_height > row_y + row_height - cell_gap:
                    continue

                bar_x = grid_left + seg["start_col"] * col_width + 2
                bar_w = (seg["end_col"] - seg["start_col"] + 1) * col_width - 4
                bar_color = hex_to_rgb(seg["color"])

                # Draw rounded rect bar
                self.draw.rounded_rectangle(
                    [bar_x, bar_y, bar_x + bar_w, bar_y + bar_height],
                    radius=4,
                    fill=bar_color,
                )

                # Label inside bar
                label = self._abbreviate_name(
                    seg["label"], bar_w - 8, bar_font
                )
                if label:
                    label_y = bar_y + (bar_height - bar_font_size) // 2
                    draw_text(
                        self.draw, label, bar_x + 4, label_y,
                        bar_font, COLOR_WHITE,
                    )

        y += len(weeks) * row_height
        return y

    def _draw_legend(
        self, y_start: int, month_events: list[dict], consts: dict
    ) -> int:
        """Draw a color key legend showing venue colors used this month."""
        # Collect unique venues in display order (order of first appearance)
        seen = {}
        for event in month_events:
            venue = event.get("venue", "")
            if venue and venue not in seen:
                seen[venue] = VENUE_COLORS.get(venue, COLOR_PRIMARY)
        if not seen:
            return y_start

        label_font_size = self._scale_font(consts["bar_label_font"])
        label_font = load_font("Regular", label_font_size)
        swatch_size = label_font_size + 2
        item_gap = 12
        row_gap = 6
        y = y_start + 12

        # Lay out items in rows that fit within content_width
        x = self.margin
        row_height = swatch_size + row_gap

        for venue, color in seen.items():
            bbox = label_font.getbbox(venue)
            text_w = bbox[2] - bbox[0]
            item_w = swatch_size + 5 + text_w + item_gap

            # Wrap to next row if needed
            if x + item_w - item_gap > self.margin + self.content_width and x > self.margin:
                x = self.margin
                y += row_height

            # Draw color swatch
            self.draw.rounded_rectangle(
                [x, y, x + swatch_size, y + swatch_size],
                radius=3,
                fill=hex_to_rgb(color),
            )
            # Draw venue label
            draw_text(
                self.draw, venue, x + swatch_size + 5,
                y + (swatch_size - label_font_size) // 2,
                label_font, COLOR_MUTED,
            )
            x += item_w

        y += row_height
        return y

    def _abbreviate_name(
        self, name: str, max_width: int, font
    ) -> str:
        """Truncate event name to fit within max_width pixels, adding '...' if needed."""
        if max_width <= 0:
            return ""
        bbox = font.getbbox(name)
        if (bbox[2] - bbox[0]) <= max_width:
            return name
        # Truncate with ellipsis
        for end in range(len(name), 0, -1):
            truncated = name[:end] + "..."
            bbox = font.getbbox(truncated)
            if (bbox[2] - bbox[0]) <= max_width:
                return truncated
        return ""
