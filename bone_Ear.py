#This File contain speech intake function just like our Ears its only task is to intake the voice convert to text and return to requested files
# pyrefly: ignore [missing-import]
import speech_recognition as sr

# Single global recognizer to persist calibration and pause thresholds
r = sr.Recognizer()
# Set a very comfortable pause threshold (2.5 seconds gives you plenty of time to pause and think)
r.pause_threshold = 2.5

# Tracking flag for one-time microphone calibration
_is_calibrated = False

def voice_to_text():
    global _is_calibrated
    
    with sr.Microphone() as source:
        # Calibrate energy threshold ONLY ONCE on startup
        # This prevents your voice from being accidentally calibrated as background noise!
        if not _is_calibrated:
            print("Calibrating microphone for ambient noise... Please stay silent for 1 second.")
            r.adjust_for_ambient_noise(source, duration=1)
            _is_calibrated = True
            print("Calibration complete! Bone is listening.")
            
        print("Listening...")
        try:
            # Infinite phrase limit for large/short sentences, with 10s wait timeout
            audio = r.listen(source, timeout=10, phrase_time_limit=None)
        except sr.WaitTimeoutError:
            print("Listening timed out (no speech detected).")
            return ""
        
        try:
            print("Transcribing locally...")
            # Use Vosk offline speech recognition (looks for "model" folder or system default)
            text = r.recognize_vosk(audio)
            return text.lower()
        except sr.UnknownValueError:
            return "Could not understand audio"
        except sr.RequestError as e:
            return f"Vosk error: {str(e)}"
        except Exception as e:
            return f"Local transcription failed: {str(e)}"

# Test the function
# if __name__ == "__main__":
#     print("Speak now:")
#     result = voice_to_text()
#     print(f"You said: {result}")
