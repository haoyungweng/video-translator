#!/usr/bin/env python3
"""
Extract audio from video file using FFmpeg.
"""

import argparse
import subprocess
import os

def extract_audio(video_path, audio_path, audio_format="wav"):
    """Extract audio from video file using FFmpeg."""
    if not os.path.exists(video_path):
        print(f"Error: Video file '{video_path}' not found.")
        return False
    
    try:
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-q:a', '0',  # Highest quality
            '-map', 'a',  # Extract audio only
            '-y',  # Overwrite output file if it exists
            audio_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Successfully extracted audio to {audio_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error extracting audio: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Extract audio from video file.')
    parser.add_argument('video_path', help='Path to input video file')
    parser.add_argument('audio_path', help='Path for output audio file')
    parser.add_argument('--format', default='wav', help='Audio format (default: wav)')
    
    args = parser.parse_args()
    
    success = extract_audio(args.video_path, args.audio_path, args.format)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())