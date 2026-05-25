#This is the Main File everything is opraits frome here

#importing lisning Function
import bone_Ear
from bone_Ear import voice_to_text as Intake

#import Speaking Function
from bone_Mouth import speak

#importing filter module for removing noise from the output
import re

#this is filter for speaking only the text from the output and removing any unwanted noise
def clean_reply(text):
    # Remove all characters except letters, numbers, and spaces
    return re.sub(r"[^a-zA-Z0-9\s]", "", text)

#importing ollama for local/remote chatbot
# pyrefly: ignore [missing-import]
import ollama

# Configure Ollama Host & Model
# Set OLLAMA_HOST to None to run locally on your computer.
# Or paste your Google Colab ngrok tunnel URL to run on a free Cloud GPU!
OLLAMA_HOST = "https://bc37-34-124-205-113.ngrok-free.app"

# Select the model to use.
# - If running locally on CPU: "llama3.2" (3B, 2.0GB) is recommended.
# - If running on Google Colab GPU: "gemma2" (9B, 5.5GB) or "llama3.1" (8B, 4.7GB) are incredible and blazing fast!
OLLAMA_MODEL = "gemma2"


#import to save and load history 
import json

#this part is tosave and load the history of the conversation from a file
# Save conversation history to a file
def save_history(filename="conversation_history.json"):
    with open(filename, "w") as file:
        json.dump(conversation_history, file)

# Load conversation history from a file
def load_history(filename="conversation_history.json"):
    system_prompt = (
        "You are Bone, a futuristic, offline personal AI assistant with full local workspace control. "
        "You can execute terminal commands on the user's system to perform tasks, run code, manage files, "
        "check status, or run tests. "
        "To run a command in the background, output it EXACTLY in the format: [RUN: your command here] "
        "at the end of your response. For example: 'Sure! Let me check the directory contents. [RUN: dir]' "
        "or 'I am running the test script now. [RUN: python test.py]'. "
        "Keep command strings concise. You can chain commands using '&&' or ';'. "
        "After the command completes, the system will automatically supply you with the exit code and "
        "console output, letting you verify and explain the results to the user."
    )
    try:
        with open(filename, "r") as file:
            hist = json.load(file)
            # Ensure the system instruction is always the upgraded agentic prompt
            if hist and hist[0]["role"] == "system":
                hist[0]["content"] = system_prompt
            else:
                hist.insert(0, {"role": "system", "content": system_prompt})
            return hist
    except FileNotFoundError:
        return [{"role": "system", "content": system_prompt}]

#this mantain the length of the history of the conversation
MAX_HISTORY_LENGTH = 10  # Keep only the last 10 exchanges

def truncate_history(history):
    if len(history) > MAX_HISTORY_LENGTH:
        return history[-MAX_HISTORY_LENGTH:]
    return history


# this part is of chatbot where we give a text input and get a text out put
# Using local Ollama service


# Load conversation history from file
conversation_history = load_history()

# Before making an API call, truncate the history
conversation_history = truncate_history(conversation_history)

def chatbot(prompt):

    # Add user input to conversation history
    conversation_history.append({"role": "user", "content": prompt})

    print("Bone is thinking...", end="\r", flush=True)

    try:
        # Initialize client with custom host if remote Colab is used
        if OLLAMA_HOST:
            client = ollama.Client(
                host=OLLAMA_HOST,
                headers={"ngrok-skip-browser-warning": "true"}
            )
        else:
            client = ollama
            
        # Make API call to get the assistant's reply using Ollama (streaming)
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=conversation_history,
            stream=True,
        )
        
        # Clear "thinking" line and start printing the reply
        print(" " * 30, end="\r", flush=True)
        print("Bone: ", end="", flush=True)
        
        assistant_reply = ""
        for chunk in response:
            token = chunk['message']['content']
            print(token, end="", flush=True)
            assistant_reply += token
        print() # New line after streaming finishes
    except Exception as e:
        print(f"\nOllama Error: {e}")
        assistant_reply = "Sorry, I had trouble reaching Ollama. Please check if the Ollama service is running."

    # Add assistant's reply to conversation history
    conversation_history.append({"role": "assistant", "content": assistant_reply})

    # Save updated history to file
    save_history()

    return assistant_reply


def verify_connection():
    """Verifies that the Ollama host is reachable and the model is loaded before starting."""
    print("Testing connection to Ollama server... Please wait.")
    try:
        # Initialize client with custom host if remote Colab is used
        if OLLAMA_HOST:
            client = ollama.Client(
                host=OLLAMA_HOST,
                headers={"ngrok-skip-browser-warning": "true"}
            )
            print(f"[Connection Check] Attempting to reach remote Google Colab at: {OLLAMA_HOST}")
        else:
            client = ollama
            print("[Connection Check] Attempting to reach local Ollama service...")
            
        # Call a quick lightweight endpoint (list tags/models)
        models_list = client.list()
        
        # Robustly extract model names supporting different library versions (m.model vs m['name'])
        available_models = []
        models_data = models_list.models if hasattr(models_list, 'models') else models_list.get('models', [])
        for m in models_data:
            if hasattr(m, 'model'):
                available_models.append(m.model)
            elif isinstance(m, dict) and 'model' in m:
                available_models.append(m['model'])
            elif isinstance(m, dict) and 'name' in m:
                available_models.append(m['name'])
        
        print("\n🎉 CONNECTION SUCCESSFUL! 🎉")
        print(f"Server is fully reachable.")
        print(f"Available models on server: {available_models}")
        
        if OLLAMA_MODEL in available_models or f"{OLLAMA_MODEL}:latest" in available_models:
            print(f"👉 Success: Selected model '{OLLAMA_MODEL}' is pulled and ready!")
            return True
        else:
            print(f"\n⚠️ Warning: Model '{OLLAMA_MODEL}' is NOT pulled on this server yet!")
            print(f"Please make sure your server has pulled it using: ollama pull {OLLAMA_MODEL}")
            return False
            
    except Exception as e:
        print("\n❌ CONNECTION FAILED! ❌")
        print(f"Error details: {e}")
        print("\n💡 Troubleshooting Steps:")
        if OLLAMA_HOST:
            print("1. Verify your Google Colab notebook cell is currently running.")
            print("2. Double-check that your OLLAMA_HOST ngrok URL is copied correctly.")
            print("3. IMPORTANT: Copy your tunnel URL, open it in your browser, and click 'Visit Site' to bypass Ngrok's bot filter.")
        else:
            print("1. Make sure the local Ollama desktop application is open and running in your taskbar.")
        print("-" * 50)
        return False


#Test for Chat bot Functioning
if __name__ == "__main__":
    import sys
    if "--cli" in sys.argv:
        # Run startup health check once
        connection_ok = verify_connection()
        
        while True:
            print("\nSpeak now:")
            ask = Intake()
            # If the user didn't say anything, continue
            if not ask.strip():
                continue
                
            # Check for memory reset commands
            if ask.lower().strip() in ["reset", "clear history", "clear"]:
                conversation_history = [{"role": "system", "content": "You are Bone, a helpful assistant."}]
                save_history()
                speak("I have reset my memory.")
                print("\n[Assistant memory cleared successfully]")
                continue
                
            print(f"You said: {ask}")
            
            try:
                reply = chatbot(ask)
                final_reply = clean_reply(reply)

                #this will exit or end the conversation if the user say bye or exit
                if "bye" in final_reply.lower() or "exit" in ask.lower():
                    speak(final_reply)
                    print("Closing the application...")
                    exit(0)
                else:
                    speak(final_reply)
            except KeyboardInterrupt as e:
                # Instantly cut off speech/thinking on Ctrl+C and return to listening
                print("\n[Interrupted! Stopping speech...]")
                try:
                    import winsound
                    winsound.PlaySound(None, winsound.SND_PURGE)
                except Exception:
                    pass
                    
                # Context management: update conversation history to match only what was actually spoken
                spoken_so_far = str(e).strip()
                if spoken_so_far:
                    print(f"(Bone spoke: \"{spoken_so_far}\")")
                    if conversation_history and conversation_history[-1]["role"] == "assistant":
                        conversation_history[-1]["content"] = spoken_so_far
                        save_history()
                else:
                    # Interrupted during thinking/generation: pop the user prompt out of context
                    if conversation_history and conversation_history[-1]["role"] == "user":
                        conversation_history.pop()
                        save_history()
                continue
    else:
        print("Launching B.O.N.E. Futuristic GUI Core...")
        from bone_GUI import BoneApp
        app = BoneApp()
        app.mainloop()




