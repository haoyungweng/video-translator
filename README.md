# Video Translator

A pipeline for translating videos from English to German with lip synchronization.

## Requirements

- Python 3.11
- Conda
- FFmpeg (installed and available in PATH)

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

# Set up Wav2Lip
git clone https://github.com/Rudrabha/Wav2Lip.git

# Download the Wav2Lip model checkpoint from OneDrive
# Visit this URL and download the model manually:
# https://iiitaphyd-my.sharepoint.com/personal/radrabha_m_research_iiit_ac_in/_layouts/15/embed.aspx?UniqueId=b6edc8d8-8065-4c0a-aac5-68114517a4bb
# Then place the downloaded file in Wav2Lip/checkpoints/wav2lip_gan.pth
```

## Usage

### Basic Usage

1. Run with default input files:
   ```bash
   ./run.sh
   ```

2. Specify custom input files:
   ```bash
   ./run.sh --video my_video.mp4 --subtitles my_subtitles.srt
   ```

3. All available options:
   ```bash
   ./run.sh --help
   ```

4. Output files:
   - Final video with lip-sync: `$OUTPUT_DIR/final_${VIDEO_NAME}.mp4`
   - Translated video without lip-sync: `$OUTPUT_DIR/translated_${VIDEO_NAME}.mp4`

### Pipeline Steps

The workflow consists of these sequential steps:

1. **Translate Subtitles**: `translate_subtitles.py` - Convert English SRT to German
2. **Extract Audio**: `extract_audio.py` - Extract audio from original video
3. **Generate Audio**: `generate_audio.py` - Create German speech with voice cloning
4. **Sync Video**: `sync_video.py` - Adjust video timing to match German audio (creates `translated_${VIDEO_NAME}.mp4`)
5. **Extract Face**: `extract_face.py` - Isolate face region from video
6. **Lip Sync**: `lip_sync.py` - Synchronize lip movements with German audio
7. **Combine Video**: `combine_video.py` - Merge lip-synced face into full video (creates `final_${VIDEO_NAME}.mp4`)

### Custom Usage

Run each step individually for more control:

```bash
# Example of running individual steps
python translate_subtitles.py input_subtitles.srt output/translated_subtitles.srt
python extract_audio.py input_video.mp4 output/original_audio.wav
python generate_audio.py output/original_audio.wav output/translated_subtitles.srt output/translated_audio.wav
python sync_video.py input_video.mp4 output/translated_audio.wav output/translated_audio_timings.json output/translated_video.mp4
python extract_face.py output/translated_video.mp4 output/face_video.mp4
python lip_sync.py output/face_video.mp4 output/translated_audio.wav output/lip_synced_face.mp4
python combine_video.py output/translated_video.mp4 output/lip_synced_face.mp4 output/final_video.mp4 --audio output/translated_audio.wav
```

## Output Files

The pipeline generates several output files in the specified output directory:

- **Final video with lip-sync**: `final_${VIDEO_NAME}.mp4` - This is the complete translated video with synchronized lip movements
- **Translated video without lip-sync**: `translated_${VIDEO_NAME}.mp4` - This is the intermediate result after step 4, with the German audio but before lip synchronization
- **Timing file**: `translated_audio_timings.json` - Contains timing information for synchronizing the video and audio
- **Face coordinates**: `face_coordinates.txt` - Stores the detected face region coordinates

If you need just the translated video without lip synchronization (which is faster to generate), you can stop the pipeline after step 4.

**Note about video timing:** The pipeline adjusts the speed of video segments to match the duration of the translated audio. German sentences are often longer than their English equivalents, which may result in slowed-down video sections. This is normal and necessary to maintain synchronization between the video and the translated audio.