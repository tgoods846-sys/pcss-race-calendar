"""Automated social posting scheduler.

Determines what to post each day based on the posting schedule:
- Monday: weekly preview (Mon-Sun)
- Thursday: weekend preview (Fri-Sun)
- Every day: pre-race for events starting in 2 days
- Every day: race-day for events starting today

Usage:
    python3 -m social.scheduler              # Preview what would post today
    python3 -m social.scheduler --execute    # Generate + post
    python3 -m social.scheduler --dry-run    # Generate + dry-run post
    python3 -m social.scheduler --date 2026-03-05  # Simulate a different date
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from social.config import DATA_DIR, OUTPUT_DIR
from social.generate import (
    generate_event_images,
    generate_weekly_images,
    generate_weekend_images,
    get_pre_race_events,
    get_race_day_events,
    get_weekly_events,
    get_weekend_events,
    load_events,
    _event_folder_name,
)
from social.poster import MetaPoster, detect_content_type

POSTING_LOG_PATH = DATA_DIR / "posting_log.json"


def load_posting_log() -> dict:
    """Read the posting log from disk."""
    if not POSTING_LOG_PATH.exists():
        return {"posts": []}
    with open(POSTING_LOG_PATH) as f:
        return json.load(f)


def save_posting_log(log: dict) -> None:
    """Write the posting log to disk."""
    with open(POSTING_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)
        f.write("\n")


def is_posted(log: dict, key: str) -> bool:
    """Check if a key exists in the posting log."""
    return any(entry["key"] == key for entry in log.get("posts", []))


def get_todays_tasks(events: list[dict], log: dict, ref_date: date | None = None) -> list[dict]:
    """Return list of task dicts based on day-of-week and event dates.

    Each task dict has: type, key, identifier, and relevant events/event data.
    """
    today = ref_date or date.today()
    tasks = []

    # Monday: weekly preview
    if today.weekday() == 0:  # Monday
        key = f"weekly_preview:{today.isoformat()}"
        if not is_posted(log, key):
            weekly = get_weekly_events(events)
            if weekly:
                tasks.append({
                    "type": "weekly_preview",
                    "key": key,
                    "identifier": today.isoformat(),
                    "events": weekly,
                })

    # Thursday: weekend preview
    if today.weekday() == 3:  # Thursday
        friday = today + timedelta(days=1)
        key = f"weekend_preview:{friday.isoformat()}"
        if not is_posted(log, key):
            weekend = get_weekend_events(events)
            if weekend:
                tasks.append({
                    "type": "weekend_preview",
                    "key": key,
                    "identifier": friday.isoformat(),
                    "events": weekend,
                })

    # Every day: pre-race (events starting in 2 days)
    pre_race = get_pre_race_events(events, days_ahead=2, ref_date=today)
    for event in pre_race:
        key = f"pre_race:{event['id']}"
        if not is_posted(log, key):
            tasks.append({
                "type": "pre_race",
                "key": key,
                "identifier": event["id"],
                "event": event,
            })

    # Every day: race day (events starting today)
    race_day = get_race_day_events(events, ref_date=today)
    for event in race_day:
        key = f"race_day:{event['id']}"
        if not is_posted(log, key):
            tasks.append({
                "type": "race_day",
                "key": key,
                "identifier": event["id"],
                "event": event,
            })

    return tasks


def execute_tasks(tasks: list[dict], all_events: list[dict], dry_run: bool = False) -> None:
    """Execute posting tasks: generate images, post, and log results."""
    if not tasks:
        print("No tasks to execute.")
        return

    # Build poster
    if dry_run:
        poster = MetaPoster(
            page_access_token="DRY_RUN",
            page_id="DRY_RUN",
            ig_user_id="DRY_RUN",
        )
    else:
        token = os.environ.get("META_PAGE_ACCESS_TOKEN")
        page_id = os.environ.get("META_PAGE_ID")
        ig_user_id = os.environ.get("META_IG_USER_ID")
        if not token or not page_id:
            print("Error: META_PAGE_ACCESS_TOKEN and META_PAGE_ID must be set")
            sys.exit(1)
        if not ig_user_id:
            print("Error: META_IG_USER_ID must be set")
            sys.exit(1)
        poster = MetaPoster(
            page_access_token=token,
            page_id=page_id,
            ig_user_id=ig_user_id,
        )

    log = load_posting_log()
    platforms = ["facebook", "instagram"]
    formats = ["post", "facebook"]

    for task in tasks:
        task_type = task["type"]
        print(f"\n--- {task_type}: {task['identifier']} ---")

        try:
            # Generate images
            if task_type == "weekly_preview":
                outputs = generate_weekly_images(task["events"], formats)
            elif task_type == "weekend_preview":
                outputs = generate_weekend_images(task["events"], formats)
            elif task_type in ("pre_race", "race_day"):
                outputs = generate_event_images(
                    task["event"], [task_type], formats, all_events=all_events,
                )
            else:
                print(f"  Unknown task type: {task_type}")
                continue

            if not outputs:
                print("  No images generated, skipping.")
                continue

            # Determine output folder
            folder = outputs[0].parent
            content_type = detect_content_type(folder)

            print(f"  Folder: {folder.name}")
            print(f"  Content type: {content_type}")

            # Post
            results = poster.post_folder(folder, content_type, platforms, dry_run=dry_run)

            # Log success (only if not dry run and at least one platform posted)
            posted_platforms = [p for p, r in results.items() if "posted" in r]
            if not dry_run and posted_platforms:
                log["posts"].append({
                    "key": task["key"],
                    "content_type": task_type,
                    "identifier": task["identifier"],
                    "posted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "folder": folder.name,
                    "platforms": posted_platforms,
                })
                save_posting_log(log)
                print(f"  Logged: {task['key']}")

        except Exception as e:
            print(f"  Error: {e}")
            continue


def main():
    parser = argparse.ArgumentParser(description="Automated social posting scheduler")
    parser.add_argument("--execute", action="store_true", help="Generate and post")
    parser.add_argument("--dry-run", action="store_true", help="Generate and dry-run post")
    parser.add_argument("--date", help="Simulate a different date (YYYY-MM-DD)")
    args = parser.parse_args()

    # Parse reference date
    ref_date = None
    if args.date:
        try:
            ref_date = date.fromisoformat(args.date)
        except ValueError:
            print(f"Invalid date format: {args.date} (expected YYYY-MM-DD)")
            sys.exit(1)

    display_date = ref_date or date.today()
    day_name = display_date.strftime("%A")
    print(f"Scheduler: {display_date.isoformat()} ({day_name})")

    events = load_events()
    log = load_posting_log()
    tasks = get_todays_tasks(events, log, ref_date=ref_date)

    if not tasks:
        print("No posts scheduled for today.")
        return

    print(f"\nTasks for today ({len(tasks)}):")
    for task in tasks:
        status = "ALREADY POSTED" if is_posted(log, task["key"]) else "pending"
        print(f"  [{status}] {task['type']}: {task['identifier']} (key={task['key']})")

    if args.execute or args.dry_run:
        execute_tasks(tasks, all_events=events, dry_run=args.dry_run)
    else:
        print("\nRun with --execute to post, or --dry-run to preview.")


if __name__ == "__main__":
    main()
