# This script will generate a sample offline Kokoro neural speech WAV file in the workspace
# so you can listen to how beautifully it speaks!

import os
import re
import numpy as np
import soundfile as sf
from bone_Mouth import get_kokoro

def create_sample_audio():
    sample_text = (
        "It seems like there's a deeper emotional resonance going on here! "
        "It can be really tough to talk about closure, especially when it comes to "
        "relationships or experiences that have had a significant impact on our lives."
    )
    
    print("Initializing Kokoro neural speech engine...")
    kokoro = get_kokoro()
    
    print("\nSplitting text into sentences...")
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', sample_text) if s.strip()]
    
    all_samples = []
    sample_rate = 24000
    
    print("Synthesizing sentences...")
    for i, sentence in enumerate(sentences):
        print(f"Synthesizing sentence {i+1}/{len(sentences)}: {sentence}")
        samples, sr = kokoro.create(
            sentence,
            voice="af_sarah",
            speed=1.0,
            lang="en-us"
        )
        sample_rate = sr
        all_samples.append(samples)
        
    print("\nConcatenating sentences with breathing pauses...")
    combined_samples = []
    silence_duration = 0.15  # seconds
    silence = np.zeros(int(sample_rate * silence_duration), dtype=np.float32)
    
    for i, samples in enumerate(all_samples):
        combined_samples.append(samples)
        if i < len(all_samples) - 1:
            combined_samples.append(silence)
            
    final_samples = np.concatenate(combined_samples)
    
    # Save the output file in the workspace directory so the user can easily open it
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(workspace_dir, "sample_bone_voice.wav")
    
    print(f"Writing audio to {output_path}...")
    sf.write(output_path, final_samples, sample_rate)
    print("\nSuccess! 'sample_bone_voice.wav' has been created in your project folder.")
    print("You can double-click and play it now to hear the new human-like neural voice!")

if __name__ == "__main__":
    create_sample_audio()
