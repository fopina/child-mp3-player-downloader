# AGPTEK Swiss Army Knife

A toolkit for preparing media for an AGPTEK player, with MP3 music downloads
and YouTube video conversion for the **AGPTEK M3**.

## Music

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

# Search music directly and display titles, channels, durations, IDs, and URLs
uv run download.py --search "Daft Punk Get Lucky"
uv run download.py --search "Daft Punk Get Lucky" --limit 10

# Download one of the displayed YouTube IDs as a tagged MP3
uv run download.py --search --download dQw4w9WgXcQ
```

With `--search`, the argument is a search string unless `--download` is set;
then it must be an 11-character YouTube video ID (not a URL). Search defaults
to five results and does not create a matches file or downloads directory.
Single-video downloads use `--output` (default: `downloads/`) and YouTube metadata.
For IDs starting with a hyphen, place the ID after `--`.

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

## YouTube videos → AMV

Download videos with the same yt-dlp library used for music, then convert them
with FFmpeg:

```sh
uv run video.py 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
uv run video.py dQw4w9WgXcQ --output videos/
# Fallback if the player rejects the 25 fps video:
uv run video.py dQw4w9WgXcQ --fps 15 --output videos-15fps/
```

Watch URLs, Shorts URLs, youtu.be links, and 11-character IDs are accepted.
For IDs starting with a hyphen, place the ID after `--`. Output is named
`<video-id>.amv`; existing files are skipped. Use a separate output directory
when trying another frame rate. Temporary downloads are removed after conversion
or failure; failed conversions do not leave a final AMV file.

The preset follows the final command in the
[conversion discussion](https://chatgpt.com/share/6ac42ab5-9cb8-83eb-8aad-614bb7c9cd66):

```sh
ffmpeg -i input.mp4 \
  -vf "fps=25,scale=320:240:force_original_aspect_ratio=decrease,pad=320:240:(ow-iw)/2:(oh-ih)/2" \
  -c:v amv -fps_mode cfr \
  -c:a adpcm_ima_amv -ar 22050 -ac 1 -block_size 882 output.amv
```

This preserves aspect ratio with padding at 320×240 and uses mono audio.
The 15 fps option uses 1470-sample blocks instead. FFmpeg needs the `amv` and
`adpcm_ima_amv` encoders; check with `ffmpeg -encoders`. Sources must contain
both video and audio. Copy the resulting AMV to the player's removable drive.
Playback on the physical M3 still needs verification; the discussion does not
confirm its exact required resolution, and other AGPTEK models may need a
different preset.

## Planned: ebooks for the screen

The player's ebook reader supports raw `.txt` files. A future tool could prepare
ebooks as screen-ready text: wrap lines to fit the display, tidy paragraph and
chapter spacing, and normalize characters and encoding for the player. This
feature is an idea and is not implemented yet.
