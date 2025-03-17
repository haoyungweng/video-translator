#!/usr/bin/env python3
"""
Simplified approach to lip syncing that works around Wav2Lip limitations.
"""

import argparse
import os
import sys
import subprocess
import tempfile
import shutil

def setup_wav2lip():
    """Set up Wav2Lip if not already installed."""
    if not os.path.exists("Wav2Lip"):
        print("Setting up Wav2Lip...")
        subprocess.run(["git", "clone", "https://github.com/Rudrabha/Wav2Lip.git"], check=True)
        
        # Create checkpoints directory
        os.makedirs("Wav2Lip/checkpoints", exist_ok=True)
        
        # Download the model file
        model_path = "Wav2Lip/checkpoints/wav2lip_gan.pth"
        if not os.path.exists(model_path):
            print("Downloading pre-trained model...")
            import requests
            from tqdm import tqdm
            
            url = "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth"
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            with open(model_path, 'wb') as f:
                if total_size > 0:
                    with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                else:
                    f.write(response.content)
        
        # Install dependencies
        subprocess.run([sys.executable, "-m", "pip", "install", 
                        "librosa==0.8.0", "opencv-python", "mediapipe", 
                        "numpy==1.23.5", "requests", "tqdm"], check=True)
    
    return True

def extract_audio(video_path, audio_path):
    """Extract audio from video using ffmpeg."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        audio_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return audio_path

def run_lip_sync(face_video, audio_path, output_path):
    """Run Wav2Lip on a face-only video."""
    # Copy files to Wav2Lip directory
    wav2lip_face = "Wav2Lip/temp_face.mp4"
    wav2lip_audio = "Wav2Lip/temp_audio.wav"
    wav2lip_output = "Wav2Lip/temp_output.mp4"
    
    # Make sure temp directory exists
    os.makedirs("Wav2Lip/temp", exist_ok=True)
    
    # Verify model exists
    model_path = os.path.abspath("Wav2Lip/checkpoints/wav2lip_gan.pth")
    if not os.path.exists(model_path):
        print(f"Model file not found at {model_path}")
        print("Checking if it exists at an alternative location...")
        
        # Check if it might be in the current directory
        alt_path = os.path.abspath("checkpoints/wav2lip_gan.pth")
        if os.path.exists(alt_path):
            model_path = alt_path
            print(f"Found model at {alt_path}")
        else:
            print("Model file not found. Please ensure it has been downloaded.")
            return False
    
    # Copy input files
    shutil.copy2(face_video, wav2lip_face)
    shutil.copy2(audio_path, wav2lip_audio)
    
    # Change to Wav2Lip directory
    original_dir = os.getcwd()
    os.chdir("Wav2Lip")
    
    try:
        # Fix audio.py file if needed
        fix_audio_py_file()
        
        # Verify checkpoints directory exists
        os.makedirs("checkpoints", exist_ok=True)
        
        # Ensure model is in the right place
        if not os.path.exists("checkpoints/wav2lip_gan.pth"):
            # If model is elsewhere, copy it to the expected location
            if os.path.exists(model_path):
                shutil.copy2(model_path, "checkpoints/wav2lip_gan.pth")
            else:
                # Try downloading it again
                print("Downloading model file...")
                import requests
                from tqdm import tqdm
                
                url = "https://github.com/Rudrabha/Wav2Lip/releases/download/v1.0/wav2lip_gan.pth"
                response = requests.get(url, stream=True)
                
                with open("checkpoints/wav2lip_gan.pth", 'wb') as f:
                    total_size = int(response.headers.get('content-length', 0))
                    with tqdm(total=total_size, unit='B', unit_scale=True) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
        
        # Run Wav2Lip with minimal parameters and small batch sizes
        cmd = [
            "python", "inference.py",
            "--checkpoint_path", "checkpoints/wav2lip_gan.pth",
            "--face", "temp_face.mp4",
            "--audio", "temp_audio.wav",
            "--outfile", "temp_output.mp4",
            "--wav2lip_batch_size", "4",
            "--face_det_batch_size", "1",
            # "--nosmooth"  # Disable smoothing for better results
        ]
        
        print("Running Wav2Lip...")
        print(f"Command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Wav2Lip error:")
            print(result.stderr)
            return False
        
        # Copy output back
        if os.path.exists("temp_output.mp4"):
            shutil.copy2("temp_output.mp4", os.path.join(original_dir, output_path))
            print(f"Lip-synced video saved to {output_path}")
            return True
        else:
            print("Error: Output file was not created")
            return False
            
    finally:
        os.chdir(original_dir)
        
        # Clean up
        for file in [wav2lip_face, wav2lip_audio, wav2lip_output]:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    pass

def fix_audio_py_file():
    """Fix audio.py file for compatibility with newer librosa versions."""
    audio_py_path = "audio.py"
    
    # Read the file
    with open(audio_py_path, 'r') as f:
        content = f.read()
    
    # Check if the file needs to be fixed
    if "return librosa.filters.mel(hp.sample_rate, hp.n_fft, n_mels=hp.num_mels," in content:
        print("Fixing audio.py file for compatibility...")
        
        # Replace the problematic line
        content = content.replace(
            "return librosa.filters.mel(hp.sample_rate, hp.n_fft, n_mels=hp.num_mels,",
            "return librosa.filters.mel(sr=hp.sample_rate, n_fft=hp.n_fft, n_mels=hp.num_mels,"
        )
        
        # Write the fixed content back
        with open(audio_py_path, 'w') as f:
            f.write(content)
        
        print("Fixed audio.py file successfully")

def main():
    parser = argparse.ArgumentParser(description='Simple approach to lip syncing')
    parser.add_argument('face_video', help='Path to video containing only the face region')
    parser.add_argument('audio_file', help='Path to the audio file for lip syncing')
    parser.add_argument('output_video', help='Path for the output lip-synced video')
    
    args = parser.parse_args()
    
    try:
        # Set up Wav2Lip
        setup_wav2lip()
        
        # Run lip sync
        success = run_lip_sync(args.face_video, args.audio_file, args.output_video)
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())