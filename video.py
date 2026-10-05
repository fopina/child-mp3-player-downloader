#!/usr/bin/env python3
"""Download a YouTube video and convert it to AMV for the AGPTEK M3."""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from download import run_ytdlp


def convert_video(source, destination, fps=25):
    """Use the explicit FPS filter and matching AMV audio block size."""
    result = subprocess.run([
        'ffmpeg', '-nostdin', '-y', '-i', str(source),
        '-map', '0:v:0', '-map', '0:a:0',
        '-vf', f'fps={fps},scale=320:240:force_original_aspect_ratio=decrease,'
               'pad=320:240:(ow-iw)/2:(oh-ih)/2',
        '-c:v', 'amv', '-fps_mode', 'cfr',
        '-c:a', 'adpcm_ima_amv', '-ar', '22050', '-ac', '1',
        '-block_size', str(22050 // fps), str(destination),
    ])
    if result.returncode or not destination.is_file() or not destination.stat().st_size:
        raise RuntimeError('FFmpeg did not create an AMV video; see its output above')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', help='YouTube video ID or watch / short / youtu.be URL')
    parser.add_argument('--output', type=Path, default=Path('downloads'))
    parser.add_argument('--fps', type=int, choices=(15, 25), default=25,
                        help='25 by default; try 15 if the player rejects the video')
    args = parser.parse_args()
    video_id = args.video
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        match = re.fullmatch(
            r'https?://(?:(?:www\.|m\.)?youtube\.com/(?:watch\?v=|shorts/)'
            r'|youtu\.be/)([A-Za-z0-9_-]{11})(?:[?&][^\s]*)?', video_id)
        if not match:
            parser.error('Provide a YouTube video ID or a YouTube watch / short / youtu.be URL')
        video_id = match[1]
    if any(not shutil.which(tool) for tool in ('ffmpeg', 'ffprobe')):
        parser.error('Install FFmpeg first (macOS: brew install ffmpeg)')
    try:
        args.output.mkdir(parents=True, exist_ok=True)
        destination = args.output / f'{video_id}.amv'
        if destination.exists():
            print(f'Already downloaded: {destination}')
            return 0
        # Stage both files together so a failed conversion never becomes a final output.
        with tempfile.TemporaryDirectory(prefix='agptek-video-', dir=args.output) as folder:
            staging = Path(folder)
            manifest = staging / 'source-path.txt'
            template = str(staging).replace('%', '%%') + '/source.%(ext)s'
            run_ytdlp([
                '--no-playlist', '-f', 'bestvideo+bestaudio/best',
                '--merge-output-format', 'mkv', '-o', template,
                '--print-to-file', 'after_move:filepath', str(manifest),
                'https://www.youtube.com/watch?v=' + video_id,
            ])
            source = Path(manifest.read_text().strip())
            converted = staging / 'converted.amv'
            convert_video(source, converted, args.fps)
            converted.replace(destination)
        print(f'Video saved in {destination}')
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f'Failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
