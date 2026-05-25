import os
import re
import urllib.request
import tempfile
import soundfile as sf
import numpy as np
from kokoro_onnx import Kokoro

# Global cache for the Kokoro model instance
_kokoro_instance = None

def download_file(url, dest_path):
    """Downloads a file with a progress indicator."""
    print(f"\nDownloading {os.path.basename(dest_path)} from GitHub releases...")
    print("This is a one-time setup for the high-quality local voice engine. Please wait...")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    req = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
        total_size = int(response.getheader('Content-Length', 0))
        block_size = 1024 * 1024  # 1 MB blocks
        downloaded = 0
        
        while True:
            buffer = response.read(block_size)
            if not buffer:
                break
            downloaded += len(buffer)
            out_file.write(buffer)
            if total_size > 0:
                percent = min(100, int(downloaded * 100 / total_size))
                print(f"Downloaded: {downloaded / (1024 * 1024):.1f}MB / {total_size / (1024 * 1024):.1f}MB ({percent}%)", end="\r", flush=True)
                
    print(f"\nSuccessfully downloaded and set up {os.path.basename(dest_path)}!")

def get_kokoro():
    """Lazily loads and initializes the Kokoro engine, downloading models if needed."""
    global _kokoro_instance
    if _kokoro_instance is None:
        # Save model and voice binary in the same directory as this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, "kokoro-v1.0.onnx")
        voices_path = os.path.join(current_dir, "voices-v1.0.bin")
        
        # Auto-download ONNX model if missing or corrupted (size < 100MB)
        if not os.path.exists(model_path) or os.path.getsize(model_path) < 100 * 1024 * 1024:
            if os.path.exists(model_path):
                print(f"\nDetecting corrupted model file (size {os.path.getsize(model_path)/(1024*1024):.1f}MB < 100MB). Deleting and re-downloading...")
                try:
                    os.remove(model_path)
                except Exception:
                    pass
            url = "https://huggingface.co/fastrtc/kokoro-onnx/resolve/main/kokoro-v1.0.onnx"
            download_file(url, model_path)
            
        # Auto-download voice database if missing or corrupted (size < 15MB)
        if not os.path.exists(voices_path) or os.path.getsize(voices_path) < 15 * 1024 * 1024:
            if os.path.exists(voices_path):
                print(f"\nDetecting corrupted voices file (size {os.path.getsize(voices_path)/(1024*1024):.1f}MB < 15MB). Deleting and re-downloading...")
                try:
                    os.remove(voices_path)
                except Exception:
                    pass
            url = "https://huggingface.co/fastrtc/kokoro-onnx/resolve/main/voices-v1.0.bin"
            download_file(url, voices_path)
            
        print("\nLoading local Kokoro neural voice engine into memory...")
        _kokoro_instance = Kokoro(model_path, voices_path)
        print("Kokoro neural voice engine loaded successfully!")
        
    return _kokoro_instance

def speak(text, interrupt_event=None):
    """Synthesizes text to a highly realistic neural human voice and plays it.
    Returns the exact string that was successfully spoken before any interruption.
    """
    if not text.strip():
        return ""
        
    spoken_text = []
    try:
        # Lazily load/get the Kokoro model
        kokoro = get_kokoro()
        
        # Split text into sentences to prevent hitting Kokoro's 510 phoneme limit
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]
        
        import winsound
        import time
        
        for i, sentence in enumerate(sentences):
            # Check for early GUI interruption before starting synthesis
            if interrupt_event and interrupt_event.is_set():
                raise KeyboardInterrupt(" ".join(spoken_text))
                
            # Strip markdown stars, hashes, etc.
            cleaned_sentence = re.sub(r'[*_`#~]', '', sentence).strip()
            if not cleaned_sentence:
                continue
                
            # Synthesize single sentence (extremely fast)
            samples, sample_rate = kokoro.create(
                cleaned_sentence, 
                voice="af_sarah", 
                speed=1.0, 
                lang="en-us"
            )
            
            # Save output temporarily to user temp directory
            temp_wav = os.path.join(tempfile.gettempdir(), f"bone_speech_temp.wav")
            sf.write(temp_wav, samples, sample_rate)
            
            # Calculate duration in seconds
            duration = len(samples) / sample_rate
            
            # Play the audio using native Windows winsound in background (async)
            winsound.PlaySound(temp_wav, winsound.SND_FILENAME | winsound.SND_ASYNC)
            
            # Sleep in tiny chunks to allow Python or GUI to process interrupts instantly!
            start_time = time.time()
            try:
                while time.time() - start_time < duration:
                    if interrupt_event and interrupt_event.is_set():
                        raise KeyboardInterrupt()
                    time.sleep(0.05)
                # Add a brief pause between sentences for natural phrasing
                start_pause = time.time()
                while time.time() - start_pause < 0.15:
                    if interrupt_event and interrupt_event.is_set():
                        raise KeyboardInterrupt()
                    time.sleep(0.05)
                # Mark as successfully spoken
                spoken_text.append(sentence)
            except KeyboardInterrupt:
                # Stop the background audio playback immediately!
                winsound.PlaySound(None, winsound.SND_PURGE)
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
                # Raise exception with what we managed to say so far
                raise KeyboardInterrupt(" ".join(spoken_text))
                
            # Clean up the temporary audio file
            try:
                os.remove(temp_wav)
            except Exception:
                pass
                
        return " ".join(spoken_text)
        
    except KeyboardInterrupt:
        # Re-raise KeyboardInterrupt so the main loop can handle it
        raise
    except Exception as e:
        print(f"\n[Speech Engine Warning] Local neural engine failed: {e}")
        print("Falling back to standard robotic speech system...")
        
        # Fallback to basic pyttsx3 offline speech
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 190)
            engine.setProperty('volume', 1.0)
            voices = engine.getProperty('voices')
            if len(voices) > 1:
                engine.setProperty('voice', voices[1].id)

            engine.say(text)
            engine.runAndWait()
            return text
        except Exception as fallback_error:
            print(f"Robotic speech fallback also failed: {fallback_error}")
            return ""

# Quick offline speech test
if __name__ == "__main__":
    print("Testing offline Kokoro Neural Text-to-Speech...")
    speak("Hello! I am Bone, your new human like local assistant.")
