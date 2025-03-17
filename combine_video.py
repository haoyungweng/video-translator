#!/usr/bin/env python3
"""
Combine the lip-synced face video back into the original video.
"""

import argparse
import os
import cv2
import numpy as np
from tqdm import tqdm

def get_video_properties(video_path):
    """Get video properties (fps, dimensions, frame count)."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    return fps, width, height, total_frames

def combine_videos(original_video, face_video, output_video, audio_path=None, face_coordinates=None):
    """
    Combine the lip-synced face region back into the original video.
    
    Args:
        original_video: Path to the original full-size video
        face_video: Path to the lip-synced face video
        output_video: Path for the output combined video
        audio_path: Path to the audio file to use (if None, uses original video audio)
        face_coordinates: Path to file containing face coordinates or a tuple of (x, y, w, h)
    """
    # Get properties of both videos
    orig_fps, orig_width, orig_height, orig_frames = get_video_properties(original_video)
    face_fps, face_width, face_height, face_frames = get_video_properties(face_video)
    
    # Initialize face region as None
    face_region = None
    
    # If face_coordinates is provided as a file path
    if face_coordinates and isinstance(face_coordinates, str) and os.path.exists(face_coordinates):
        print(f"Loading face coordinates from {face_coordinates}")
        with open(face_coordinates, 'r') as f:
            coords = f.read().strip().split(',')
            face_region = tuple(map(int, coords))
            print(f"Loaded face region: x={face_region[0]}, y={face_region[1]}, width={face_region[2]}, height={face_region[3]}")
    # If face_coordinates is provided as a tuple
    elif face_coordinates and not isinstance(face_coordinates, str):
        face_region = face_coordinates
    
    # If face region still not provided, try alternative methods
    if face_region is None:
        # First check for default coordinates file
        default_coords_file = os.path.splitext(face_video)[0] + "_coordinates.txt"
        if os.path.exists(default_coords_file):
            print(f"Loading face coordinates from {default_coords_file}")
            with open(default_coords_file, 'r') as f:
                coords = f.read().strip().split(',')
                face_region = tuple(map(int, coords))
                print(f"Loaded face region: x={face_region[0]}, y={face_region[1]}, width={face_region[2]}, height={face_region[3]}")
        else:
            print("Face region not provided and coordinates file not found. Detecting automatically...")
            # Use MediaPipe to detect face in first frame of original video
            import mediapipe as mp
            
            mp_face_detection = mp.solutions.face_detection
            face_detection = mp_face_detection.FaceDetection(
                model_selection=1, min_detection_confidence=0.5)
                
            cap = cv2.VideoCapture(original_video)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                # Get face detection
                results = face_detection.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                
                if results.detections:
                    detection = results.detections[0]
                    bbox = detection.location_data.relative_bounding_box
                    
                    # Convert to absolute coordinates
                    x = int(bbox.xmin * orig_width)
                    y = int(bbox.ymin * orig_height)
                    w = int(bbox.width * orig_width)
                    h = int(bbox.height * orig_height)
                    
                    # Add padding
                    padding = 0.5
                    padding_x = int(w * padding)
                    padding_y = int(h * padding)
                    
                    x = max(0, x - padding_x)
                    y = max(0, y - padding_y)
                    w = min(orig_width - x, w + 2 * padding_x)
                    h = min(orig_height - y, h + 2 * padding_y)
                    
                    # Make sure dimensions are even
                    w = w - (w % 2)
                    h = h - (h % 2)
                    
                    face_region = (x, y, w, h)
                    print(f"Detected face region: x={x}, y={y}, width={w}, height={h}")
                else:
                    print("No face detected in original video. Using center placement.")
                    # Place in center
                    x = (orig_width - face_width) // 2
                    y = (orig_height - face_height) // 2
                    face_region = (x, y, face_width, face_height)
            else:
                print("Could not read first frame from original video")
                return False
    
    # If provided face region doesn't match face video dimensions, scale the face video
    if face_region[2] != face_width or face_region[3] != face_height:
        print(f"Face region dimensions ({face_region[2]}x{face_region[3]}) don't match face video dimensions ({face_width}x{face_height})")
        print("Will resize face video during processing")
        resize_required = True
    else:
        resize_required = False
    
    # Set up video capture for both videos
    original_cap = cv2.VideoCapture(original_video)
    face_cap = cv2.VideoCapture(face_video)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_video)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Set up video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, orig_fps, (orig_width, orig_height))
    
    # Get face region coordinates
    x, y, w, h = face_region
    
    # Process each frame
    frame_count = min(orig_frames, face_frames)
    
    print(f"Combining videos: {frame_count} frames")
    for i in tqdm(range(int(frame_count))):
        # Read frames from both videos
        ret1, original_frame = original_cap.read()
        ret2, face_frame = face_cap.read()
        
        if not ret1 or not ret2:
            break
        
        # Resize face frame if needed
        if resize_required:
            face_frame = cv2.resize(face_frame, (w, h))
        
        # Overlay face frame onto original frame
        original_frame[y:y+h, x:x+w] = face_frame
        
        # Write to output video
        out.write(original_frame)
    
    # Release resources
    original_cap.release()
    face_cap.release()
    out.release()
    
    # Add audio to the video
    if audio_path:
        print(f"Adding audio from {audio_path} to the video...")
        temp_output = output_video + ".temp.mp4"
        os.rename(output_video, temp_output)
        
        # Use FFmpeg to add the audio
        import subprocess
        cmd = [
            "ffmpeg", "-y",
            "-i", temp_output,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v",
            "-map", "1:a",
            "-shortest",
            output_video
        ]
        
        subprocess.run(cmd, check=True)
        
        # Remove temp file
        os.remove(temp_output)
    
    print(f"Combined video saved to {output_video}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Combine lip-synced face with original video')
    parser.add_argument('original_video', help='Path to original full-size video')
    parser.add_argument('face_video', help='Path to lip-synced face video')
    parser.add_argument('output_video', help='Path for output combined video')
    parser.add_argument('--face_coordinates', help='Path to face coordinates file')
    parser.add_argument('--face_region', help='Face region coordinates (x,y,width,height) as a string', type=str)
    parser.add_argument('--audio', help='Path to audio file to use for the output video')
    
    args = parser.parse_args()
    
    # Parse face region if provided as a string
    face_region = None
    if args.face_region:
        try:
            face_region = tuple(map(int, args.face_region.split(',')))
            if len(face_region) != 4:
                print("Face region must have exactly 4 values: x,y,width,height")
                return 1
        except ValueError:
            print("Invalid face region format. Please use x,y,width,height")
            return 1
    
    try:
        success = combine_videos(
            args.original_video,
            args.face_video,
            args.output_video,
            args.audio,
            args.face_coordinates if args.face_coordinates else face_region
        )
        return 0 if success else 1
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())