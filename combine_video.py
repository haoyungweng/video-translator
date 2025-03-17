"""
Combine the lip-synced face video back into the original video.
Includes color correction to maintain consistent appearance.
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

def color_correct_image(source, target):
    """Apply color correction to make source match target's color profile."""
    # Convert images to LAB color space (better for color correction)
    source_lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB)
    target_lab = cv2.cvtColor(target, cv2.COLOR_BGR2LAB)
    
    # Calculate the mean and std for each channel in LAB
    source_mean, source_std = cv2.meanStdDev(source_lab)
    target_mean, target_std = cv2.meanStdDev(target_lab)
    
    # Adjust each channel
    corrected_lab = np.copy(source_lab).astype(np.float32)
    for i in range(3):  # L, A, B channels
        if source_std[i] > 0:
            corrected_lab[:,:,i] = (corrected_lab[:,:,i] - source_mean[i]) * (target_std[i] / source_std[i]) + target_mean[i]
    
    # Clip values to valid range
    corrected_lab = np.clip(corrected_lab, 0, 255).astype(np.uint8)
    
    # Convert back to BGR
    corrected = cv2.cvtColor(corrected_lab, cv2.COLOR_LAB2BGR)
    return corrected

def blend_edges(face, target, blend_width=5):
    """Blend the edges of the face to avoid hard borders."""
    mask = np.ones_like(face, dtype=np.float32)
    h, w = face.shape[:2]
    
    # Create a gradient along the edges
    for i in range(blend_width):
        alpha = i / blend_width
        # Top edge
        mask[i, :] = alpha
        # Bottom edge
        mask[h-i-1, :] = alpha
        # Left edge
        mask[:, i] = alpha
        # Right edge
        mask[:, w-i-1] = alpha
    
    # Apply the mask
    blended = face.astype(np.float32) * mask + target.astype(np.float32) * (1 - mask)
    return blended.astype(np.uint8)

def combine_videos(original_video, face_video, output_video, audio_path=None, face_coordinates=None, 
                   apply_color_correction=True, blend_edges_width=5):
    """
    Combine the lip-synced face region back into the original video.
    
    Args:
        original_video: Path to the original full-size video
        face_video: Path to the lip-synced face video
        output_video: Path for the output combined video
        audio_path: Path to the audio file to use (if None, uses original video audio)
        face_coordinates: Path to file containing face coordinates or a tuple of (x, y, w, h)
        apply_color_correction: Whether to apply color correction
        blend_edges_width: Width in pixels for edge blending (0 to disable)
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
    
    # Initialize color transfer reference
    color_reference = None
    
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
        
        if apply_color_correction:
            # Extract the corresponding region from the original frame to use as reference
            original_face_region = original_frame[y:y+h, x:x+w]
            
            # Perform color correction to match original video colors
            corrected_face = color_correct_image(face_frame, original_face_region)
            
            # If edge blending is enabled
            if blend_edges_width > 0:
                corrected_face = blend_edges(corrected_face, original_face_region, blend_edges_width)
                
            # Replace face region with color-corrected version
            original_frame[y:y+h, x:x+w] = corrected_face
        else:
            # Direct replacement without color correction
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
    parser.add_argument('--no_color_correction', action='store_true', help='Disable color correction')
    parser.add_argument('--blend_width', type=int, default=5, help='Width of edge blending in pixels (0 to disable)')
    
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
            args.face_coordinates if args.face_coordinates else face_region,
            not args.no_color_correction,
            args.blend_width
        )
        return 0 if success else 1
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())