# Video Translator

A pipeline for translating videos from English to German with lip synchronization.

## Requirements

- Python 3.11
- Conda
- FFmpeg (installed and available in PATH)
- CUDA-compatible GPU (optional but recommended)

## Installation

```bash
# Clone repository
git clone https://github.com/haoyungweng/video-translator.git
cd video-translator

# Create and activate conda environment
conda create -n heygen python=3.11
conda activate heygen

# Install dependencies
pip install -r requirements.txt

# Make scripts executable (Linux/macOS)
chmod +x *.py run.sh
```

## Usage

### Basic Usage

1. Place input video (e.g., `Tanzania-2.mp4`) and SRT file (e.g., `Tanzania-caption.srt`) in project directory
2. Run: `./run.sh`

### Pipeline Steps

The workflow consists of these sequential steps:

1. **Extract Audio**: `extract_audio.py` - Extract audio from original video
2. **Translate Subtitles**: `translate_subtitles.py` - Convert English SRT to German
3. **Generate Audio**: `generate_audio.py` - Create German speech with voice cloning
4. **Sync Video**: `sync_video.py` - Adjust video timing to match German audio
5. **Extract Face**: `extract_face.py` - Isolate face region from video
6. **Lip Sync**: `lip_sync.py` - Synchronize lip movements with German audio
7. **Combine Video**: `combine_video.py` - Merge lip-synced face into full video

### Custom Usage

Run each step individually for more control:

```bash
# Example of running individual steps
python extract_audio.py input_video.mp4 output/original_audio.wav
python translate_subtitles.py input_subtitles.srt output/translated_subtitles.srt
python generate_audio.py output/original_audio.wav output/translated_subtitles.srt output/translated_audio.wav
python sync_video.py input_video.mp4 output/translated_audio.wav output/translated_audio_timings.json output/translated_video.mp4
python extract_face.py output/translated_video.mp4 output/face_video.mp4
python lip_sync.py output/face_video.mp4 output/translated_audio.wav output/lip_synced_face.mp4
python combine_video.py output/translated_video.mp4 output/lip_synced_face.mp4 output/final_video.mp4 --audio output/translated_audio.wav
```