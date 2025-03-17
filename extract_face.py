"""
Extract just the face region from a video to create a smaller video for lip syncing.
"""

import argparse
import os
import cv2
import numpy as np
import mediapipe as mp
from tqdm import tqdm

def extract_face_region(input_video, output_video, coordinates_file=None, padding=0.5):
    """
    Extract just the face region from a video and save to a new file.
    Also saves the face coordinates to a file for later use.
    
    Args:
        input_video: Path to input video
        output_video: Path to output video (will contain just the face)
        coordinates_file: Path to save face coordinates (if None, uses default based on output_video)
        padding: Extra padding around the face (0.5 = 50% extra on each side)
    """
    # Initialize face detector
    mp_face_detection = mp.solutions.face_detection
    face_detection = mp_face_detection.FaceDetection(
        model_selection=1,  # Use full range model
        min_detection_confidence=0.5
    )
    
    # Open video
    cap = cv2.VideoCapture(input_video)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Sample frames to detect face
    print("Detecting consistent face region...")
    face_boxes = []
    sample_rate = max(1, total_frames // 20)  # Sample ~20 frames
    
    for i in tqdm(range(0, total_frames, sample_rate)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            continue
            
        # Convert to RGB for MediaPipe
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detection.process(frame_rgb)
        
        if results.detections:
            # Get the first face
            detection = results.detections[0]
            bbox = detection.location_data.relative_bounding_box
            
            # Convert to absolute coordinates
            x = int(bbox.xmin * frame_width)
            y = int(bbox.ymin * frame_height)
            w = int(bbox.width * frame_width)
            h = int(bbox.height * frame_height)
            
            face_boxes.append((x, y, w, h))
    
    # Calculate average face box
    if not face_boxes:
        print("No faces detected. Using full frame.")
        x, y, w, h = 0, 0, frame_width, frame_height
    else:
        avg_x = sum(box[0] for box in face_boxes) // len(face_boxes)
        avg_y = sum(box[1] for box in face_boxes) // len(face_boxes)
        avg_w = sum(box[2] for box in face_boxes) // len(face_boxes)
        avg_h = sum(box[3] for box in face_boxes) // len(face_boxes)
        
        # Add padding
        padding_x = int(avg_w * padding)
        padding_y = int(avg_h * padding)
        
        x = max(0, avg_x - padding_x)
        y = max(0, avg_y - padding_y)
        w = min(frame_width - x, avg_w + 2 * padding_x)
        h = min(frame_height - y, avg_h + 2 * padding_y)
    
    # Make dimensions divisible by 2 (required by some codecs)
    w = w - (w % 2)
    h = h - (h % 2)
    
    print(f"Extracting region: x={x}, y={y}, width={w}, height={h}")
    
    # Set up output video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video, fourcc, fps, (w, h))
    
    # Reset video to beginning
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    # Extract face region from each frame
    print("Extracting face region from video...")
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Extract face region
        face_frame = frame[y:y+h, x:x+w]
        out.write(face_frame)
        
        frame_count += 1
        if frame_count % 100 == 0:
            print(f"Processed {frame_count}/{total_frames} frames")
    
    # Release resources
    cap.release()
    out.release()
    
    # If coordinates_file is None, use default path
    if coordinates_file is None:
        coordinates_file = os.path.splitext(output_video)[0] + "_coordinates.txt"
    
    # Save face coordinates to a file
    with open(coordinates_file, 'w') as f:
        f.write(f"{x},{y},{w},{h}")
    
    print(f"Face region extracted and saved to {output_video}")
    print(f"Face coordinates saved to {coordinates_file}")
    
    return x, y, w, h

def main():
    parser = argparse.ArgumentParser(description='Extract face region from video')
    parser.add_argument('input_video', help='Path to input video file')
    parser.add_argument('output_video', help='Path for output video file')
    parser.add_argument('--coordinates_file', help='Path to save face coordinates')
    parser.add_argument('--padding', type=float, default=0.5, 
                        help='Extra padding around face (default: 0.5)')
    
    args = parser.parse_args()
    
    try:
        extract_face_region(args.input_video, args.output_video, args.coordinates_file, args.padding)
        return 0
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())