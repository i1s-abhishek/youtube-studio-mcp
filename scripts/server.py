#!/usr/bin/env python3
"""Dependency-free MCP server for YouTube metadata, thumbnails, and analytics."""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = "2024-11-05"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
REDIRECT_URI = "http://127.0.0.1:8765/oauth2callback"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_UPLOAD_BASE = "https://www.googleapis.com/upload/youtube/v3"
YOUTUBE_ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def text_content(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def abs_path(path_value: str | None) -> Path:
    if not path_value:
        raise ValueError("Missing path value.")
    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = PLUGIN_ROOT / path
    return path.resolve()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def http_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": {"message": body or str(exc)}}
        raise RuntimeError(parsed.get("error", {}).get("message", body or str(exc))) from exc


def http_empty(
    url: str,
    *,
    method: str = "POST",
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(url, data=data, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": {"message": body or str(exc)}}
        raise RuntimeError(parsed.get("error", {}).get("message", body or str(exc))) from exc


@dataclass
class AuthConfig:
    client_secrets_path: Path
    token_path: Path

    def load_client_config(self) -> dict[str, Any]:
        payload = read_json(self.client_secrets_path)
        client = payload.get("installed") or payload.get("web")
        if not client:
            raise RuntimeError(
                "client_secret.json must contain an 'installed' or 'web' client definition."
            )
        return client

    def load_token(self) -> dict[str, Any]:
        if not self.token_path.exists():
            raise RuntimeError(
                f"Token file not found at {self.token_path}. Run scripts/auth.py first."
            )
        return read_json(self.token_path)

    def save_token(self, payload: dict[str, Any]) -> None:
        write_json(self.token_path, payload)

    def auth_status(self) -> dict[str, Any]:
        return {
            "client_secrets_exists": self.client_secrets_path.exists(),
            "token_exists": self.token_path.exists(),
            "client_secrets_path": str(self.client_secrets_path),
            "token_path": str(self.token_path),
        }


class YouTubeClient:
    def __init__(self, auth: AuthConfig):
        self.auth = auth

    def _refresh_token(self, token: dict[str, Any]) -> dict[str, Any]:
        client = self.auth.load_client_config()
        refresh_token = token.get("refresh_token")
        if not refresh_token:
            raise RuntimeError("Token file does not contain a refresh_token.")
        payload = urllib.parse.urlencode(
            {
                "client_id": client["client_id"],
                "client_secret": client.get("client_secret", ""),
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        refreshed = http_json(
            TOKEN_URL,
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=payload,
        )
        refreshed["refresh_token"] = refresh_token
        refreshed["created_at"] = int(time.time())
        self.auth.save_token(refreshed)
        return refreshed

    def _access_token(self) -> str:
        token = self.auth.load_token()
        expires_in = int(token.get("expires_in", 0))
        created_at = int(token.get("created_at", 0))
        if not token.get("access_token"):
            raise RuntimeError("Token file is missing access_token.")
        if created_at + max(expires_in - 120, 0) <= int(time.time()):
            token = self._refresh_token(token)
        return token["access_token"]

    def _request(
        self,
        base_url: str,
        path: str,
        *,
        method: str = "GET",
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        raw_data: bytes | None = None,
    ) -> dict[str, Any]:
        query_string = ""
        if query:
            cleaned = {key: value for key, value in query.items() if value is not None}
            query_string = "?" + urllib.parse.urlencode(cleaned, doseq=True)
        url = f"{base_url}{path}{query_string}"
        request_headers = {
            "Authorization": f"Bearer {self._access_token()}",
        }
        if headers:
            request_headers.update(headers)
        data = raw_data
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        return http_json(url, method=method, headers=request_headers, data=data)

    def channel_overview(self) -> dict[str, Any]:
        return self._request(
            YOUTUBE_API_BASE,
            "/channels",
            query={"part": "snippet,statistics,brandingSettings,contentDetails", "mine": "true"},
        )

    def list_videos(self, max_results: int = 10, page_token: str | None = None) -> dict[str, Any]:
        channel = self.channel_overview()
        channels = channel.get("items", [])
        if not channels:
            raise RuntimeError("No authenticated YouTube channel was returned.")
        uploads_playlist = (
            channels[0].get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")
        )
        if not uploads_playlist:
            raise RuntimeError("Could not find the uploads playlist for the authenticated channel.")
        playlist = self._request(
            YOUTUBE_API_BASE,
            "/playlistItems",
            query={
                "part": "snippet,contentDetails,status",
                "playlistId": uploads_playlist,
                "maxResults": max(1, min(max_results, 25)),
                "pageToken": page_token,
            },
        )
        video_ids = [
            item.get("contentDetails", {}).get("videoId")
            for item in playlist.get("items", [])
            if item.get("contentDetails", {}).get("videoId")
        ]
        details = {}
        if video_ids:
            details_response = self._request(
                YOUTUBE_API_BASE,
                "/videos",
                query={
                    "part": "snippet,statistics,status,contentDetails",
                    "id": ",".join(video_ids),
                },
            )
            details = {item["id"]: item for item in details_response.get("items", [])}
        merged = []
        for item in playlist.get("items", []):
            video_id = item.get("contentDetails", {}).get("videoId")
            merged.append(
                {
                    "playlistItem": item,
                    "details": details.get(video_id),
                }
            )
        return {
            "items": merged,
            "nextPageToken": playlist.get("nextPageToken"),
            "pageInfo": playlist.get("pageInfo", {}),
        }

    def get_video(self, video_id: str) -> dict[str, Any]:
        result = self._request(
            YOUTUBE_API_BASE,
            "/videos",
            query={"part": "snippet,statistics,status,contentDetails", "id": video_id},
        )
        items = result.get("items", [])
        if not items:
            raise RuntimeError(f"Video {video_id} not found.")
        return items[0]

    def update_video(
        self,
        video_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        category_id: str | None = None,
        default_language: str | None = None,
        privacy_status: str | None = None,
    ) -> dict[str, Any]:
        existing = self.get_video(video_id)
        snippet = existing["snippet"]
        status = existing["status"]
        snippet["title"] = title if title is not None else snippet.get("title", "")
        snippet["description"] = (
            description if description is not None else snippet.get("description", "")
        )
        if tags is not None:
            snippet["tags"] = tags
        if category_id is not None:
            snippet["categoryId"] = category_id
        if default_language is not None:
            snippet["defaultLanguage"] = default_language
        if privacy_status is not None:
            status["privacyStatus"] = privacy_status
        body = {
            "id": video_id,
            "snippet": snippet,
            "status": status,
        }
        return self._request(
            YOUTUBE_API_BASE,
            "/videos",
            method="PUT",
            query={"part": "snippet,status"},
            body=body,
        )

    def upload_thumbnail(self, video_id: str, image_path: str) -> dict[str, Any]:
        path = abs_path(image_path)
        if not path.exists():
            raise RuntimeError(f"Thumbnail file not found: {path}")
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = path.read_bytes()
        return self._request(
            YOUTUBE_UPLOAD_BASE,
            "/thumbnails/set",
            method="POST",
            query={"videoId": video_id, "uploadType": "media"},
            headers={"Content-Type": mime},
            raw_data=body,
        )

    def channel_analytics(self, start_date: str, end_date: str) -> dict[str, Any]:
        return self._request(
            YOUTUBE_ANALYTICS_BASE,
            "/reports",
            query={
                "ids": "channel==MINE",
                "startDate": start_date,
                "endDate": end_date,
                "metrics": ",".join(
                    [
                        "views",
                        "estimatedMinutesWatched",
                        "averageViewDuration",
                        "averageViewPercentage",
                        "likes",
                        "comments",
                        "shares",
                        "subscribersGained",
                        "subscribersLost",
                    ]
                ),
            },
        )

    def video_analytics(self, video_id: str, start_date: str, end_date: str) -> dict[str, Any]:
        return self._request(
            YOUTUBE_ANALYTICS_BASE,
            "/reports",
            query={
                "ids": "channel==MINE",
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": "day",
                "filters": f"video=={video_id}",
                "metrics": ",".join(
                    [
                        "views",
                        "estimatedMinutesWatched",
                        "averageViewDuration",
                        "likes",
                        "comments",
                        "shares",
                        "subscribersGained",
                    ]
                ),
            },
        )

    def post_comment(self, video_id: str, text: str) -> dict[str, Any]:
        body = {
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": text,
                    }
                },
            }
        }
        return self._request(
            YOUTUBE_API_BASE,
            "/commentThreads",
            method="POST",
            query={"part": "snippet"},
            body=body,
        )

    def list_comments(self, video_id: str, max_results: int = 20) -> dict[str, Any]:
        return self._request(
            YOUTUBE_API_BASE,
            "/commentThreads",
            query={
                "part": "snippet",
                "videoId": video_id,
                "maxResults": max(1, min(max_results, 100)),
                "order": "relevance",
                "textFormat": "plainText",
            },
        )


class McpServer:
    def __init__(self) -> None:
        client_secrets = os.environ.get("YOUTUBE_CLIENT_SECRETS", "secrets/client_secret.json")
        token_file = os.environ.get("YOUTUBE_TOKEN_FILE", "secrets/token.json")
        self.auth = AuthConfig(
            client_secrets_path=abs_path(client_secrets),
            token_path=abs_path(token_file),
        )
        self.youtube = YouTubeClient(self.auth)
        self.tools = [
            {
                "name": "youtube_auth_status",
                "description": "Show whether YouTube OAuth credentials and tokens are configured.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "youtube_start_auth",
                "description": "Generate the OAuth authorization URL and local auth command.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "youtube_channel_overview",
                "description": "Fetch the authenticated YouTube channel profile and public statistics.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "youtube_list_videos",
                "description": "List your most recent channel videos with details and statistics.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 25},
                        "page_token": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
            },
            {
                "name": "youtube_get_video",
                "description": "Fetch detailed metadata for a single YouTube video.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"video_id": {"type": "string"}},
                    "required": ["video_id"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "youtube_update_video",
                "description": "Update title, description, tags, category, language, or privacy status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "category_id": {"type": "string"},
                        "default_language": {"type": "string"},
                        "privacy_status": {"type": "string"},
                    },
                    "required": ["video_id"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "youtube_upload_thumbnail",
                "description": "Upload a new custom thumbnail for a video from a local image path.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string"},
                        "image_path": {"type": "string"},
                    },
                    "required": ["video_id", "image_path"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "youtube_channel_analytics",
                "description": "Return channel-level analytics for a date range.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                        "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                    },
                    "required": ["start_date", "end_date"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "youtube_video_analytics",
                "description": "Return per-day analytics for one video across a date range.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string"},
                        "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                        "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                    },
                    "required": ["video_id", "start_date", "end_date"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "youtube_post_comment",
                "description": "Post a top-level comment on one of your YouTube videos.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string"},
                        "text": {"type": "string"},
                    },
                    "required": ["video_id", "text"],
                    "additionalProperties": False,
                },
            },
            {
                "name": "youtube_list_comments",
                "description": "List top-level comment threads on one of your YouTube videos.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "video_id": {"type": "string"},
                        "max_results": {"type": "integer", "minimum": 1, "maximum": 100},
                    },
                    "required": ["video_id"],
                    "additionalProperties": False,
                },
            },
        ]

    def _start_auth_payload(self) -> dict[str, Any]:
        status = self.auth.auth_status()
        if not status["client_secrets_exists"]:
            raise RuntimeError(
                "client_secret.json is missing. Add your Google OAuth desktop client JSON first."
            )
        client = self.auth.load_client_config()
        state = secrets.token_urlsafe(24)
        params = urllib.parse.urlencode(
            {
                "client_id": client["client_id"],
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "scope": " ".join(SCOPES),
                "access_type": "offline",
                "prompt": "consent",
                "state": state,
            }
        )
        helper = PLUGIN_ROOT / "scripts" / "auth.py"
        return {
            "authorization_url": f"{AUTH_URL}?{params}",
            "token_path": status["token_path"],
            "client_secrets_path": status["client_secrets_path"],
            "helper_command": f"python3 {helper} auth",
            "redirect_uri": REDIRECT_URI,
        }

    def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "youtube_auth_status":
            return self.auth.auth_status()
        if name == "youtube_start_auth":
            return self._start_auth_payload()
        if name == "youtube_channel_overview":
            return self.youtube.channel_overview()
        if name == "youtube_list_videos":
            return self.youtube.list_videos(
                int(arguments.get("max_results", 10)), arguments.get("page_token")
            )
        if name == "youtube_get_video":
            return self.youtube.get_video(arguments["video_id"])
        if name == "youtube_update_video":
            return self.youtube.update_video(
                arguments["video_id"],
                title=arguments.get("title"),
                description=arguments.get("description"),
                tags=arguments.get("tags"),
                category_id=arguments.get("category_id"),
                default_language=arguments.get("default_language"),
                privacy_status=arguments.get("privacy_status"),
            )
        if name == "youtube_upload_thumbnail":
            return self.youtube.upload_thumbnail(arguments["video_id"], arguments["image_path"])
        if name == "youtube_channel_analytics":
            return self.youtube.channel_analytics(arguments["start_date"], arguments["end_date"])
        if name == "youtube_video_analytics":
            return self.youtube.video_analytics(
                arguments["video_id"], arguments["start_date"], arguments["end_date"]
            )
        if name == "youtube_post_comment":
            return self.youtube.post_comment(arguments["video_id"], arguments["text"])
        if name == "youtube_list_comments":
            return self.youtube.list_comments(
                arguments["video_id"], int(arguments.get("max_results", 20))
            )
        raise RuntimeError(f"Unknown tool: {name}")

    _ndjson = False  # detected client framing: True = newline-delimited JSON (MCP spec), False = Content-Length

    @classmethod
    def _read_message(cls) -> dict[str, Any] | None:
        headers: dict[str, str] = {}
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                return None
            stripped = line.strip()
            if stripped.startswith(b"{"):
                cls._ndjson = True
                return json.loads(stripped.decode("utf-8"))
            if line == b"\r\n":
                break
            key, _, value = line.decode("utf-8").partition(":")
            headers[key.strip().lower()] = value.strip()
        length = int(headers.get("content-length", "0"))
        if length <= 0:
            return None
        body = sys.stdin.buffer.read(length)
        return json.loads(body.decode("utf-8"))

    @classmethod
    def _write_message(cls, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        if cls._ndjson:
            sys.stdout.buffer.write(encoded + b"\n")
        else:
            sys.stdout.buffer.write(f"Content-Length: {len(encoded)}\r\n\r\n".encode("utf-8"))
            sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()

    def _success(self, message_id: Any, result: dict[str, Any]) -> None:
        self._write_message({"jsonrpc": "2.0", "id": message_id, "result": result})

    def _error(self, message_id: Any, code: int, message: str) -> None:
        self._write_message(
            {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {"code": code, "message": message},
            }
        )

    def serve(self) -> None:
        while True:
            message = self._read_message()
            if message is None:
                return
            message_id = message.get("id")
            method = message.get("method")
            try:
                if method == "initialize":
                    self._success(
                        message_id,
                        {
                            "protocolVersion": PROTOCOL_VERSION,
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "youtube-studio-mcp", "version": "0.1.0"},
                        },
                    )
                elif method == "notifications/initialized":
                    continue
                elif method == "ping":
                    self._success(message_id, {})
                elif method == "tools/list":
                    self._success(message_id, {"tools": self.tools})
                elif method == "tools/call":
                    params = message.get("params", {})
                    result = self._call_tool(params["name"], params.get("arguments", {}))
                    self._success(message_id, {"content": [text_content(json.dumps(result, indent=2))]})
                else:
                    self._error(message_id, -32601, f"Method not found: {method}")
            except Exception as exc:  # noqa: BLE001
                self._error(message_id, -32000, str(exc))


def main() -> None:
    McpServer().serve()


if __name__ == "__main__":
    main()
