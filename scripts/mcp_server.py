#!/usr/bin/env python3
"""MCP server for YouTube Studio using the official MCP Python SDK."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add parent so we can import from server.py
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.fastmcp import FastMCP
from server import AuthConfig, YouTubeClient, abs_path

# Initialize auth and client
client_secrets = os.environ.get("YOUTUBE_CLIENT_SECRETS", "secrets/client_secret.json")
token_file = os.environ.get("YOUTUBE_TOKEN_FILE", "secrets/token.json")
auth = AuthConfig(
    client_secrets_path=abs_path(client_secrets),
    token_path=abs_path(token_file),
)
youtube = YouTubeClient(auth)

mcp = FastMCP("youtube-studio")


@mcp.tool()
def youtube_auth_status() -> str:
    """Show whether YouTube OAuth credentials and tokens are configured."""
    return json.dumps(auth.auth_status(), indent=2)


@mcp.tool()
def youtube_channel_overview() -> str:
    """Fetch the authenticated YouTube channel profile and public statistics."""
    return json.dumps(youtube.channel_overview(), indent=2)


@mcp.tool()
def youtube_list_videos(max_results: int = 10, page_token: str | None = None) -> str:
    """List your most recent channel videos with details and statistics."""
    return json.dumps(youtube.list_videos(max_results, page_token), indent=2)


@mcp.tool()
def youtube_get_video(video_id: str) -> str:
    """Fetch detailed metadata for a single YouTube video."""
    return json.dumps(youtube.get_video(video_id), indent=2)


@mcp.tool()
def youtube_update_video(
    video_id: str,
    title: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    category_id: str | None = None,
    default_language: str | None = None,
    privacy_status: str | None = None,
) -> str:
    """Update title, description, tags, category, language, or privacy status."""
    return json.dumps(
        youtube.update_video(
            video_id,
            title=title,
            description=description,
            tags=tags,
            category_id=category_id,
            default_language=default_language,
            privacy_status=privacy_status,
        ),
        indent=2,
    )


@mcp.tool()
def youtube_upload_thumbnail(video_id: str, image_path: str) -> str:
    """Upload a new custom thumbnail for a video from a local image path."""
    return json.dumps(youtube.upload_thumbnail(video_id, image_path), indent=2)


@mcp.tool()
def youtube_channel_analytics(start_date: str, end_date: str) -> str:
    """Return channel-level analytics for a date range (YYYY-MM-DD)."""
    return json.dumps(youtube.channel_analytics(start_date, end_date), indent=2)


@mcp.tool()
def youtube_video_analytics(video_id: str, start_date: str, end_date: str) -> str:
    """Return per-day analytics for one video across a date range (YYYY-MM-DD)."""
    return json.dumps(youtube.video_analytics(video_id, start_date, end_date), indent=2)


@mcp.tool()
def youtube_post_comment(video_id: str, text: str) -> str:
    """Post a top-level comment on one of your YouTube videos."""
    return json.dumps(youtube.post_comment(video_id, text), indent=2)


@mcp.tool()
def youtube_list_comments(video_id: str, max_results: int = 20) -> str:
    """List top-level comment threads on one of your YouTube videos."""
    return json.dumps(youtube.list_comments(video_id, max_results), indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
