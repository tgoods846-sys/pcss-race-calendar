"""Post social media images to Instagram and Facebook via the Meta Graph API.

Usage:
    python3 -m social.poster                          # List available folders
    python3 -m social.poster "Folder Name"            # Post to both platforms
    python3 -m social.poster "Folder Name" --dry-run  # Preview without posting
    python3 -m social.poster "Folder Name" --facebook-only
    python3 -m social.poster "Folder Name" --instagram-only
    python3 -m social.poster "Folder Name" --type pre_race
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import requests

from social.captions import get_caption_for_platform, parse_caption_file
from social.config import (
    META_GRAPH_API_BASE,
    OUTPUT_DIR,
    PLATFORM_FORMAT_MAP,
    TEMPLATE_TYPES,
)


def _check_response(resp: requests.Response, context: str) -> dict:
    """Check a Meta Graph API response and raise on error.

    Provides clear messages for common failure modes:
    - Rate limits (error codes 4, 32, 613)
    - Expired/invalid tokens (error code 190)
    """
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"{context}: non-JSON response ({resp.status_code}): {resp.text[:200]}")

    if "error" in data:
        err = data["error"]
        code = err.get("code", 0)
        msg = err.get("message", "Unknown error")

        if code in (4, 32, 613):
            raise RuntimeError(f"{context}: rate limited (code {code}). Wait and retry. API said: {msg}")
        if code == 190:
            raise RuntimeError(
                f"{context}: access token expired or invalid (code 190). "
                f"Generate a new Page Access Token. API said: {msg}"
            )
        raise RuntimeError(f"{context}: API error (code {code}): {msg}")

    resp.raise_for_status()
    return data


def detect_content_type(folder: Path) -> str:
    """Detect the content type from files present in an output folder.

    Returns one of the TEMPLATE_TYPES values.
    """
    filenames = [f.name for f in folder.iterdir()] if folder.is_dir() else []
    for name in filenames:
        if name.startswith("weekend_preview"):
            return "weekend_preview"
        if name.startswith("weekly_preview"):
            return "weekly_preview"
        if name.startswith("monthly_calendar"):
            return "monthly_calendar"
        if name.startswith("race_day"):
            return "race_day"
        if name.startswith("pre_race"):
            return "pre_race"
    return "pre_race"


class MetaPoster:
    """Client for posting images to Facebook and Instagram via the Meta Graph API."""

    # Seconds to wait between Instagram container status polls
    POLL_INTERVAL = 3
    MAX_POLLS = 20

    def __init__(
        self,
        page_access_token: str,
        page_id: str,
        ig_user_id: str,
    ):
        self.token = page_access_token
        self.page_id = page_id
        self.ig_user_id = ig_user_id
        self.api = META_GRAPH_API_BASE

    # ------------------------------------------------------------------
    # Facebook
    # ------------------------------------------------------------------

    def post_to_facebook(self, image_path: Path, caption: str) -> dict:
        """Post a photo to the Facebook Page.

        Uses multipart upload via ``POST /{page_id}/photos``.
        Returns the API response dict (contains ``id`` and ``post_id``).
        """
        url = f"{self.api}/{self.page_id}/photos"
        with open(image_path, "rb") as f:
            resp = requests.post(
                url,
                files={"source": (image_path.name, f, "image/png")},
                data={"caption": caption, "access_token": self.token},
            )
        return _check_response(resp, f"Facebook post ({image_path.name})")

    def get_photo_cdn_url(self, photo_id: str) -> str:
        """Retrieve the CDN URL for a Facebook photo.

        Uses ``GET /{photo_id}?fields=images`` and returns the largest image URL.
        """
        url = f"{self.api}/{photo_id}"
        resp = requests.get(url, params={"fields": "images", "access_token": self.token})
        data = _check_response(resp, f"Get photo CDN URL ({photo_id})")
        images = data.get("images", [])
        if not images:
            raise RuntimeError(f"No images returned for photo {photo_id}")
        # images are sorted largest-first by default
        return images[0]["source"]

    def _upload_unpublished(self, image_path: Path) -> str:
        """Upload a photo to Facebook without publishing it.

        Returns the photo ID, which can be used to get a CDN URL for Instagram.
        """
        url = f"{self.api}/{self.page_id}/photos"
        with open(image_path, "rb") as f:
            resp = requests.post(
                url,
                files={"source": (image_path.name, f, "image/png")},
                data={
                    "published": "false",
                    "access_token": self.token,
                },
            )
        data = _check_response(resp, f"Unpublished upload ({image_path.name})")
        return data["id"]

    # ------------------------------------------------------------------
    # Instagram
    # ------------------------------------------------------------------

    def _wait_for_container(self, container_id: str) -> None:
        """Poll an Instagram media container until its status is FINISHED."""
        url = f"{self.api}/{container_id}"
        for _ in range(self.MAX_POLLS):
            resp = requests.get(
                url,
                params={"fields": "status_code", "access_token": self.token},
            )
            data = _check_response(resp, f"Container status ({container_id})")
            status = data.get("status_code")
            if status == "FINISHED":
                return
            if status == "ERROR":
                raise RuntimeError(f"Instagram container {container_id} failed: {data}")
            time.sleep(self.POLL_INTERVAL)
        raise RuntimeError(f"Instagram container {container_id} did not finish in time")

    def post_to_instagram(self, image_url: str, caption: str) -> dict:
        """Post an image to Instagram via the Content Publishing API.

        This is a two-step process:
        1. Create a media container with the ``image_url``
        2. Publish the container

        ``image_url`` must be a publicly accessible URL (e.g. a Facebook CDN URL).
        """
        # Step 1: create container
        create_url = f"{self.api}/{self.ig_user_id}/media"
        resp = requests.post(
            create_url,
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": self.token,
            },
        )
        data = _check_response(resp, "Instagram create container")
        container_id = data["id"]

        # Wait for processing
        self._wait_for_container(container_id)

        # Step 2: publish
        publish_url = f"{self.api}/{self.ig_user_id}/media_publish"
        resp = requests.post(
            publish_url,
            data={"creation_id": container_id, "access_token": self.token},
        )
        return _check_response(resp, "Instagram publish")

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def post_folder(
        self,
        folder: Path,
        content_type: str,
        platforms: list[str],
        dry_run: bool = False,
    ) -> dict[str, str]:
        """Post images from an output folder to the specified platforms.

        Returns a dict mapping platform names to result descriptions.
        """
        results: dict[str, str] = {}

        # Load captions
        caption_file = folder / "captions.txt"
        if caption_file.exists():
            sections = parse_caption_file(caption_file)
        else:
            sections = {}

        for platform in platforms:
            fmt = PLATFORM_FORMAT_MAP.get(platform)
            if not fmt:
                results[platform] = f"skipped: unknown platform '{platform}'"
                continue

            # Find the image file
            image_path = self._find_image(folder, content_type, fmt)
            if not image_path:
                results[platform] = f"skipped: no {content_type}_{fmt}.png found"
                continue

            caption = get_caption_for_platform(sections, content_type, platform) or ""

            if dry_run:
                caption_preview = (caption[:80] + "...") if len(caption) > 80 else caption
                results[platform] = f"would post {image_path.name} with caption: {caption_preview}"
                print(f"  [DRY RUN] {platform}: {image_path.name}")
                print(f"    Caption: {caption_preview}")
                continue

            if platform == "facebook":
                data = self.post_to_facebook(image_path, caption)
                results["facebook"] = f"posted (id={data.get('id', '?')})"
                print(f"  Facebook: posted {image_path.name} (id={data.get('id', '?')})")

            elif platform == "instagram":
                # Instagram needs a public URL — upload to Facebook first
                if "facebook" in results and "posted" in results.get("facebook", ""):
                    # Already posted to Facebook; get CDN URL from that photo
                    fb_photo_id = results["facebook"].split("id=")[1].rstrip(")")
                    cdn_url = self.get_photo_cdn_url(fb_photo_id)
                else:
                    # Upload unpublished to get a CDN URL
                    ig_image_path = self._find_image(folder, content_type, PLATFORM_FORMAT_MAP["instagram"])
                    if ig_image_path is None:
                        ig_image_path = image_path
                    photo_id = self._upload_unpublished(ig_image_path)
                    cdn_url = self.get_photo_cdn_url(photo_id)

                data = self.post_to_instagram(cdn_url, caption)
                results["instagram"] = f"posted (id={data.get('id', '?')})"
                print(f"  Instagram: posted (id={data.get('id', '?')})")

        return results

    @staticmethod
    def _find_image(folder: Path, content_type: str, fmt: str) -> Path | None:
        """Find the image file for a given content type and format."""
        path = folder / f"{content_type}_{fmt}.png"
        return path if path.exists() else None


def list_folders() -> list[Path]:
    """List available output folders in OUTPUT_DIR."""
    if not OUTPUT_DIR.exists():
        return []
    return sorted(
        [p for p in OUTPUT_DIR.iterdir() if p.is_dir()],
        key=lambda p: p.name,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Post social media images to Instagram and Facebook",
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Folder name within output/social/ (omit to list available folders)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without posting")
    parser.add_argument("--facebook-only", action="store_true", help="Post to Facebook only")
    parser.add_argument("--instagram-only", action="store_true", help="Post to Instagram only")
    parser.add_argument(
        "--type",
        choices=TEMPLATE_TYPES,
        help="Content type (auto-detected if omitted)",
    )
    args = parser.parse_args()

    # List mode
    if not args.folder:
        folders = list_folders()
        if not folders:
            print("No output folders found in output/social/")
            sys.exit(0)
        print("Available folders:")
        for f in folders:
            print(f"  {f.name}")
        sys.exit(0)

    # Resolve folder
    folder = OUTPUT_DIR / args.folder
    if not folder.exists():
        # Try partial match
        matches = [f for f in list_folders() if args.folder.lower() in f.name.lower()]
        if len(matches) == 1:
            folder = matches[0]
            print(f"Matched folder: {folder.name}")
        elif len(matches) > 1:
            print(f"Ambiguous folder name '{args.folder}'. Matches:")
            for m in matches:
                print(f"  {m.name}")
            sys.exit(1)
        else:
            print(f"Folder not found: {args.folder}")
            sys.exit(1)

    # Detect content type
    content_type = args.type or detect_content_type(folder)
    print(f"Content type: {content_type}")

    # Platforms
    if args.facebook_only:
        platforms = ["facebook"]
    elif args.instagram_only:
        platforms = ["instagram"]
    else:
        platforms = ["facebook", "instagram"]

    print(f"Platforms: {', '.join(platforms)}")
    print(f"Folder: {folder.name}")

    if args.dry_run:
        print("\n[DRY RUN MODE]")
        poster = MetaPoster(
            page_access_token="DRY_RUN",
            page_id="DRY_RUN",
            ig_user_id="DRY_RUN",
        )
        poster.post_folder(folder, content_type, platforms, dry_run=True)
        return

    # Load credentials from environment
    token = os.environ.get("META_PAGE_ACCESS_TOKEN")
    page_id = os.environ.get("META_PAGE_ID")
    ig_user_id = os.environ.get("META_IG_USER_ID")

    if not token or not page_id:
        print("Error: META_PAGE_ACCESS_TOKEN and META_PAGE_ID must be set")
        sys.exit(1)

    if "instagram" in platforms and not ig_user_id:
        print("Error: META_IG_USER_ID must be set for Instagram posting")
        sys.exit(1)

    poster = MetaPoster(
        page_access_token=token,
        page_id=page_id,
        ig_user_id=ig_user_id or "",
    )

    print(f"\nPosting to {', '.join(platforms)}...")
    results = poster.post_folder(folder, content_type, platforms)

    print("\nResults:")
    for platform, result in results.items():
        print(f"  {platform}: {result}")


if __name__ == "__main__":
    main()
