"""
Translate SRT file from English to German using the srt library and deep_translator.
"""

import argparse
import srt
import os
import time
from deep_translator import GoogleTranslator

def translate_srt_file(input_path, output_path, source_lang="en", target_lang="de"):
    """Translate SRT file from English to German using Google Translate via deep_translator."""
    try:
        # Create translator
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        
        # Parse SRT file
        with open(input_path, 'r', encoding='utf-8') as f:
            subtitle_generator = srt.parse(f.read())
            subtitles = list(subtitle_generator)
        
        total_subs = len(subtitles)
        print(f"Found {total_subs} subtitles to translate")
        
        # Translate each subtitle content
        for i, subtitle in enumerate(subtitles):
            print(f"Translating subtitle {i+1}/{total_subs}...", end='\r')
            
            # Skip empty subtitles
            if not subtitle.content.strip():
                continue
                
            # Translate text (with retry mechanism)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    translated_text = translator.translate(subtitle.content)
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
            f.write(srt.compose(subtitles))
        
        print(f"Translated SRT saved to {output_path}")
        return True
        
    except Exception as e:
        print(f"Error translating SRT file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Translate SRT file from English to German using Google Translate.')
    parser.add_argument('input_srt', help='Path to input SRT file')
    parser.add_argument('output_srt', help='Path for output translated SRT file')
    parser.add_argument('--source', default='en', help='Source language (default: en)')
    parser.add_argument('--target', default='de', help='Target language (default: de)')
    
    args = parser.parse_args()
    
    success = translate_srt_file(args.input_srt, args.output_srt, args.source, args.target)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())