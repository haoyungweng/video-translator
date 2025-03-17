#!/usr/bin/env python3
"""
Smart video synchronization that works with a continuous audio file and timing data.
This approach creates a more natural flow by avoiding segment cuts.
"""

import argparse
import os
import sys
import subprocess
import tempfile
import json
import srt
from datetime import timedelta
from tqdm import tqdm

def extract_subtitles(srt_path):
    """Extract subtitles from SRT file."""
    with open(srt_path, 'r', encoding='utf-8') as f:
        return list(srt.parse(f.read()))

def load_timing_data(timing_path):
    """Load timing data from JSON file."""
    with open(timing_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_video_segment(video_path, start_time, end_time, output_path):
    """Extract a segment of the video between start_time and end_time."""
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-ss', str(start_time),
        '-to', str(end_time),
        '-c:v', 'libx264',
        '-preset', 'ultrafast',  # Fast encoding for the first pass
        '-an',  # No audio needed
        '-y',
        output_path
    ]
    
    subprocess.run(cmd, capture_output=True)
    return output_path

def extract_audio_segment(audio_path, start_time, end_time, output_path):
    """Extract a segment of the audio between start_time and end_time."""
    cmd = [
        'ffmpeg',
        '-i', audio_path,
        '-ss', str(start_time),
        '-to', str(end_time),
        '-c:a', 'aac',
        '-y',
        output_path
    ]
    
    subprocess.run(cmd, capture_output=True)
    return output_path

def adjust_video_segment(video_segment, duration_factor, output_path):
    """Adjust video segment speed by the given factor."""
    cmd = [
        'ffmpeg',
        '-i', video_segment,
        '-filter:v', f'setpts={duration_factor}*PTS',  # Adjust video speed
        '-an',  # No audio
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-y',
        output_path
    ]
    
    subprocess.run(cmd, capture_output=True)
    return output_path

def create_segment_list(segments_dir, segments):
    """Create a file list for concatenation."""
    list_path = os.path.join(segments_dir, "segments.txt")
    
    with open(list_path, 'w') as f:
        for segment in segments:
            segment_path = segment["path"]
            if os.path.exists(segment_path):
                f.write(f"file '{os.path.basename(segment_path)}'\n")
                f.write(f"duration {segment['duration']}\n")
    
    return list_path

def concat_segments(segments_list, output_path):
    """Concatenate all segments into the final video."""
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', segments_list,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-an',  # No audio - we'll add it later
        '-y',
        output_path
    ]
    
    subprocess.run(cmd)
    return output_path

def add_audio_to_video(video_path, audio_path, output_path):
    """Add the audio track to the adjusted video."""
    cmd = [
        'ffmpeg',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-map', '0:v',  # Video from first input
        '-map', '1:a',  # Audio from second input
        '-shortest',
        '-y',
        output_path
    ]
    
    subprocess.run(cmd)
    return output_path

def smart_video_sync(video_path, audio_path, timing_path, output_path, max_slowdown=2.0):
    """
    Synchronize video with translated audio using timing data.
    This approach works with a continuous audio file and produces smoother results.
    """
    print("Starting smart video synchronization...")
    
    # Load timing data
    timing_data = load_timing_data(timing_path)
    
    # Create temporary directory for segments
    with tempfile.TemporaryDirectory() as temp_dir:
        # Process each segment
        print(f"Processing {len(timing_data)} video segments...")
        segments = []
        
        for i, segment in tqdm(enumerate(timing_data), total=len(timing_data)):
            # Extract video segment based on original subtitle timing
            subtitle_start = segment["subtitle_start"]
            subtitle_end = segment["subtitle_end"]
            subtitle_duration = segment["subtitle_duration"]
            
            # Get audio timing from the new continuous audio
            audio_duration = segment["audio_duration"]
            
            # Calculate how much to slow down the video
            duration_factor = audio_duration / subtitle_duration if subtitle_duration > 0 else 1.0
            
            # Cap the slowdown factor
            duration_factor = min(duration_factor, max_slowdown)
            
            # Extract the video segment
            video_segment_path = os.path.join(temp_dir, f"video_{i:04d}.mp4")
            extract_video_segment(video_path, subtitle_start, subtitle_end, video_segment_path)
            
            # Adjust the video segment speed
            adjusted_path = os.path.join(temp_dir, f"adjusted_{i:04d}.mp4")
            adjust_video_segment(video_segment_path, duration_factor, adjusted_path)
            
            # Store segment information
            segments.append({
                "index": i,
                "path": adjusted_path,
                "duration": audio_duration,
                "factor": duration_factor
            })
        
        # Create intermediate video with adjusted segments
        segments_list = create_segment_list(temp_dir, segments)
        intermediate_video = os.path.join(temp_dir, "intermediate.mp4")
        concat_segments(segments_list, intermediate_video)
        
        # Add audio to the adjusted video
        print("Adding German audio to the adjusted video...")
        add_audio_to_video(intermediate_video, audio_path, output_path)
        
        print(f"Smart video synchronization complete. Output saved to {output_path}")
        
        # Print statistics
        total_segments = len(segments)
        avg_factor = sum(s["factor"] for s in segments) / total_segments if total_segments > 0 else 0
        max_factor = max(s["factor"] for s in segments) if total_segments > 0 else 0
        
        print(f"Statistics:")
        print(f"- Total segments processed: {total_segments}")
        print(f"- Average slowdown factor: {avg_factor:.2f}x")
        print(f"- Maximum slowdown factor: {max_factor:.2f}x")
        
    return True

def main():
    parser = argparse.ArgumentParser(description='Smart video synchronization with continuous audio')
    parser.add_argument('video_path', help='Path to the original video file')
    parser.add_argument('audio_path', help='Path to the translated audio file')
    parser.add_argument('timing_path', help='Path to the timing JSON file')
    parser.add_argument('output_path', help='Path for the output synchronized video')
    parser.add_argument('--max-slowdown', type=float, default=2.0, 
                        help='Maximum video slowdown factor (default: 2.0)')
    
    args = parser.parse_args()
    
    try:
        success = smart_video_sync(
            args.video_path,
            args.audio_path,
            args.timing_path,
            args.output_path,
            args.max_slowdown
        )
        
        return 0 if success else 1
    
    except Exception as e:
        print(f"Error during video synchronization: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())