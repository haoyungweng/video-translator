"""
Translate SRT file from English to German using the srt library and deep_translator.
Includes text preprocessing to improve TTS quality and combines short subtitles.
"""

import argparse
import srt
import os
import time
import re
from deep_translator import GoogleTranslator
from datetime import timedelta

def preprocess_text_for_tts(text):
    """
    Preprocess text to make it more TTS-friendly.
    
    Args:
        text: The input text
        
    Returns:
        Preprocessed text optimized for TTS
    """
    # Replace em dashes with colons or spaces depending on context
    processed = text.replace(' - ', ': ')  # Replace em dash with colon when surrounded by spaces
    processed = processed.replace('- ', ': ')  # Replace em dash with colon at start of words

    # Handle common patterns in German translations
    processed = processed.replace(' -', ' ')  # Remove space-dash pattern like "Serengeti -Nationalpark"
    
    # Handle other dashes and hyphens
    processed = processed.replace('—', ': ')  # Replace true em dash with colon and space
    processed = processed.replace('–', ': ')  # Replace en dash with colon and space
    
    # Fix spaces
    processed = re.sub(r'\s+', ' ', processed)  # Replace multiple spaces with a single space
    processed = processed.strip()
    
    # Fix common punctuation issues
    processed = processed.replace(' ,', ',')  # Remove space before comma
    processed = processed.replace(' .', '.')  # Remove space before period
    processed = processed.replace(' :', ':')  # Remove space before colon
    processed = processed.replace(' ;', ';')  # Remove space before semicolon
    
    return processed

def count_words(text):
    """Count the number of words in a text string."""
    # Remove newlines and split by whitespace
    return len(re.sub(r'\s+', ' ', text).strip().split())

def combine_short_subtitles(subtitles, min_word_count=7):
    """
    Combine short subtitles with the previous subtitle.
    
    Args:
        subtitles: List of srt.Subtitle objects
        min_word_count: Minimum word count to keep subtitle separate
        
    Returns:
        List of processed srt.Subtitle objects
    """
    if not subtitles:
        return []
    
    combined_subtitles = []
    current_subtitle = subtitles[0]
    
    for i in range(1, len(subtitles)):
        next_subtitle = subtitles[i]
        
        # Count words in the next subtitle
        word_count = count_words(next_subtitle.content)
        
        # If the next subtitle is short, combine it with the current one
        if word_count < min_word_count:
            # Check if subtitles are adjacent or close enough
            time_gap = next_subtitle.start - current_subtitle.end
            if time_gap <= timedelta(seconds=2):
                # Combine content
                combined_content = current_subtitle.content
                # Add a space if there's no ending punctuation
                if not combined_content.strip().endswith(('.', '!', '?', ':', ';')):
                    combined_content += ' '
                combined_content += next_subtitle.content
                
                # Update current subtitle
                current_subtitle = srt.Subtitle(
                    index=current_subtitle.index,
                    start=current_subtitle.start,
                    end=next_subtitle.end,  # Extend end time to the end of the next subtitle
                    content=combined_content
                )
            else:
                # If the gap is too large, add current to result and start with next
                combined_subtitles.append(current_subtitle)
                current_subtitle = next_subtitle
        else:
            # If the next subtitle is not short, add current to result and start with next
            combined_subtitles.append(current_subtitle)
            current_subtitle = next_subtitle
    
    # Add the last subtitle
    combined_subtitles.append(current_subtitle)
    
    # Re-number subtitles
    for i, subtitle in enumerate(combined_subtitles):
        combined_subtitles[i] = srt.Subtitle(
            index=i+1,
            start=subtitle.start,
            end=subtitle.end,
            content=subtitle.content
        )
    
    return combined_subtitles

def translate_srt_file(input_path, output_path, source_lang="en", target_lang="de", min_word_count=7):
    """Translate SRT file from English to German using Google Translate via deep_translator."""
    try:
        # Create translator
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        
        # Parse SRT file
        with open(input_path, 'r', encoding='utf-8') as f:
            subtitle_generator = srt.parse(f.read())
            subtitles = list(subtitle_generator)
        
        total_subs = len(subtitles)
        print(f"Found {total_subs} subtitles in the original file")
        
        # Combine short subtitles
        processed_subtitles = combine_short_subtitles(subtitles, min_word_count)
        print(f"After combining short subtitles: {len(processed_subtitles)} subtitles")
        
        # Translate each subtitle content
        for i, subtitle in enumerate(processed_subtitles):
            print(f"Translating subtitle {i+1}/{len(processed_subtitles)}...", end='\r')
            
            # Skip empty subtitles
            if not subtitle.content.strip():
                continue
            
            # Pre-process the content: replace line breaks with spaces
            # This improves translation quality and prevents unwanted line breaks
            original_content = subtitle.content
            processed_content = original_content.replace('\n', ' ').strip()
            
            # Translate text (with retry mechanism)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    translated_text = translator.translate(processed_content)
                    
                    # Further post-process translated text to improve TTS quality
                    translated_text = preprocess_text_for_tts(translated_text)
                    
                    subtitle.content = translated_text
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(1)  # Wait before retrying
                    else:
                        print(f"\nWarning: Failed to translate subtitle {i+1}: {e}")
                        # Keep original text if translation fails
        
        print("\nTranslation completed.")
        
        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Write translated SRT
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(srt.compose(processed_subtitles))
        
        print(f"Translated and preprocessed SRT saved to {output_path}")
        return True
        
    except Exception as e:
        print(f"Error translating SRT file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Translate SRT file from English to German and preprocess for TTS.')
    parser.add_argument('input_srt', help='Path to input SRT file')
    parser.add_argument('output_srt', help='Path for output translated SRT file')
    parser.add_argument('--source', default='en', help='Source language (default: en)')
    parser.add_argument('--target', default='de', help='Target language (default: de)')
    parser.add_argument('--min-words', type=int, default=7, 
                       help='Minimum number of words to keep subtitle separate (default: 7)')
    
    args = parser.parse_args()
    
    success = translate_srt_file(args.input_srt, args.output_srt, 
                                args.source, args.target, args.min_words)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())