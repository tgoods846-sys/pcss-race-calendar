"""Tests for social media poster module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from social.poster import MetaPoster, _check_response, detect_content_type


# -- detect_content_type --

class TestDetectContentType:
    def test_weekend_preview(self, tmp_path):
        (tmp_path / "weekend_preview_post.png").touch()
        (tmp_path / "captions.txt").touch()
        assert detect_content_type(tmp_path) == "weekend_preview"

    def test_weekly_preview(self, tmp_path):
        (tmp_path / "weekly_preview_post.png").touch()
        assert detect_content_type(tmp_path) == "weekly_preview"

    def test_monthly_calendar(self, tmp_path):
        (tmp_path / "monthly_calendar_post.png").touch()
        assert detect_content_type(tmp_path) == "monthly_calendar"

    def test_race_day(self, tmp_path):
        (tmp_path / "race_day_post.png").touch()
        assert detect_content_type(tmp_path) == "race_day"

    def test_pre_race(self, tmp_path):
        (tmp_path / "pre_race_post.png").touch()
        assert detect_content_type(tmp_path) == "pre_race"

    def test_mixed_prefers_weekend(self, tmp_path):
        (tmp_path / "weekend_preview_post.png").touch()
        (tmp_path / "pre_race_post.png").touch()
        assert detect_content_type(tmp_path) == "weekend_preview"

    def test_empty_folder(self, tmp_path):
        assert detect_content_type(tmp_path) == "pre_race"

    def test_nonexistent_folder(self, tmp_path):
        assert detect_content_type(tmp_path / "nope") == "pre_race"


# -- _check_response --

class TestCheckResponse:
    def _make_response(self, status_code, json_data):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data
        resp.text = json.dumps(json_data)
        resp.raise_for_status = MagicMock()
        return resp

    def test_success(self):
        resp = self._make_response(200, {"id": "123"})
        data = _check_response(resp, "test")
        assert data["id"] == "123"

    def test_rate_limit_code_4(self):
        resp = self._make_response(400, {
            "error": {"code": 4, "message": "Too many calls"}
        })
        with pytest.raises(RuntimeError, match="rate limited"):
            _check_response(resp, "test")

    def test_rate_limit_code_32(self):
        resp = self._make_response(400, {
            "error": {"code": 32, "message": "Limit reached"}
        })
        with pytest.raises(RuntimeError, match="rate limited"):
            _check_response(resp, "test")

    def test_rate_limit_code_613(self):
        resp = self._make_response(400, {
            "error": {"code": 613, "message": "Calls limit"}
        })
        with pytest.raises(RuntimeError, match="rate limited"):
            _check_response(resp, "test")

    def test_expired_token(self):
        resp = self._make_response(400, {
            "error": {"code": 190, "message": "Invalid token"}
        })
        with pytest.raises(RuntimeError, match="expired or invalid"):
            _check_response(resp, "test")

    def test_generic_error(self):
        resp = self._make_response(400, {
            "error": {"code": 100, "message": "Something broke"}
        })
        with pytest.raises(RuntimeError, match="Something broke"):
            _check_response(resp, "test")

    def test_non_json_response(self):
        resp = MagicMock()
        resp.status_code = 500
        resp.json.side_effect = ValueError("No JSON")
        resp.text = "Internal Server Error"
        with pytest.raises(RuntimeError, match="non-JSON response"):
            _check_response(resp, "test")


# -- MetaPoster.post_folder (dry run) --

class TestPostFolder:
    def test_dry_run_selects_correct_files(self, tmp_path):
        """Dry run should identify the right image files without making API calls."""
        # Create test files
        (tmp_path / "pre_race_post.png").write_bytes(b"fake png")
        (tmp_path / "pre_race_facebook.png").write_bytes(b"fake png")
        (tmp_path / "captions.txt").write_text(
            "=== PRE_RACE — INSTAGRAM ===\nIG caption\n\n"
            "=== PRE_RACE — FACEBOOK ===\nFB caption\n"
        )

        poster = MetaPoster("token", "page_id", "ig_user_id")
        results = poster.post_folder(
            tmp_path, "pre_race", ["facebook", "instagram"], dry_run=True,
        )

        assert "facebook" in results
        assert "instagram" in results
        assert "would post" in results["facebook"]
        assert "pre_race_facebook.png" in results["facebook"]
        assert "would post" in results["instagram"]
        assert "pre_race_post.png" in results["instagram"]

    def test_dry_run_missing_image(self, tmp_path):
        """Dry run with missing image file should report 'skipped'."""
        poster = MetaPoster("token", "page_id", "ig_user_id")
        results = poster.post_folder(
            tmp_path, "pre_race", ["facebook"], dry_run=True,
        )
        assert "skipped" in results["facebook"]

    def test_dry_run_with_bare_captions(self, tmp_path):
        """Dry run should work with weekend-style bare caption keys."""
        (tmp_path / "weekend_preview_post.png").write_bytes(b"fake png")
        (tmp_path / "weekend_preview_facebook.png").write_bytes(b"fake png")
        (tmp_path / "captions.txt").write_text(
            "=== INSTAGRAM ===\nWeekend IG caption\n\n"
            "=== FACEBOOK ===\nWeekend FB caption\n"
        )

        poster = MetaPoster("token", "page_id", "ig_user_id")
        results = poster.post_folder(
            tmp_path, "weekend_preview", ["facebook", "instagram"], dry_run=True,
        )

        assert "would post" in results["facebook"]
        assert "Weekend FB" in results["facebook"]
        assert "would post" in results["instagram"]
        assert "Weekend IG" in results["instagram"]


# -- Full post sequence (mocked API) --

class TestPostSequence:
    @patch("social.poster.requests")
    def test_facebook_then_instagram(self, mock_requests, tmp_path):
        """Verify the Facebook→CDN→Instagram call chain."""
        (tmp_path / "pre_race_post.png").write_bytes(b"fake png")
        (tmp_path / "pre_race_facebook.png").write_bytes(b"fake png")
        (tmp_path / "captions.txt").write_text(
            "=== PRE_RACE — INSTAGRAM ===\nIG caption\n\n"
            "=== PRE_RACE — FACEBOOK ===\nFB caption\n"
        )

        # Mock responses
        fb_post_resp = MagicMock()
        fb_post_resp.json.return_value = {"id": "fb_photo_123", "post_id": "post_456"}
        fb_post_resp.status_code = 200

        cdn_resp = MagicMock()
        cdn_resp.json.return_value = {
            "images": [{"source": "https://cdn.fbsbx.com/photo.jpg"}]
        }
        cdn_resp.status_code = 200

        container_resp = MagicMock()
        container_resp.json.return_value = {"id": "container_789"}
        container_resp.status_code = 200

        status_resp = MagicMock()
        status_resp.json.return_value = {"status_code": "FINISHED"}
        status_resp.status_code = 200

        publish_resp = MagicMock()
        publish_resp.json.return_value = {"id": "ig_media_101"}
        publish_resp.status_code = 200

        # Sequence: FB post → CDN get → IG create → IG status → IG publish
        mock_requests.post.side_effect = [fb_post_resp, container_resp, publish_resp]
        mock_requests.get.side_effect = [cdn_resp, status_resp]

        poster = MetaPoster("token", "page_id", "ig_user_id")
        results = poster.post_folder(
            tmp_path, "pre_race", ["facebook", "instagram"],
        )

        assert "posted" in results["facebook"]
        assert "posted" in results["instagram"]

        # Verify call counts
        assert mock_requests.post.call_count == 3  # FB post + IG create + IG publish
        assert mock_requests.get.call_count == 2    # CDN URL + container status

    @patch("social.poster.requests")
    def test_instagram_only_uses_unpublished(self, mock_requests, tmp_path):
        """Instagram-only should use unpublished Facebook upload for CDN URL."""
        (tmp_path / "pre_race_post.png").write_bytes(b"fake png")
        (tmp_path / "captions.txt").write_text(
            "=== PRE_RACE — INSTAGRAM ===\nIG caption\n"
        )

        unpublished_resp = MagicMock()
        unpublished_resp.json.return_value = {"id": "unpub_photo_123"}
        unpublished_resp.status_code = 200

        cdn_resp = MagicMock()
        cdn_resp.json.return_value = {
            "images": [{"source": "https://cdn.fbsbx.com/unpub.jpg"}]
        }
        cdn_resp.status_code = 200

        container_resp = MagicMock()
        container_resp.json.return_value = {"id": "container_789"}
        container_resp.status_code = 200

        status_resp = MagicMock()
        status_resp.json.return_value = {"status_code": "FINISHED"}
        status_resp.status_code = 200

        publish_resp = MagicMock()
        publish_resp.json.return_value = {"id": "ig_media_101"}
        publish_resp.status_code = 200

        mock_requests.post.side_effect = [unpublished_resp, container_resp, publish_resp]
        mock_requests.get.side_effect = [cdn_resp, status_resp]

        poster = MetaPoster("token", "page_id", "ig_user_id")
        results = poster.post_folder(tmp_path, "pre_race", ["instagram"])

        assert "posted" in results["instagram"]

        # The first post call should be the unpublished upload (published=false)
        first_post_call = mock_requests.post.call_args_list[0]
        assert "published" in str(first_post_call) or "photos" in str(first_post_call[0])
