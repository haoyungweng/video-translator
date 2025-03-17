"""
Generate German audio from translated SRT file using XTTS-v2 for voice cloning.
This improved version creates individual audio segments that are concatenated
in the order of the subtitles, without time gaps or overlaps.
"""

import argparse
import os
import sys
import torch
import srt
from datetime import timedelta
from tqdm import tqdm
from pydub import AudioSegment
import subprocess
import json

# For PyTorch 2.6+, monkey patch the torch.load function to use weights_only=False
original_torch_load = torch.load
def patched_torch_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return original_torch_load(*args, **kwargs)

torch.load = patched_torch_load

# Set environment variable to allow old-style loading
os.environ["TORCH_LOAD_LEGACY_MODULES"] = "1"

def generate_german_audio(srt_path, speaker_wav, output_path, temp_dir="audio_segments", 
                         timing_file=None, generate_timings=True):
    """Generate German audio using XTTS-v2 voice cloning and create a continuous audio file."""
    try:
        # Import TTS
        from TTS.api import TTS
        
        # Create temporary directory
        os.makedirs(temp_dir, exist_ok=True)
        
        # Set up the TTS system
        print("Loading XTTS-v2 model (this may take a minute)...")
        
        # Determine GPU availability automatically
        use_gpu = torch.cuda.is_available()
        use_mps = not use_gpu and torch.backends.mps.is_available()
        
        if use_gpu:
            print("CUDA GPU detected - using for faster processing")
            device = torch.device("cuda")
        elif use_mps:
            print("Apple Silicon (MPS) detected - using CPU since XTTS doesn't directly support MPS")
            device = torch.device("cpu")
            use_gpu = False
        else:
            print("No GPU detected - using CPU")
            device = torch.device("cpu")
            use_gpu = False
        
        # Add safe globals for PyTorch 2.6+ if possible
        if hasattr(torch.serialization, 'add_safe_globals'):
            try:
                from TTS.tts.configs.xtts_config import XttsConfig
                torch.serialization.add_safe_globals([XttsConfig])
            except Exception as e:
                print(f"Note: Could not add safe globals: {e}")
                pass
        
        # Load the XTTS model using the API
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        tts.to(device)
        
        # Parse SRT file
        print("Parsing SRT file...")
        with open(srt_path, 'r', encoding='utf-8') as f:
            subtitles = list(srt.parse(f.read()))
        
        # Process each subtitle - generate audio segments sequentially
        print(f"Generating audio for {len(subtitles)} segments...")
        
        # Dictionary to store timing information for each segment
        timing_data = []
        
        # Create a blank audio to start with
        full_audio = AudioSegment.silent(duration=100)  # Just a tiny initial silence
        current_position = 0  # Track position in milliseconds
        
        for i, subtitle in tqdm(enumerate(subtitles), total=len(subtitles)):
            if not subtitle.content.strip():
                continue  # Skip empty subtitles
                
            # Generate audio for this subtitle
            segment_path = os.path.join(temp_dir, f"segment_{i:04d}.wav")
            
            try:
                # Generate audio with voice cloning
                tts.tts_to_file(
                    text=subtitle.content,
                    file_path=segment_path,
                    speaker_wav=speaker_wav,
                    language="de",  # German
                    split_sentences=False  # Keep as one unit for better coherence
                )
                
                # Get the generated audio segment
                if os.path.exists(segment_path):
                    segment_audio = AudioSegment.from_wav(segment_path)
                    
                    # Calculate segment duration
                    segment_duration = len(segment_audio)
                    
                    # Store timing information
                    timing_data.append({
                        "index": i,
                        "subtitle_start": subtitle.start.total_seconds(),
                        "subtitle_end": subtitle.end.total_seconds(),
                        "subtitle_duration": (subtitle.end - subtitle.start).total_seconds(),
                        "audio_start": current_position / 1000,  # Convert ms to seconds
                        "audio_end": (current_position + segment_duration) / 1000,  # Convert ms to seconds
                        "audio_duration": segment_duration / 1000,  # Convert ms to seconds
                        "content": subtitle.content
                    })
                    
                    # Append to the full audio
                    full_audio = full_audio + segment_audio
                    
                    # Update position for next segment
                    current_position += segment_duration
                    
            except Exception as e:
                print(f"Error generating audio for segment {i}: {e}")
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Save the final merged audio
        print(f"Saving final audio to {output_path}...")
        full_audio.export(output_path, format="wav")
        
        # If timing_file is provided, use it; otherwise, use default path
        if timing_file is None and generate_timings:
            timing_file = os.path.splitext(output_path)[0] + "_timings.json"
        
        # If requested, save timing information to JSON file
        if generate_timings and timing_file:
            # Create timing file directory if it doesn't exist
            timing_dir = os.path.dirname(timing_file)
            if timing_dir and not os.path.exists(timing_dir):
                os.makedirs(timing_dir)
                
            with open(timing_file, 'w', encoding='utf-8') as f:
                json.dump(timing_data, f, indent=2)
            print(f"Timing information saved to {timing_file}")
        
        return output_path
        
    except ImportError:
        print("TTS not installed. Installing required packages...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "TTS"])
        
        # Try again after installation
        from TTS.api import TTS
        return generate_german_audio(srt_path, speaker_wav, output_path, temp_dir, timing_file)

def main():
    parser = argparse.ArgumentParser(description='Generate German audio from SRT using XTTS-v2 voice cloning')
    parser.add_argument('speaker_wav', help='Path to the original speaker WAV file')
    parser.add_argument('translated_srt', help='Path to the translated German SRT file')
    parser.add_argument('output_audio', help='Path for the output German audio file')
    parser.add_argument('--timing_file', help='Path for the timing JSON file')
    parser.add_argument('--temp_dir', default='audio_segments', help='Directory for temporary audio segments')
    parser.add_argument('--no-timings', action='store_true', help="Don't generate timing JSON file")
    
    args = parser.parse_args()
    
    try:
        # Generate German audio with voice cloning
        generate_german_audio(
            args.translated_srt,
            args.speaker_wav,
            args.output_audio, 
            args.temp_dir,
            args.timing_file,
            not args.no_timings
        )
        
        print(f"German audio successfully generated at {args.output_audio}")
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())