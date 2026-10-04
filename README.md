# Spotify track list → YouTube MP3s

Search YouTube for tracks in a CSV, rank five candidates using title/artist and
duration, and download confident matches as tagged 320 kbps MP3s with yt-dlp and
FFmpeg. Reruns reuse matches and skip existing MP3s. Individual failures do not
stop the remaining tracks; the process exits nonzero if anything needs attention.

## Setup

```sh
brew install uv ffmpeg
uv sync --locked
```

YouTube extraction may also require a supported JavaScript runtime, such as
Deno (`brew install deno`). See the [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp).

## Run

```sh
# Search without downloading; inspect candidates and selected_url in matches.json
uv run download.py playlist.csv

# Search and download into downloads/
uv run download.py playlist.csv --download

# Test just the first track
uv run download.py playlist.csv --download --limit 1
```

uv manages the project's `.venv` and installs the versions recorded in `uv.lock`.
To update yt-dlp and its dependencies, run `uv lock --upgrade` followed by
`uv sync --locked`. Python 3.10 or newer is required.

Low-confidence matches are left unselected. Set their `selected_url` in
`matches.json` to the correct `https://www.youtube.com/watch?v=...` URL and rerun.
You can also replace an incorrect automatic choice. `--refresh` discards those
choices for processed tracks and searches again. Matching is heuristic: check
candidates for alternate edits, covers, or music videos with extra audio.

The included `playlist.csv` contains **only the first 25 publicly visible tracks**
from [Chill Clubbing Mix](https://open.spotify.com/playlist/37i9dQZF1EIesBMVrz3ZKZ),
captured October 4, 2026. Spotify reports 50 tracks, but its logged-out page only
exposes 25. Append the remaining rows to process the whole playlist. The script
reads this saved CSV; it does not refresh or import Spotify playlists itself.
Columns: `title,artist,duration,album`, with duration in seconds. Quote values
containing commas. The CSV path is required: use `uv run download.py another.csv`
and a separate `--matches` and
`--output` for another playlist. Keep row order stable when resuming downloads.

MP3 encoding uses the best available YouTube audio as input. 320 kbps limits
additional encoding loss; it cannot recover detail missing from the source.
