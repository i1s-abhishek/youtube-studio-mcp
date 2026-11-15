# Tools

The server exposes these MCP tools.

| Tool | Purpose |
| --- | --- |
| `youtube_auth_status` | Check whether local OAuth files exist. |
| `youtube_start_auth` | Return the auth helper command and OAuth details. |
| `youtube_channel_overview` | Fetch channel profile, branding, uploads playlist, and public statistics. |
| `youtube_list_videos` | List recent uploads with metadata, status, statistics, and pagination. |
| `youtube_get_video` | Fetch metadata for a single video. |
| `youtube_update_video` | Update title, description, tags, category, default language, or privacy status. |
| `youtube_upload_thumbnail` | Upload a local image as a custom thumbnail. |
| `youtube_channel_analytics` | Read channel-level analytics for a date range. |
| `youtube_video_analytics` | Read daily analytics for one video across a date range. |
| `youtube_post_comment` | Post a top-level comment on a video. |
| `youtube_list_comments` | List top-level comment threads for a video. |
| `youtube_search_channels` | Search public channels by keyword and return each match's subscriber, view, and video counts. |
| `youtube_channel_stats` | Fetch public stats for any channels given as IDs, `@handles`, or URLs, sorted by subscribers. |

## API quota

The YouTube Data API's default quota is 10,000 units per day. Most read calls cost 1 unit.
`youtube_search_channels` uses `search.list`, which costs **100 units per call**, plus 1 unit for
the follow-up stats lookup. `youtube_channel_stats` costs 1 unit per 50 channel IDs, or 1 unit per
`@handle` (handles are resolved one at a time).

Stats for other channels are public counts only. YouTube Analytics data is available only for
channels you own, and subscriber counts are omitted for channels that hide them.

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

```text
Find the most popular channels about my niche and compare their stats to mine.
```
