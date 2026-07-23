# Tools

Both servers (`scripts/mcp_server.py` and `scripts/server.py`) expose these MCP tools.

| Tool | Purpose |
| --- | --- |
| `youtube_auth_status` | Check whether local OAuth files exist. |
| `youtube_channel_overview` | Fetch channel profile, branding, uploads playlist, and public statistics. |
| `youtube_list_videos` | List recent uploads with metadata, status, statistics, and pagination. |
| `youtube_get_video` | Fetch metadata for a single video. |
| `youtube_update_video` | Update title, description, tags, category, default language, or privacy status. |
| `youtube_upload_thumbnail` | Upload a local image as a custom thumbnail. |
| `youtube_channel_analytics` | Read channel-level analytics for a date range. |
| `youtube_video_analytics` | Read daily analytics for one video across a date range. |
| `youtube_post_comment` | Post a top-level comment on a video. |
| `youtube_list_comments` | List top-level comment threads for a video. |

## server.py-only tools

| Tool | Purpose |
| --- | --- |
| `youtube_start_auth` | Return the auth helper command (`python3 scripts/auth.py auth`) and OAuth file paths. Not available in `scripts/mcp_server.py` — run the helper directly instead. |

## Example prompts

```text
Show my channel overview and the last 10 uploaded videos.
```

```text
Summarize my YouTube analytics for the last 28 days and suggest title or thumbnail improvements.
```

```text
Update video VIDEO_ID with this title, description, and tags.
```

```text
Upload /absolute/path/to/thumbnail.png as the thumbnail for VIDEO_ID.
```
