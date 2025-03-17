#!/bin/bash

# Create output directory for all generated files
OUTPUT_DIR="output"
mkdir -p $OUTPUT_DIR

# Extract audio from original video
python extract_audio.py Tanzania-2.mp4 $OUTPUT_DIR/original_audio.wav

# Translate subtitles from English to German
python translate_subtitles.py Tanzania-caption.srt $OUTPUT_DIR/translated-caption.srt

# Generate German audio with voice cloning
python generate_audio.py $OUTPUT_DIR/original_audio.wav $OUTPUT_DIR/translated-caption.srt $OUTPUT_DIR/translated_audio.wav --temp_dir $OUTPUT_DIR/audio_segments

# Sync video timing with the new audio
python sync_video.py Tanzania-2.mp4 $OUTPUT_DIR/translated_audio.wav $OUTPUT_DIR/translated_audio_timings.json $OUTPUT_DIR/translated_video.mp4

# Extract face region from video
python extract_face.py $OUTPUT_DIR/translated_video.mp4 $OUTPUT_DIR/face_video.mp4 --coordinates_file $OUTPUT_DIR/face_coordinates.txt

# Apply lip sync to the face video
python lip_sync.py $OUTPUT_DIR/face_video.mp4 $OUTPUT_DIR/translated_audio.wav $OUTPUT_DIR/lip_synced_face.mp4

# Combine lip-synced face back into the full video
python combine_video.py $OUTPUT_DIR/translated_video.mp4 $OUTPUT_DIR/lip_synced_face.mp4 $OUTPUT_DIR/final_video.mp4 --audio $OUTPUT_DIR/translated_audio.wav --face_coordinates $OUTPUT_DIR/face_coordinates.txt