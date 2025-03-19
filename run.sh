#!/bin/bash

# Default values
VIDEO_FILE="Tanzania.mp4"
SUBTITLE_FILE="Tanzania-caption.srt"
OUTPUT_DIR="out"

# Show usage information
function show_usage {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -v, --video FILE       Input video file (default: $VIDEO_FILE)"
    echo "  -s, --subtitles FILE   Input subtitles file (default: $SUBTITLE_FILE)"
    echo "  -o, --output DIR       Output directory (default: $OUTPUT_DIR)"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Example: $0 --video my_video.mp4 --subtitles my_subtitles.srt"
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -v|--video)
            VIDEO_FILE="$2"
            shift 2
            ;;
        -s|--subtitles)
            SUBTITLE_FILE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if input files exist
if [ ! -f "$VIDEO_FILE" ]; then
    echo "Error: Video file '$VIDEO_FILE' not found."
    exit 1
fi

if [ ! -f "$SUBTITLE_FILE" ]; then
    echo "Error: Subtitle file '$SUBTITLE_FILE' not found."
    exit 1
fi

# Extract file names without extensions for use in output paths
VIDEO_NAME=$(basename "$VIDEO_FILE" | sed 's/\.[^.]*$//')
SUBTITLE_NAME=$(basename "$SUBTITLE_FILE" | sed 's/\.[^.]*$//')

echo "Starting video translation pipeline..."
echo "Input video: $VIDEO_FILE"
echo "Input subtitles: $SUBTITLE_FILE"
echo "Output directory: $OUTPUT_DIR"

# Create output directory for all generated files
mkdir -p "$OUTPUT_DIR"

# Translate subtitles from English to German
echo -e "\n1. Translating subtitles..."
python translate_subtitles.py "$SUBTITLE_FILE" "$OUTPUT_DIR/translated_${SUBTITLE_NAME}.srt"

# Extract audio from original video
echo -e "\n2. Extracting audio..."
python extract_audio.py "$VIDEO_FILE" "$OUTPUT_DIR/original_audio.wav"

# Generate German audio with voice cloning
echo -e "\n3. Generating German audio with voice cloning..."
export COQUI_TOS_AGREED=1
python generate_audio.py "$OUTPUT_DIR/original_audio.wav" "$OUTPUT_DIR/translated_${SUBTITLE_NAME}.srt" "$OUTPUT_DIR/translated_audio.wav" --temp_dir "$OUTPUT_DIR/audio_segments"

# Sync video timing with the new audio
echo -e "\n4. Synchronizing video timing..."
python sync_video.py "$VIDEO_FILE" "$OUTPUT_DIR/translated_audio.wav" "$OUTPUT_DIR/translated_audio_timings.json" "$OUTPUT_DIR/translated_${VIDEO_NAME}.mp4"

# Extract face region from video
echo -e "\n5. Extracting face region..."
python extract_face.py "$OUTPUT_DIR/translated_${VIDEO_NAME}.mp4" "$OUTPUT_DIR/face_video.mp4" --coordinates_file "$OUTPUT_DIR/face_coordinates.txt"

# Apply lip sync to the face video
echo -e "\n6. Applying lip sync to face..."
python lip_sync.py "$OUTPUT_DIR/face_video.mp4" "$OUTPUT_DIR/translated_audio.wav" "$OUTPUT_DIR/lip_synced_face.mp4"

# Combine lip-synced face back into the full video
echo -e "\n7. Combining final video..."
python combine_video.py "$OUTPUT_DIR/translated_${VIDEO_NAME}.mp4" "$OUTPUT_DIR/lip_synced_face.mp4" "$OUTPUT_DIR/final_${VIDEO_NAME}.mp4" --audio "$OUTPUT_DIR/translated_audio.wav" --face_coordinates "$OUTPUT_DIR/face_coordinates.txt" --blend_width 5

echo -e "\nVideo translation completed successfully!"
echo "Final output: $OUTPUT_DIR/final_${VIDEO_NAME}.mp4"