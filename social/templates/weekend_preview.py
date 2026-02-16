"""Weekend preview 'THIS WEEKEND IN YOUTH SKI RACING' template."""

from social.templates.weekly_preview import WeeklyPreviewTemplate


class WeekendPreviewTemplate(WeeklyPreviewTemplate):
    """'THIS WEEKEND IN YOUTH SKI RACING' — Fri-Sun events, all races."""

    TITLE_LINE_1 = "THIS WEEKEND IN"
    TITLE_LINE_2 = "PC SKI RACING"
    MAX_EVENTS = 3
