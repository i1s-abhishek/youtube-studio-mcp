#!/usr/bin/env python3
"""Check the stdio transport speaks both NDJSON (MCP spec) and Content-Length framing."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parent.parent / "scripts" / "server.py"

INITIALIZE = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
TOOLS_LIST = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}


def run_server(stdin: bytes) -> bytes:
    done = subprocess.run(
        [sys.executable, str(SERVER)],
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=15,
    )
    assert done.returncode == 0, done.stderr.decode()
    return done.stdout


def test_ndjson_framing() -> None:
    stdin = b"".join(json.dumps(m).encode() + b"\n" for m in (INITIALIZE, TOOLS_LIST))
    lines = [line for line in run_server(stdin).split(b"\n") if line.strip()]
    assert len(lines) == 2, lines
    init, tools = (json.loads(line) for line in lines)
    assert init["id"] == 1 and init["result"]["serverInfo"]["name"] == "youtube-studio-mcp"
    assert tools["id"] == 2 and len(tools["result"]["tools"]) > 0


def test_content_length_framing() -> None:
    stdin = b""
    for message in (INITIALIZE, TOOLS_LIST):
        body = json.dumps(message).encode()
        stdin += b"Content-Length: %d\r\n\r\n" % len(body) + body
    stdout = run_server(stdin)
    assert stdout.startswith(b"Content-Length: "), stdout[:40]
    ids = [json.loads(chunk.split(b"\r\n\r\n", 1)[1]) ["id"] for chunk in stdout.split(b"Content-Length: ")[1:]]
    assert ids == [1, 2], ids


def test_unknown_method_is_a_jsonrpc_error() -> None:
    bad = {"jsonrpc": "2.0", "id": 9, "method": "nope/nope"}
    reply = json.loads(run_server(json.dumps(bad).encode() + b"\n").strip())
    assert reply["error"]["code"] == -32601, reply


if __name__ == "__main__":
    test_ndjson_framing()
    test_content_length_framing()
    test_unknown_method_is_a_jsonrpc_error()
    print("ok")
