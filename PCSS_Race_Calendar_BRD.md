# PCSS Race Calendar - Business Requirements Document

**Project:** Youth Ski Race Calendar (sim.sports)
**URL:** https://race-calendar-ten.vercel.app
**Date:** February 21, 2026
**Status:** Production

---

## 1. Overview

An interactive youth alpine ski race calendar aggregating events from IMD (Intermountain Division), Western Region, USSA, and FIS sources. Built for Park City Ski & Snowboard (PCSS) families, it provides race schedules, racer/club search, blog recaps, calendar subscriptions, and automated social media content.

**Tech stack:** Vanilla JavaScript frontend, Python ingestion pipeline, Vercel hosting. No frameworks, no database — JSON files only.

---

## 2. Data Pipeline

### 2.1 Sources

| Source | Method | File |
|--------|--------|------|
| IMD iCal feed | `ical_parser.py` | `imdalpine.org` iCal endpoint |
| USSA/FIS events | `ussa_seeds.py` | `data/ussa_manual_events.json` (manual) |
| Race result PDFs | `pcss_detector.py`, `name_extractor.py` | `imdalpine.org/race-results/` scrape |
| Blog recaps | `blog_linker.py` | `simsportsarena.com/blog-feed.xml` RSS |

### 2.2 Enrichment

Each event is enriched with:

- **Disciplines:** Parsed from event name via regex (SL, GS, SG, DH, PS, K, AC) with counts (e.g., "2 SL")
- **Circuit:** Mapped from category keywords (IMD, Western Region, USSA, FIS)
- **Age groups:** Extracted from U-codes (U10-U21) and keywords (YSL -> U10/U12, IMC -> U14/U16, Devo -> U16/U18/U21)
- **Venue & state:** 40+ known venues mapped to UT, ID, WY, CA, WA, OR, MT
- **Status:** Computed from dates (upcoming, in_progress, completed, canceled)
- **PCSS confirmed:** Set `true` when result PDFs contain "PCSS" or "Park City" patterns
- **Blog recaps:** Auto-linked by matching venue + date within 14-day lookback
- **Racer names & clubs:** Parsed from result PDFs ("Lastname, Firstname YYYY CLUB COUNTRY" format)

### 2.3 Outputs

| Output | Path | Description |
|--------|------|-------------|
| Race database | `data/race_database.json` -> `site/data/` | All events with full metadata |
| Racer database | `data/racer_database.json` -> `site/data/` | 1,120 racers with club codes and event_ids |
| ICS feed | `site/pcss-calendar.ics` | Subscribable calendar (RFC 5545) |
| Caches | `data/pcss_results_cache.json`, `data/racer_names_cache.json` | Avoid re-downloading PDFs |

### 2.4 Running

```bash
npm run refresh    # Full pipeline: fetch, enrich, write JSON, copy to site/
npm run dev        # Refresh + start local server on port 3000
```

### 2.5 Event Data Schema

```json
{
  "id": "imd-14398",
  "name": "South Series- 2 GS- Snowbird",
  "dates": { "start": "2026-02-09", "end": "2026-02-10", "display": "Feb 9-10, 2026" },
  "venue": "Snowbird",
  "state": "UT",
  "disciplines": ["GS"],
  "discipline_counts": { "GS": 2 },
  "circuit": "IMD",
  "series": "South Series",
  "age_groups": ["U10", "U12", "U14"],
  "status": "completed",
  "pcss_relevant": true,
  "pcss_confirmed": true,
  "td_name": "John Doe",
  "description": "Girls run 1, Boys run 2",
  "source_url": "https://imdalpine.org/event/...",
  "blog_recap_urls": [{ "date": "2026-02-12", "title": "...", "url": "..." }],
  "results_url": null
}
```

### 2.6 Racer Data Schema

```json
{
  "name": "Feren Johnson",
  "key": "feren johnson",
  "club": "PCSS",
  "event_ids": ["imd-14398", "imd-14421"]
}
```

---

## 3. Frontend Features

### 3.1 Month View

Traditional 7-column calendar grid with month navigation and "Today" button.

- Multi-day events span columns with visual continuity arrows across week breaks
- Color-coded by primary discipline (SL=blue, GS=red, SG=orange, DH=purple, PS=green, K=amber)
- Urgency glow: green (race day), orange (tomorrow), blue (this week), gray (next week)
- PCSS confirmed events get pink accent border
- Events with blog recaps get purple dot indicator
- Canceled events show strikethrough + reduced opacity
- Smart lane allocation prevents visual overlap (greedy row-packing algorithm)
- Click any event to open detail modal

### 3.2 List View

Chronological card list grouped by month headers. Each card shows:

- Large date column (month abbreviation + day number)
- Event name, venue, state
- Countdown text ("Starts in 3 days", "Race day!", "Ended 2 days ago")
- Badge row: urgency, disciplines, circuit, age groups, PCSS, recap, canceled
- Auto-scrolls to current date on view switch

### 3.3 Filter System

Chip-based filters in a sticky bar below the header:

| Filter | Options | Behavior |
|--------|---------|----------|
| Disciplines | SL, GS, SG, DH, PS, K | Multi-select, OR within group |
| Circuits | IMD, WR, USSA, FIS | Multi-select, OR within group |
| Age groups | U10-U21 | Multi-select, OR within group |
| PCSS | Toggle | Show only PCSS-confirmed events |
| Upcoming only | Toggle | Hide completed events (default in embed mode) |

Filters across groups combine with AND logic. "Clear filters" link resets all. All filter state reflected in URL params.

### 3.4 Racer & Club Search

Autocomplete search input in the filters bar:

- Lazy-loads racer database on first keystroke (2-char minimum)
- **Name search:** Type racer name, see matches with club badge + event count
- **Club search:** Type club code (e.g., "PCSS"), see "Club: PCSS (N racers)" option that filters to all events where any member competed
- Keyboard navigation (arrow keys, Enter, Escape)
- Deep-linkable: `?racer=john+smith` or `?racer=club:pcss`

### 3.5 Event Detail Modal

Click any event to see:

1. **Venue photo** (24 venues have photos in `site/assets/venues/`)
2. **Status badges** (upcoming/in-progress/completed/canceled, urgency, PCSS)
3. **Event name**
4. **Metadata grid:** dates + countdown, venue/state, disciplines with counts, circuit + series, age groups, TD name
5. **Description** (scheduling notes like "Girls run 1, Boys run 2")
6. **Action buttons:**
   - "View on IMD" -> source URL
   - "Recap: [Title]" -> blog post (multiple supported)
   - "View Results" -> results URL
   - "Google Cal" -> pre-filled Google Calendar event
   - "Download .ics" -> client-side RFC 5545 file

### 3.6 Calendar Subscription

"Subscribe" button in header opens modal with three options:

1. **Google Calendar:** `calendar.google.com/calendar/r?cid={feed_url}`
2. **Apple Calendar / Outlook:** `webcal:` protocol handler
3. **Copy Feed URL:** Clipboard copy for manual paste

The `.ics` feed includes all events, canceled events marked `STATUS:CANCELLED`, 1-day-before reminders, 12-hour refresh interval.

### 3.7 Embed Mode

`?embed=true` hides the header, defaults to upcoming-only, serves with CORS + iframe-friendly headers. Designed for embedding on the Wix site.

### 3.8 URL Parameters

| Param | Example | Effect |
|-------|---------|--------|
| `view` | `?view=list` | Month or list view |
| `discipline` | `?discipline=SL,GS` | Pre-filter disciplines |
| `circuit` | `?circuit=IMD` | Pre-filter circuit |
| `age` | `?age=U14,U16` | Pre-filter age groups |
| `pcss` | `?pcss=true` | PCSS-only filter |
| `past` | `?past=true` | Show past events |
| `racer` | `?racer=john+smith` | Filter to racer's events |
| `racer` | `?racer=club:pcss` | Filter to club's events |
| `embed` | `?embed=true` | Embed mode |

---

## 4. Social Media System

### 4.1 Image Generation

CLI tool (`social/generate.py`) produces branded graphics using Pillow:

| Template | Content | Use Case |
|----------|---------|----------|
| Pre-race | Event name, venue, dates, disciplines | Post 1-2 days before event |
| Race day | "It's race day!" with event details | Post morning of event |
| Weekend preview | All events happening Fri-Sun | Post Thursday evening |
| Weekly preview | PCSS events for the week | Post Monday morning |
| Monthly calendar | Visual calendar grid with events | Post start of month |

Each template generates 4 formats: post (1080x1080), story (1080x1920), reel (1080x1920), facebook (1200x630). Venue photos included when available.

### 4.2 Caption Generation

Auto-generated captions (`social/captions.py`) with platform-specific formatting:

- **Instagram:** Includes hashtags (#IMDAlpine, #YouthSkiRacing, #PCSkiRacing, #[Venue])
- **Facebook:** Conversational, no hashtags
- **Short:** One-liner for blog/email
- Smart historical context: auto-adds "Check out our recap from last time at [Venue]" when a prior blog post exists for that venue

### 4.3 Posting

Meta Graph API integration (`social/poster.py`) for Instagram + Facebook:

```bash
python3 -m social.generate                              # Generate images
python3 -m social.poster "Event Name" --dry-run         # Preview
python3 -m social.poster "Event Name"                   # Post to both platforms
```

Handles rate limiting, expired tokens, and two-step Instagram upload flow (upload to Facebook CDN, create container, poll until ready, publish).

---

## 5. Blog Integration

**Source:** `https://www.simsportsarena.com/blog-feed.xml` (RSS)

**Matching logic:**
1. Extract venue from blog post URL slug (e.g., `snowbird-south-series-recap` -> "Snowbird")
2. Find completed events where venue matches and event ended within 14 days before blog publication
3. Pick most recent matching event

**User-facing display:**
- Event modal shows "Recap: [Title]" action button(s)
- List view shows purple "RECAP" badge
- Month view shows purple dot indicator on event banner

---

## 6. Design System

**Brand font:** Montserrat (Google Fonts, 400/500/600/700)
**Primary color:** #1190CB (Sim.Sports blue)
**PCSS highlight:** #e94560 (pink)

| Element | Color Scheme |
|---------|-------------|
| Disciplines | SL=#2563eb, GS=#dc2626, SG=#ea580c, DH=#7c3aed, PS=#059669, K=#d97706 |
| Circuits | IMD=#475569, WR=#7c3aed, USSA=#dc2626, FIS=#2563eb |
| Urgency | Race day=#059669, Tomorrow=#d97706, This week=#2563eb, Next week=#64748b |
| Status | Upcoming=#2563eb, In progress=#059669, Completed=#64748b, Canceled=#dc2626 |

Mobile responsive with breakpoints at 768px and 480px. Month view collapses to discipline-badge-only on mobile. Modal slides up from bottom on mobile.

---

## 7. Infrastructure

| Component | Technology |
|-----------|-----------|
| Hosting | Vercel (static site, auto-deploy on push to main) |
| Frontend | Vanilla JS (ES6 modules), CSS custom properties |
| Backend | Python 3.9+ (requests, beautifulsoup4, pypdf, Pillow) |
| Data format | JSON files (no database) |
| Calendar feed | RFC 5545 .ics file |
| Social APIs | Meta Graph API (Instagram + Facebook) |
| Version control | Git, GitHub |

### Deployment

Push to `main` triggers Vercel auto-deploy. Data refresh is manual (`npm run refresh`) or can be automated via cron/GitHub Actions.

### Caching

PDF download results cached to avoid re-fetching on subsequent runs. Old cache entries without newer fields (e.g., `club`) gracefully default to `null` via `.get()`.

---

## 8. Current Metrics

| Metric | Value |
|--------|-------|
| Total events tracked | ~150 per season |
| Unique racers indexed | 1,120 |
| Clubs/teams identified | 30+ (PCSS, RM, SVSEF, JHSC, SB, BBSEF, etc.) |
| Venues mapped | 40+ |
| Venue photos | 24 |
| Social image templates | 5 types x 4 formats |
| Test coverage | 261 tests passing |

---

## 9. File Map

```
RaceCalendar/
├── site/                          # Static frontend (served by Vercel)
│   ├── index.html
│   ├── js/                        # app, filters, racer-search, calendar-month,
│   │                                calendar-list, event-modal, calendar-export,
│   │                                data-loader, date-utils, url-params
│   ├── css/                       # styles.css, variables.css
│   ├── assets/venues/             # 24 venue photos
│   ├── data/                      # race_database.json, racer_database.json
│   └── pcss-calendar.ics          # Subscribable feed
├── ingestion/                     # Python data pipeline
│   ├── refresh.py                 # Orchestrator
│   ├── config.py                  # Constants, patterns, venue maps
│   ├── ical_parser.py             # IMD feed parser
│   ├── pcss_detector.py           # Result PDF scraping, PCSS detection
│   ├── name_extractor.py          # Racer name + club extraction
│   ├── blog_linker.py             # RSS scraping, recap matching
│   ├── ics_feed.py                # .ics generation
│   ├── age_group_extractor.py     # Age group parsing
│   ├── circuit_mapper.py          # Circuit classification
│   └── summary_parser.py          # Event name parsing
├── social/                        # Social media tooling
│   ├── generate.py                # Image generation CLI
│   ├── poster.py                  # Meta Graph API posting
│   ├── captions.py                # Caption generation
│   └── templates/                 # pre_race, race_day, weekend, weekly, monthly
├── data/                          # Source data + caches
│   ├── race_database.json
│   ├── racer_database.json
│   ├── blog_links.json
│   ├── ussa_manual_events.json
│   └── *_cache.json
├── tests/                         # 261 tests
└── output/social/                 # Generated social images
```

---

## 10. Operational Workflows

### Weekly Content Cycle

1. **Monday:** Run `npm run refresh` to update data. Generate weekly preview images.
2. **Thursday:** Generate weekend preview images, post to Instagram/Facebook.
3. **Race mornings:** Generate race day images, post.
4. **Post-race:** Blog recap auto-links after publishing on simsportsarena.com.

### Admin Commands

```bash
npm run refresh                                    # Full data refresh
npm run dev                                        # Refresh + local server
python3 -m ingestion.name_extractor                # Re-extract racer names from PDFs
python3 -m social.generate                         # Generate all upcoming event images
python3 -m social.generate --type weekend_preview  # Weekend preview only
python3 -m social.poster "Event Name"              # Post to Instagram + Facebook
python3 -m social.poster "Event Name" --dry-run    # Preview without posting
python3 -m pytest tests/ -v                        # Run all tests
```
