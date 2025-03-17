#!/usr/bin/env python3
"""
Lip syncing script using Wav2Lip.
"""

import argparse
import os
import sys
import subprocess
import tempfile
import shutil

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

def fix_audio_py_file():
    """Fix audio.py file for compatibility with newer librosa versions."""
    # Get the absolute path to the Wav2Lip directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    audio_py_path = os.path.join(script_dir, "Wav2Lip/audio.py")
    
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

def run_lip_sync(face_video, audio_path, output_path):
    """Run Wav2Lip on a face-only video."""
    # Get the absolute path to the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    wav2lip_dir = os.path.join(script_dir, "Wav2Lip")
    
    # Verify Wav2Lip directory exists
    if not os.path.exists(wav2lip_dir):
        print(f"Error: Wav2Lip directory not found at {wav2lip_dir}!")
        print("Please run: git clone https://github.com/Rudrabha/Wav2Lip.git")
        return False
    
    # Verify model checkpoint exists
    checkpoints_dir = os.path.join(wav2lip_dir, "checkpoints")
    model_path = os.path.join(checkpoints_dir, "wav2lip_gan.pth")
    if not os.path.exists(model_path):
        print(f"Error: Wav2Lip model checkpoint not found at {model_path}")
        print("Please download it from OneDrive:")
        print("https://iiitaphyd-my.sharepoint.com/personal/radrabha_m_research_iiit_ac_in/_layouts/15/onedrive.aspx?id=%2Fpersonal%2Fradrabha%5Fm%5Fresearch%5Fiiit%5Fac%5Fin%2FDocuments%2FWav2Lip%5FModels%2Fwav2lip%5Fgan%2Epth")
        print(f"Then place it in: {model_path}")
        return False
    
    # Use absolute paths for files
    wav2lip_face = os.path.join(wav2lip_dir, "temp_face.mp4")
    wav2lip_audio = os.path.join(wav2lip_dir, "temp_audio.wav")
    wav2lip_output = os.path.join(wav2lip_dir, "temp_output.mp4")
    
    # Make sure temp directory exists
    os.makedirs(os.path.join(wav2lip_dir, "temp"), exist_ok=True)
    
    # Copy input files
    shutil.copy2(face_video, wav2lip_face)
    shutil.copy2(audio_path, wav2lip_audio)
    
    # Change to Wav2Lip directory
    original_dir = os.getcwd()
    os.chdir(wav2lip_dir)
    
    try:
        # Fix audio.py file if needed
        fix_audio_py_file()
        
        # Run Wav2Lip with minimal parameters and small batch sizes
        cmd = [
            sys.executable,  # Use the current Python interpreter
            "inference.py",
            "--checkpoint_path", "checkpoints/wav2lip_gan.pth",
            "--face", "temp_face.mp4",
            "--audio", "temp_audio.wav",
            "--outfile", "temp_output.mp4",
            "--wav2lip_batch_size", "4",
            "--face_det_batch_size", "1",
            "--nosmooth"  # Disable smoothing for better results
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
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(os.path.join(original_dir, output_path))
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
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

def main():
    parser = argparse.ArgumentParser(description='Lip syncing using Wav2Lip')
    parser.add_argument('face_video', help='Path to video containing only the face region')
    parser.add_argument('audio_file', help='Path to the audio file for lip syncing')
    parser.add_argument('output_video', help='Path for the output lip-synced video')
    
    args = parser.parse_args()
    
    try:
        # Run lip sync
        success = run_lip_sync(args.face_video, args.audio_file, args.output_video)
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())