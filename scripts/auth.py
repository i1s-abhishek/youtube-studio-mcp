#!/usr/bin/env python3
"""Local OAuth helper for the YouTube Studio MCP plugin."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
REDIRECT_URI = "http://127.0.0.1:8765/oauth2callback"
PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def abs_path(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PLUGIN_ROOT / path
    return path.resolve()


def load_client_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    client = payload.get("installed") or payload.get("web")
    if not client:
        raise RuntimeError("Expected an 'installed' or 'web' client in client_secret.json.")
    return client


def post_form(url: str, payload: dict) -> dict:
    encoded = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


class OAuthHandler(BaseHTTPRequestHandler):
    server_version = "CodexYouTubeOAuth/0.1"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)
        self.server.auth_code = query.get("code", [None])[0]
        self.server.auth_error = query.get("error", [None])[0]
        self.server.auth_state = query.get("state", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if self.server.auth_code:
            body = "<h1>YouTube connection complete.</h1><p>You can return to Codex now.</p>"
        else:
            body = "<h1>YouTube connection failed.</h1><p>Check the terminal for details.</p>"
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        return


def run_auth(client_secrets: Path, token_path: Path) -> int:
    client = load_client_config(client_secrets)
    state = secrets.token_urlsafe(24)
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode("utf-8").rstrip("=")
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf-8")).digest())
        .decode("utf-8")
        .rstrip("=")
    )
    params = urllib.parse.urlencode(
        {
            "client_id": client["client_id"],
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(SCOPES),
            "access_type": "offline",
            "prompt": "select_account consent",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    url = f"{AUTH_URL}?{params}"

    server = HTTPServer(("127.0.0.1", 8765), OAuthHandler)
    server.timeout = 5

    def serve_until_valid():
        # Ignora callbacks obsolets (pestanyes velles del navegador que repeteixen un state
        # antic): serveix peticions fins que arribi el state d'AQUEST intent o s'acabi el temps.
        deadline = time.time() + 300
        while time.time() < deadline:
            server.handle_request()
            if getattr(server, "auth_state", None) == state and (
                getattr(server, "auth_code", None) or getattr(server, "auth_error", None)
            ):
                return
            server.auth_code = server.auth_error = server.auth_state = None

    thread = threading.Thread(target=serve_until_valid, daemon=True)
    thread.start()

    print("Open this URL if your browser does not launch automatically:")
    print(url)
    print("")
    webbrowser.open(url)

    deadline = time.time() + 300
    while time.time() < deadline and not (
        getattr(server, "auth_state", None) == state
        and (getattr(server, "auth_code", None) or getattr(server, "auth_error", None))
    ):
        time.sleep(0.25)

    if getattr(server, "auth_state", None) == state and getattr(server, "auth_error", None):
        print(f"OAuth failed: {server.auth_error}", file=sys.stderr)
        return 1
    if not getattr(server, "auth_code", None):
        print("OAuth failed: timed out waiting for Google callback.", file=sys.stderr)
        return 1

    token = post_form(
        TOKEN_URL,
        {
            "code": server.auth_code,
            "client_id": client["client_id"],
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
            **({"client_secret": client["client_secret"]} if client.get("client_secret") else {}),
        },
    )
    token["created_at"] = int(time.time())
    token_path.parent.mkdir(parents=True, exist_ok=True)
    with token_path.open("w", encoding="utf-8") as handle:
        json.dump(token, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(f"Saved OAuth token to {token_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["auth"])
    parser.add_argument(
        "--client-secrets",
        default=os.environ.get("YOUTUBE_CLIENT_SECRETS", "secrets/client_secret.json"),
    )
    parser.add_argument(
        "--token-file",
        default=os.environ.get("YOUTUBE_TOKEN_FILE", "secrets/token.json"),
    )
    args = parser.parse_args()
    client_secrets = abs_path(args.client_secrets)
    token_path = abs_path(args.token_file)
    return run_auth(client_secrets, token_path)


if __name__ == "__main__":
    raise SystemExit(main())
