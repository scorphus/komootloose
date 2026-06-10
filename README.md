<img src="https://raw.githubusercontent.com/scorphus/komootloose/main/assets/logo-wordmark.svg" alt="komootloose" width="520">

Export komoot tours as GPX files from the command line — no subscription needed.

## Installation

```sh
uv tool install komootloose
```

Or `pipx install komootloose`, or `pip install komootloose`.

## Usage

```sh
komootloose 123456
komootloose https://www.komoot.com/tour/123456
komootloose "https://www.komoot.com/tour/123456?share_token=..."  # link-shared tours
komootloose https://www.komoot.com/smarttour/123456 -o route.gpx
komootloose 123456 -o -  # write GPX to stdout
```

Each tour is written to `<tour name>.gpx` unless `-o` is given.

## Development

```sh
uv sync
uv run pytest
```
