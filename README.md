# YouTube Studio MCP

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![MCP](https://img.shields.io/badge/MCP-stdio-orange.svg)
![YouTube API](https://img.shields.io/badge/YouTube-Data%20API%20%2B%20Analytics-red.svg)

A local Model Context Protocol (MCP) server for managing YouTube channels from AI tools such as Codex, Claude Desktop, Cursor, and other MCP-compatible clients.

YouTube Studio MCP lets your assistant inspect channel performance, review recent uploads, update video metadata, upload thumbnails, post comments, and read analytics through your own Google OAuth credentials.

![YouTube Studio MCP terminal demo](assets/demo-terminal.svg)

## Demo

```text
User: Show my YouTube channel overview and summarize the last 10 uploaded videos.

Assistant uses:
- youtube_auth_status
- youtube_channel_overview
- youtube_list_videos

Result:
The assistant can review recent uploads, public stats, metadata, privacy status, and improvement opportunities.
```

See [Demo](docs/demo.md) for a setup walkthrough.

## Features

- Read authenticated channel profile, statistics, branding, and uploads playlist.
- List recent videos with metadata, privacy status, content details, and public stats.
- Update video title, description, tags, category, default language, and privacy status.
- Upload custom thumbnails from local image files.
- Read channel and per-video YouTube Analytics reports.
- Post and list top-level video comments.
- Search public channels and compare their subscriber, view, and video counts.
- Runs locally over stdio with no hosted backend.
- Uses only the Python standard library at runtime.

## Why this exists

Creators often want AI help with repetitive YouTube Studio work: auditing metadata, improving SEO, comparing video performance, preparing descriptions, and keeping thumbnails/titles consistent. This MCP server gives an AI assistant controlled access to those workflows while keeping credentials on your own machine.

## Requirements

- Python 3.10 or newer.
- A Google account with access to the YouTube channel.
- A Google Cloud project with:
  - YouTube Data API v3 enabled.
  - YouTube Analytics API enabled.
- A Google OAuth Desktop app client JSON.
- An MCP-compatible client.

## Quick start

Clone the repo:

```bash
git clone https://github.com/i1s-abhishek/youtube-studio-mcp.git
cd youtube-studio-mcp
```

Create the local secrets folder if it does not exist:

```bash
mkdir -p secrets
```

Download your Google OAuth Desktop client JSON and save it as:

```text
secrets/client_secret.json
```

Authenticate with Google:

```bash
python3 scripts/auth.py auth
```

Configure your MCP client to run:

```bash
python3 scripts/server.py
```

See [Google OAuth Setup](docs/setup-google-oauth.md) and [MCP Client Configuration](docs/mcp-client-config.md) for detailed steps.

## MCP configuration

Example stdio config:

```json
{
  "mcpServers": {
    "youtube-studio": {
      "command": "python3",
      "args": ["./scripts/server.py"],
      "cwd": "/absolute/path/to/youtube-studio-mcp",
      "env": {
        "YOUTUBE_CLIENT_SECRETS": "./secrets/client_secret.json",
        "YOUTUBE_TOKEN_FILE": "./secrets/token.json"
      }
    }
  }
}
```

Replace `/absolute/path/to/youtube-studio-mcp` with the path where you cloned this repository.

## Available tools

See [Tools](docs/tools.md) for the full tool list.

Core tools include:

- `youtube_channel_overview`
- `youtube_list_videos`
- `youtube_get_video`
- `youtube_update_video`
- `youtube_upload_thumbnail`
- `youtube_channel_analytics`
- `youtube_video_analytics`
- `youtube_post_comment`
- `youtube_list_comments`
- `youtube_search_channels`
- `youtube_channel_stats`
- `youtube_channel_videos`

## Example prompts

```text
Show my YouTube channel overview and summarize the last 10 uploads.
```

```text
Review my last 28 days of analytics and suggest what I should improve next.
```

```text
Update this video's title, description, tags, and language.
```

```text
Upload this local thumbnail image to video VIDEO_ID.
```

```text
Find the most popular channels in my niche and compare their stats to mine.
```

## OAuth scopes

This server requests:

- `https://www.googleapis.com/auth/youtube`
- `https://www.googleapis.com/auth/youtube.force-ssl`
- `https://www.googleapis.com/auth/youtube.readonly`
- `https://www.googleapis.com/auth/yt-analytics.readonly`

These scopes are broad because the server supports both read and write YouTube Studio actions. Only run this server on machines you trust.

## Safety notes

- Do not commit `secrets/client_secret.json`.
- Do not commit `secrets/token.json`.
- Review tool calls before allowing metadata updates or comments.
- Keep a backup of important titles, descriptions, and tags before bulk updates.

## Verification

Before publishing, this repo was checked to confirm that only `secrets/.gitkeep` is tracked under `secrets/`; real OAuth files such as `secrets/client_secret.json` and `secrets/token.json` are ignored by git.

## Repository topics

Suggested GitHub topics:

```text
mcp, model-context-protocol, youtube, youtube-api, youtube-analytics, youtube-studio, ai-tools, creator-tools, python
```

## Publishing

Maintainers can publish or update the GitHub repository with:

```bash
scripts/publish_github.sh i1s-abhishek youtube-studio-mcp
```

The script creates a public GitHub repo if needed, pushes `main`, and applies relevant discovery topics.

## Sharing

Use [Launch Copy](docs/launch-copy.md) when submitting this project to MCP directories or posting it on social platforms.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

Please read [SECURITY.md](SECURITY.md) before using this with a production channel.

## License

MIT. See [LICENSE](LICENSE).
