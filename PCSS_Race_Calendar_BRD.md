# Business Requirements Document
## PCSS Ski Race Calendar — sim.sports

**Author:** sim.sports team
**Date:** February 8, 2026
**Status:** Draft — for Claude Code handoff

---

## 1. Executive Summary

sim.sports needs an interactive ski race calendar focused on Park City Ski & Snowboard (PCSS) youth athletes. The calendar serves as a content engine for blog posts and social media, complementing an existing automated race blog system. It will be the go-to place for PCSS families, fans, and the sim.sports audience to see what's coming up and what just happened.

---

## 2. Business Context

### 2.1 What sim.sports already has
- **Website on Wix** (sim.sports) — used for scheduling, invoicing, email marketing, social posts
- **Automated PCSS race monitor** (`automated_pcss_monitor.py`) — scrapes imdalpine.org/race-results/ for PDFs mentioning PCSS athletes, sends email alerts
- **Existing youth ski racing blog engine** — already produces post-race results and recaps
- **Race data sources:** IMD Alpine (imdalpine.org), USSA/FIS event databases, live timing pages

### 2.2 What this project adds
A forward-looking race calendar + social media content generator that sits alongside the existing blog engine. The blog handles *what happened*; the calendar handles *what's coming* and helps promote it.

---

## 3. Scope

### 3.1 In scope
- All races where PCSS athletes compete (IMD, USSA, FIS — any circuit)
- Interactive web-based calendar (embeddable on Wix)
- Automated social media image generation
- Pre-race preview content for blog/social
- Links or references back to existing post-race blog recaps

### 3.2 Out of scope (for now)
- Replacing the existing blog engine or race monitor
- Non-PCSS race coverage
- E-commerce or paid subscription features
- Mobile app (web-responsive is sufficient)

---

## 4. Data Sources & Ingestion

### 4.1 Research findings (completed Feb 2026)

**PCSS does NOT publish a standalone race calendar.** Their events page (parkcityss.org/events) is essentially empty — just sponsor logos. Individual program pages (Jr IMC, South Series, etc.) have "Loading schedule..." widgets that defer to IMD: "Race dates can be confirmed through IMD and US Ski & Snowboard."

**IMD Alpine (imdalpine.org) is the primary and best source.** Their /events/ page has a full, structured calendar with all upcoming races. Even better, they publish iCal/Google Calendar subscription feeds.

### 4.2 Confirmed data sources

| Source | URL | Data available | Method | Priority |
|--------|-----|----------------|--------|----------|
| IMD Alpine Calendar | imdalpine.org/events/ | Full upcoming race schedule with dates, venues, disciplines, TDs, race announcements (PDFs) | **iCal feed** (preferred) or HTML scrape | **PRIMARY** |
| IMD iCal Feed | `webcal://imdalpine.org/?post_type=tribe_events&ical=1&eventDisplay=list` | Structured calendar data — subscribable, parseable | iCal consumption | **PRIMARY** |
| IMD Race Results | imdalpine.org/race-results/ | Post-race PDFs with results | Scraping (existing script already does this) | Secondary |
| USSA/US Ski & Snowboard | usskiandsnowboard.org | National-level events (U16 Nationals, Western Region Champs, etc.) | Scraping or calendar feed | **PRIMARY — include from day one** |
| AdminSkiRacing | adminskiracing.com | Registration portal — race entries, start lists | Scraping if needed | Nice-to-have |

### 4.3 PCSS relevance filtering

Not every IMD race involves PCSS athletes. Two approaches (can use both):

**Approach A — Include all IMD races, highlight PCSS-relevant ones.** Most PCSS families want to see the full IMD picture. Flag races where PCSS athletes are entered (detectable from start lists or post-race results using existing regex: `\bPCSS\b`, `\bPark City\b`, `\bPark City SS\b`, `\bPark City Ski\b`).

**Approach B — Curate PCSS-only races.** Manually or semi-automatically tag which races PCSS athletes attend. More editorial control but requires ongoing maintenance.

**Recommendation:** Start with Approach A (all IMD races visible, PCSS auto-highlighted) and layer in manual curation over time.

### 4.4 Sample data from IMD calendar (current as of Feb 8, 2026)

The following races are currently listed on imdalpine.org/events/ — this confirms the data is rich and scrapable:

| Date | Event | Discipline | Venue |
|------|-------|-----------|-------|
| Feb 9–10 | South Series GS | GS | Snowbird |
| Feb 14–15 | YSL Kombi | Kombi | Utah Olympic Park |
| Feb 17–20 | WR Elite (Bryce Astle Memorial) | SL/GS | Snowbird / UOP |
| Feb 19–24 | U16 Laura Flood Qualifier | SL/GS/SG | Sun Valley |
| Feb 25–26 | South Series SL/GS | SL/GS | Sundance |
| Feb 27–Mar 1 | U14 David Wright Qualifier | SL/GS | Park City |
| Mar 7–8 | YSL Finals | SL/GS | Snowbasin |
| Mar 12–15 | WR U16 Regionals | SL/GS/SG | Palisades |
| Mar 14–15 | IMD Finals | SL/GS | Park City |
| Mar 20–22 | IMD Champs | SL/GS/PS | Jackson Hole |
| Mar 28–Apr 1 | USSS U16 Nationals | TBD | Snowking |
| Apr 3–5 | U12/U14 Spring Fling | SL/GS/K | Grand Targhee |
| Apr 4–7 | IMC SnowCup | SL/GS | Snowbird |

Each event also links to a Race Announcement PDF with detailed schedules, entry fees, and logistics.

### 4.5 Data model (per race event)
- Race name
- Date(s) — single day or multi-day
- Location / venue
- Discipline(s) — SL, GS, SG, DH, combined, etc.
- Circuit — IMD, USSA, FIS, club race, etc.
- Age groups / categories
- Status — upcoming, in-progress, completed
- Results link (to existing blog or external source)
- Source URL (where data was scraped from)

---

## 5. Functional Requirements

### 5.1 Interactive Web Calendar

**Primary view:** Forward-looking calendar showing upcoming PCSS races

**Core features:**
- Month/week/list view toggle
- Filter by discipline (SL, GS, SG, DH, etc.)
- Filter by circuit (IMD, USSA, FIS, club)
- Click into any event for detail view (date, location, discipline, preview content)
- Past events show "View Recap" link back to existing blog posts
- Mobile-responsive design
- Embeddable on Wix via iframe or embed code

**Nice to have (Phase 2):**
- Countdown to next race
- "Add to my calendar" (Google Cal / Apple Cal / .ics export)
- Notification sign-up for race day alerts

### 5.2 Social Media Image Generation

Auto-generate branded graphics for each race event. Priority order:

| Priority | Format | Dimensions | Use |
|----------|--------|------------|-----|
| 1 | Instagram Reel / TikTok | 1080×1920 (9:16) | Short-form video covers, story posts |
| 2 | Instagram Post | 1080×1080 (1:1) | Feed posts |
| 3 | Instagram Story | 1080×1920 (9:16) | Story announcements |
| 4 | Facebook | 1200×630 | Facebook feed posts |

**Image types to generate per event:**
- **Pre-race announcement** — "PCSS races this weekend" with date, location, discipline
- **Race day** — "Race day! [Event name] at [Location]" 
- **Weekly preview** — consolidated "This week in PCSS racing" graphic
- **Monthly calendar** — visual month view of all upcoming races

**Brand requirements:**
- sim.sports logo/branding (need logo file or brand guidelines from user)
- Consistent color palette, typography
- Clean, sporty, professional aesthetic
- Space for optional custom text overlay

### 5.3 Blog-Ready Content

For each upcoming race, generate a short preview blurb suitable for:
- Blog post intros
- Email newsletter snippets
- Social media captions

Content should include: event name, date, location, discipline, and any relevant context (e.g., "Last time at Snowbasin, PCSS had 3 podium finishes").

---

## 6. Technical Architecture (Recommended)

### 6.1 Stack recommendation
- **Backend:** Python (aligns with existing scripts)
- **Data store:** JSON files or SQLite (lightweight, no server needed to start)
- **Calendar frontend:** HTML/CSS/JS (static site, embeddable)
- **Image generation:** Python (Pillow) or HTML-to-image (Puppeteer)
- **Hosting:** GitHub Pages, Vercel, or Netlify for the calendar frontend
- **Integration:** Wix embed via iframe

### 6.2 Integration with existing systems
- Extend `automated_pcss_monitor.py` or build companion script
- Share `seen_races_cache.json` data model or build unified race database
- Link completed races to existing blog posts by matching race name/date

### 6.3 Automation flow
```
[IMD iCal Feed]  ←  webcal://imdalpine.org/...
       ↓
 [iCal Parser]   ←  Python (icalendar lib)
       ↓
[Race Database]  ←  JSON/SQLite with all race data
       ↓
 [PCSS Tagger]   ←  word-boundary regex (from existing monitor)
       ↓
   ┌────┴────┐
   ↓         ↓
[Calendar]  [Image Generator]
   ↓         ↓
 [Wix]    [Social posts]
   ↓
[Existing Blog Engine]  ←  match via sim.sports/post/[slug] (venue + date in slug)
```

**Also feeds from:**
- IMD race-results/ PDFs (existing `automated_pcss_monitor.py`)
- USSA event pages (supplementary, for nationals/regionals)

---

## 7. Phasing

### Phase 0 — Discovery & Data ✅ COMPLETE
- ✅ Researched all available PCSS schedule sources (parkcityss.org has no usable calendar)
- ✅ Identified IMD Alpine (imdalpine.org/events/) as primary source with iCal feed
- ✅ Confirmed 25 upcoming events on IMD calendar through April 2026
- ✅ Documented data sources and recommended ingestion approach (see Section 4)
- **Remaining:** Set up race database schema, test iCal feed parsing

### Phase 1 — Data Ingestion & Database (Week 1)
- Parse IMD iCal feed (`webcal://imdalpine.org/?post_type=tribe_events&ical=1&eventDisplay=list`)
- Build race database (JSON/SQLite) from iCal data
- Implement PCSS relevance tagging (word-boundary regex from existing monitor)
- Set up cron job to refresh calendar data daily
- Integrate with existing `seen_races_cache.json` to avoid duplication

### Phase 2 — Calendar MVP (Weeks 2–3)
- Build interactive web calendar with upcoming races
- Month/list views, discipline filters
- Responsive design, Wix-embeddable
- Manual data entry fallback if scraping isn't complete

### Phase 3 — Social Image Generation (Weeks 3–4)
- Branded image templates for all 4 formats
- Auto-generate per-event and weekly preview graphics
- Output to folder for easy posting

### Phase 4 — Automation & Integration (Weeks 4–6)
- Automated scraping of upcoming race schedules
- Link past races to existing blog recaps
- Preview content generation
- Cron job integration alongside existing monitor

### Phase 5 — Polish & Expand (Ongoing)
- Add-to-calendar functionality
- Race day alerts
- Historical season archive
- Analytics on calendar engagement

---

## 8. Open Questions — RESOLVED

1. ~~**PCSS official calendar**~~ — ✅ PCSS does not publish a usable race calendar. IMD Alpine is the source of truth.
2. ~~**sim.sports brand assets**~~ — ✅ Brand assets available. Owner will share logo files, color palette, fonts. Claude Code should prompt for upload if not provided.
3. ~~**Wix embed support**~~ — ⚠️ Unknown. Claude Code should build the calendar as a standalone web app that works on its own AND can be embedded via iframe. Test Wix embed capability during Phase 2.
4. ~~**Blog integration**~~ — ✅ Wix blog URLs follow the pattern `https://sim.sports/post/[slug]` where the slug is based on the post title. Posts are tagged with categories. Claude Code can match race recaps by searching slugs for venue names, dates, or race series names (e.g., `snowbird-gs-recap`, `imd-finals-results`).
5. ~~**Hosting preference**~~ — ✅ No preference — Claude Code should pick the simplest option that works (Vercel or GitHub Pages recommended).
6. ~~**Race age groups**~~ — ✅ All age groups: U10 through U21+. Calendar should include filterable age group tags.
7. **iCal feed scope** — ⚠️ Still needs testing. Claude Code should parse the IMD iCal feed early in Phase 1 and report back on what fields are available (venue, discipline, age group, etc.) vs. what needs to be supplemented from HTML scraping or Race Announcement PDFs.
8. ~~**Non-IMD races**~~ — ✅ Include USSA nationals and Western Region events from the start. These are important for PCSS athletes who qualify for higher-level competition.

---

## 9. Success Criteria

- PCSS families can see all upcoming races in one place
- sim.sports can generate social content for every race week in under 5 minutes
- Calendar stays current with minimal manual intervention
- Content drives traffic to sim.sports website and blog
- Professional, branded look across all outputs

---

## 10. Claude Code Kickoff Instructions

When handing this to Claude Code, start with:

> "Read this BRD. Phase 0 (data discovery) is complete and all open questions except #7 are resolved — see Sections 4 and 8. Start with Phase 1: parse the IMD iCal feed, also identify USSA national/regional events for PCSS-relevant age groups (U10–U21+), build the race database, and test PCSS relevance tagging. Then build the calendar MVP as a standalone web app (host on Vercel or GitHub Pages) that can also be embedded via iframe on Wix. Ask me to upload sim.sports brand assets before starting Phase 3 (social images)."

**Key technical starting points:**
- IMD iCal feed URL: `webcal://imdalpine.org/?post_type=tribe_events&ical=1&eventDisplay=list`
- IMD events page (HTML fallback): `https://imdalpine.org/events/`
- Existing PCSS monitor script: `~/Downloads/automated_pcss_monitor.py`
- Existing cache: `~/Downloads/seen_races_cache.json`
- PCSS regex patterns: `\bPCSS\b`, `\bPark City\b`, `\bPark City SS\b`, `\bPark City Ski\b`
- Blog URL pattern: `https://sim.sports/post/[slug]` — match by venue/date/series name in slug
- Age groups: All (U10 through U21+)
- Hosting: Vercel or GitHub Pages (whatever is simplest)
- Brand assets: Owner will provide logo, colors, fonts before social image phase

---

*Document prepared for sim.sports / Claude Code handoff — February 2026*
