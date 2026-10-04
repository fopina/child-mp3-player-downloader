#!/usr/bin/env python3
"""Search a track CSV on YouTube and optionally download tagged MP3s."""
import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path


def words(text):
    text = unicodedata.normalize('NFKD', text.casefold())
    return set(re.findall(r'\w+', ''.join(c for c in text if not unicodedata.combining(c))))


def rank(track, video):
    """Conservative heuristic, not an identity guarantee."""
    title = words(re.sub(r'\((?:feat\.|with)\s.*?\)', '', track['title']))
    artist = words(track['artist'].split(',')[0])
    haystack = words(video.get('title', '') + ' ' + (video.get('channel') or ''))
    duration = video.get('duration')
    if not duration or video.get('live_status') == 'is_live':
        return 0
    difference = abs(duration - int(track['duration']))
    if difference > max(30, int(track['duration']) * .15):
        return 0
    score = .55 * len(title & haystack) / max(1, len(title))
    score += .30 * len(artist & haystack) / max(1, len(artist))
    score += .15 * max(0, 1 - difference / 30)
    unwanted = {'cover', 'karaoke', 'live', 'sped', 'slowed', 'remix'}
    if (words(video.get('title', '')) & unwanted) - words(track['title']):
        score -= .35
    return round(max(0, score), 3)


def run_ytdlp(args, capture=False):
    result = subprocess.run(
        [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--socket-timeout', '20',
         '--retries', '3', *args], text=True, capture_output=capture,
        timeout=180 if capture else None,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or 'yt-dlp failed')[-2000:])
    if capture and result.stderr:
        print(result.stderr, file=sys.stderr, end='')
    return result.stdout


def save(path, data):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tracks', type=Path, help='Path to the playlist CSV')
    parser.add_argument('--matches', type=Path, default=Path('matches.json'))
    parser.add_argument('--output', type=Path, default=Path('downloads'))
    parser.add_argument('--download', action='store_true', help='Download confident matches; default only searches')
    parser.add_argument('--limit', type=int, help='Process only the first N tracks')
    parser.add_argument('--refresh', action='store_true', help='Search again instead of reusing saved matches')
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    if args.download and any(not shutil.which(x) for x in ('ffmpeg', 'ffprobe')):
        parser.error('Install FFmpeg first (macOS: brew install ffmpeg)')
    with args.tracks.open(newline='', encoding='utf-8-sig') as f:
        tracks = list(csv.DictReader(f))
    for track in tracks:
        if not all(track.get(k) for k in ('title', 'artist', 'duration')) or not track['duration'].isdigit():
            parser.error('CSV requires title, artist, duration (integer seconds); album is optional')
    matches = json.loads(args.matches.read_text()) if args.matches.exists() else {}
    args.output.mkdir(parents=True, exist_ok=True)
    args.matches.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    for index, track in enumerate(tracks[:args.limit], 1):
        key = f"{track['artist']} - {track['title']}"
        print(f'[{index}] {key}', flush=True)
        try:
            item = matches.get(key)
            if args.refresh or not item or item.get('track') != track:
                query = f"ytsearch5:{track['artist']} {track['title']} official audio"
                result = json.loads(run_ytdlp(['--flat-playlist', '--dump-single-json', query], True))
                if not result.get('entries'):
                    query = f"ytsearch5:{track['artist'].split(',')[0]} {track['title']}"
                    result = json.loads(run_ytdlp(['--flat-playlist', '--dump-single-json', query], True))
                candidates = []
                for video in result.get('entries') or []:
                    if not video or not re.fullmatch(r'[\w-]{11}', video.get('id', '')):
                        continue
                    candidates.append({'url': 'https://www.youtube.com/watch?v=' + video['id'],
                                       'title': video.get('title'), 'duration': video.get('duration'),
                                       'score': rank(track, video)})
                candidates.sort(key=lambda v: v['score'], reverse=True)
                item = {'track': track, 'selected_url': candidates[0]['url'] if candidates and candidates[0]['score'] >= .8 else None,
                        'candidates': candidates}
                matches[key] = item
                save(args.matches, matches)
            url = item.get('selected_url')
            if not url:
                print('  Needs review: choose selected_url in matches.json', flush=True)
                failures += 1
                continue
            if not re.fullmatch(r'https://www\.youtube\.com/watch\?v=[\w-]{11}', url):
                raise ValueError('selected_url must be a YouTube watch URL')
            print(f'  {url}', flush=True)
            if not args.download:
                continue
            # Restrict literal filename characters; escape yt-dlp template percent signs.
            stem = re.sub(r'[^\w .()-]', '_', key)[:160].rstrip(' .')
            destination = args.output / f'{index:02d} - {stem}.mp3'
            if destination.is_file():
                print('  Already downloaded', flush=True)
                continue
            template = str(destination.with_suffix('')).replace('%', '%%') + '.%(ext)s'
            metadata = []
            for field, value in [('title', track['title']), ('artist', track['artist']),
                                 ('album', track.get('album', '')), ('track', str(index))]:
                # A literal field supplied via --parse-metadata is parsed into the tag.
                metadata += ['--parse-metadata', f'{value.replace("%", "%%")}:%(meta_{field})s']
            run_ytdlp(['--no-playlist', '-f', 'bestaudio/best', '-x', '--audio-format', 'mp3',
                       '--audio-quality', '320K', '--embed-metadata', *metadata,
                       '--no-overwrites', '-o', template, url])
            if not destination.is_file():
                raise RuntimeError('MP3 output was not created')
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            failures += 1
            print(f'  Failed: {error}', file=sys.stderr, flush=True)
    print(f'Matches saved in {args.matches}; {failures} track(s) need attention.')
    return 1 if failures else 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
