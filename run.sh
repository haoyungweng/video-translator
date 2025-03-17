#!/bin/bash

# Create output directory for all generated files
mkdir -p out

# Translate subtitles from English to German
python translate_subtitles.py Tanzania-caption.srt out/translated-caption.srt

# Extract audio from original video
python extract_audio.py Tanzania-2.mp4 out/original_audio.wav

# Generate German audio with voice cloning
export COQUI_TOS_AGREED=1
python generate_audio.py out/original_audio.wav out/translated-caption.srt out/translated_audio.wav --temp_dir out/audio_segments --gpu

# Sync video timing with the new audio
python sync_video.py Tanzania-2.mp4 out/translated_audio.wav out/translated_audio_timings.json out/translated_video.mp4

# Extract face region from video
python extract_face.py out/translated_video.mp4 out/face_video.mp4 --coordinates_file out/face_coordinates.txt

# Apply lip sync to the face video
python lip_sync.py out/face_video.mp4 out/translated_audio.wav out/lip_synced_face.mp4

# Combine lip-synced face back into the full video
python combine_video.py out/translated_video.mp4 out/lip_synced_face.mp4 out/final_video.mp4 --audio out/translated_audio.wav --face_coordinates out/face_coordinates.txt