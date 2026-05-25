# Futuristic local AI assistant GUI for Bone
# Powered by CustomTkinter, Ollama, Vosk, Kokoro-ONNX, and Autonomous Actions

import os
import sys
import re
import math
import threading
import queue
import time
import tkinter as tk
import customtkinter as ctk
import winsound
import ollama
import bone_Action as action # Dynamic workspace action execution core

# Import our modular local assistant files
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from bone_Ear import voice_to_text as Intake
from bone_Mouth import speak, get_kokoro
import bone_Brain

# Set theme and color palette (Futuristic Deep Slate Dark-Mode)
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class BoneApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Window settings
        self.title("B.O.N.E. - Futuristic Personal Assistant")
        self.geometry("850x650")
        self.minsize(800, 600)
        
        # Background thread communication queues and state
        self.text_queue = queue.Queue()
        self.status_queue = queue.Queue()
        self.current_state = "BOOTING"
        self.interrupt_event = threading.Event()
        self.task_done_event = threading.Event() # Coordinates background workspace tasks
        self.auto_trigger_brain = False # Set to True to skip voice capture after command completion
        
        # Voice mute toggle state
        self.voice_muted = False
        
        # Set up GUI grid layout (1 row, 2 columns - Sidebar & Chat Panel)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.setup_sidebar()
        self.setup_chat_panel()
        
        # Keyboard Shortcuts Bindings (Global)
        self.bind("<Escape>", lambda e: self.action_interrupt())
        self.bind("<Control-r>", lambda e: self.action_reset())
        self.bind("<Control-R>", lambda e: self.action_reset())
        self.bind("<Control-m>", lambda e: self.action_toggle_mute())
        self.bind("<Control-M>", lambda e: self.action_toggle_mute())
        
        # Launch the background speech assistant thread
        self.assistant_thread = threading.Thread(target=self.run_assistant, daemon=True)
        self.assistant_thread.start()
        
        # Start queue polling loop (handles thread-safe UI updates)
        self.poll_queues()
        
        # Start the futuristic core canvas animation
        self.animate_core()
        
    def setup_sidebar(self):
        """Creates the futuristic sidebar with status indicator and controls."""
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color="#1E1E2E")
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)
        
        # App Title
        self.logo = ctk.CTkLabel(self.sidebar, text="B.O.N.E.", font=ctk.CTkFont(family="Consolas", size=28, weight="bold"), text_color="#89B4FA")
        self.logo.grid(row=0, column=0, padx=20, pady=(30, 10))
        
        self.logo_subtitle = ctk.CTkLabel(self.sidebar, text="LOCAL COGNITIVE CORE", font=ctk.CTkFont(family="Consolas", size=10), text_color="#A6ADC8")
        self.logo_subtitle.grid(row=1, column=0, padx=20, pady=(0, 30))
        
        # Central glowing status core indicator
        self.core_frame = ctk.CTkFrame(self.sidebar, width=150, height=150, corner_radius=75, fg_color="#181825", border_width=2, border_color="#313244")
        self.sidebar.grid_propagate(False)
        self.core_frame.grid(row=2, column=0, padx=20, pady=20)
        self.core_frame.pack_propagate(False)
        
        # Dynamic Animated Canvas Core
        self.canvas = tk.Canvas(self.core_frame, width=146, height=105, bg="#181825", highlightthickness=0)
        self.canvas.pack(pady=(12, 0))
        
        self.status_label = ctk.CTkLabel(self.core_frame, text="BOOTING", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color="#A6ADC8")
        self.status_label.pack(pady=(0, 10))
        
        # Host info panel
        self.info_frame = ctk.CTkFrame(self.sidebar, fg_color="#11111B", corner_radius=10)
        self.info_frame.grid(row=3, column=0, padx=20, pady=20, sticky="ew")
        
        self.model_lbl = ctk.CTkLabel(self.info_frame, text=f"MODEL: {bone_Brain.OLLAMA_MODEL}", font=ctk.CTkFont(family="Consolas", size=11), text_color="#F38BA8")
        self.model_lbl.pack(pady=(10, 2), padx=10, anchor="w")
        
        self.host_lbl = ctk.CTkLabel(self.info_frame, text=f"HOST: {'Colab GPU' if bone_Brain.OLLAMA_HOST else 'Local CPU'}", font=ctk.CTkFont(family="Consolas", size=11), text_color="#A6E3A1")
        self.host_lbl.pack(pady=(2, 10), padx=10, anchor="w")
        
        # Control Buttons
        self.btn_interrupt = ctk.CTkButton(self.sidebar, text="🛑 INTERRUPT VOICE", fg_color="#F38BA8", hover_color="#E06B88", text_color="#11111B", font=ctk.CTkFont(weight="bold"), command=self.action_interrupt)
        self.btn_interrupt.grid(row=5, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.btn_clear = ctk.CTkButton(self.sidebar, text="🗑️ RESET MEMORY", fg_color="#313244", hover_color="#45475A", text_color="#CDD6F4", command=self.action_reset)
        self.btn_clear.grid(row=6, column=0, padx=20, pady=10, sticky="ew")
        
        self.check_mute = ctk.CTkCheckBox(self.sidebar, text="Mute Voice Response", text_color="#CDD6F4", command=self.action_toggle_mute)
        self.check_mute.grid(row=7, column=0, padx=20, pady=(10, 30))
        
    def setup_chat_panel(self):
        """Creates the spacious modern chat transcript area."""
        self.chat_panel = ctk.CTkFrame(self, fg_color="#11111B", corner_radius=0)
        self.chat_panel.grid(row=0, column=1, sticky="nsew")
        
        self.chat_panel.grid_columnconfigure(0, weight=1)
        self.chat_panel.grid_rowconfigure(0, weight=1)
        
        # Transcript Box
        self.chat_box = ctk.CTkTextbox(self.chat_panel, font=ctk.CTkFont(family="Segoe UI", size=14), fg_color="#181825", text_color="#CDD6F4", border_color="#313244", border_width=1, corner_radius=15, wrap="word")
        self.chat_box.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        welcome_msg = (
            "--- SYSTEM BOOT COMPLETE ---\n"
            "Welcome to B.O.N.E. Local Cognitive Assistant CORE.\n\n"
            "Keyboard Shortcuts:\n"
            "  [ESC]      -> Interrupt Voice / Cancel Background Subprocesses\n"
            "  [Ctrl + R] -> Reset Conversation Memory\n"
            "  [Ctrl + M] -> Toggle Mute Voice Output\n\n"
            "Testing connection to server, please wait...\n"
        )
        self.chat_box.insert("0.0", welcome_msg)
        self.chat_box.configure(state="disabled")
        
    # =====================================================================
    # ACTIONS & BUTTON COMMANDS
    # =====================================================================
    def action_interrupt(self):
        """Action when clicking the visual Interrupt button or pressing ESC."""
        print("\n[UI Interrupted! stopping speech & processes...]")
        self.interrupt_event.set()
        
        # Terminate any active background subprocesses running in the workspace
        terminated_count = action.terminate_all_tasks()
        if terminated_count > 0:
            self.text_queue.put(f"\n🛑 [System Console] Interrupted! Terminated {terminated_count} running background process(es).\n")
            
        # Unblock the assistant execution thread if it was waiting for command results
        self.task_done_event.set()
        
        self.status_queue.put(("READY", "🔵", "#89B4FA"))
        try:
            winsound.PlaySound(None, winsound.SND_PURGE)
        except Exception:
            pass
            
    def action_reset(self):
        """Action when clicking the Reset Memory button."""
        bone_Brain.conversation_history = bone_Brain.load_history()
        # Pop all conversation messages, leaving only the upgraded system prompt
        if len(bone_Brain.conversation_history) > 1:
            bone_Brain.conversation_history = [bone_Brain.conversation_history[0]]
        bone_Brain.save_history()
        self.text_queue.put("\n\n--- Memory Cleared Successfully! Starting New Session ---\n\n")
        self.status_queue.put(("READY", "🔵", "#89B4FA"))
        threading.Thread(target=lambda: speak("I have reset my memory."), daemon=True).start()
        
    def action_toggle_mute(self):
        """Mutes/Unmutes voice output."""
        self.voice_muted = self.check_mute.get() == 1
        
    # =====================================================================
    # THREAD-SAFE QUEUE POLLING (UI Thread Update loop)
    # =====================================================================
    def poll_queues(self):
        """Continuously pulls status and text updates from the background thread safely."""
        # Process all pending text updates
        while not self.text_queue.empty():
            content = self.text_queue.get_nowait()
            self.chat_box.configure(state="normal")
            self.chat_box.insert("end", content)
            self.chat_box.see("end")
            self.chat_box.configure(state="disabled")
            
        # Process all pending status updates (Glowing core)
        while not self.status_queue.empty():
            status, orb, color = self.status_queue.get_nowait()
            self.current_state = status
            self.status_label.configure(text=status, text_color=color)
            self.core_frame.configure(border_color=color)
            
        # Schedule the next check in 100 milliseconds
        self.after(100, self.poll_queues)

    def on_task_completed(self, task):
        """Callback triggered when a background shell process finishes execution."""
        print(f"\n[Task Completed] Exit Code: {task.exit_code}")
        
        # 1. Print formatted execution summary to chat transcript
        self.text_queue.put("\n" + "="*50 + "\n")
        if task.exit_code == 0:
            self.text_queue.put(f"🟢 [System Console] Command completed successfully!\n")
        else:
            self.text_queue.put(f"🔴 [System Console] Command failed with exit code: {task.exit_code}\n")
            
        out = task.stdout.strip()
        err = task.stderr.strip()
        
        if out:
            self.text_queue.put(f"Output:\n{out}\n")
        if err:
            self.text_queue.put(f"Error Log:\n{err}\n")
        self.text_queue.put("="*50 + "\n\n")
        
        # 2. Append command feedback inside conversation history
        result_msg = (
            f"SYSTEM COMMAND EXECUTED AND COMPLETED.\n"
            f"Command: {task.command}\n"
            f"Exit Code: {task.exit_code}\n"
        )
        if out:
            result_msg += f"Terminal Standard Output:\n{out}\n"
        if err:
            result_msg += f"Terminal Error Output:\n{err}\n"
            
        bone_Brain.conversation_history.append({"role": "user", "content": result_msg})
        bone_Brain.save_history()
        
        # 3. Set auto-trigger and release block on the assistant processing thread
        self.auto_trigger_brain = True
        self.task_done_event.set()
        
    # =====================================================================
    # THE MULTI-THREADED SPEECH & ACTION CORE
    # =====================================================================
    def run_assistant(self):
        """Runs the continuous voice listening & AI loop in a background thread."""
        # Perform startup connection check
        self.status_queue.put(("TESTING", "🟡", "#F9E2AF"))
        connection_ok = bone_Brain.verify_connection()
        
        if connection_ok:
            self.text_queue.put(f"🎉 Connection Successful! Server is fully reachable.\nSelected model: '{bone_Brain.OLLAMA_MODEL}' is ready!\n\nSpeak naturally when you see 'LISTENING'\n" + "-"*50 + "\n")
            self.status_queue.put(("READY", "🔵", "#89B4FA"))
        else:
            self.text_queue.put("❌ Connection Failed!\nPlease check your Colab notebook status and ngrok URL in the sidebar or config.\n" + "-"*50 + "\n")
            self.status_queue.put(("OFFLINE", "🔴", "#F38BA8"))
            
        while True:
            # Clear interrupt event before starting listening
            self.interrupt_event.clear()
            
            # Determine prompt input mode
            if getattr(self, "auto_trigger_brain", False):
                self.auto_trigger_brain = False
                ask = "" # Skip mic calibration/intake and immediately query LLM
            else:
                # Step 1: Calibrate and Listen
                self.status_queue.put(("LISTENING", "🎙️", "#A6E3A1"))
                ask = Intake()
                
                if not ask.strip():
                    # If nothing spoken/timeout, loop back
                    continue
                    
                # If user spoke memory reset voice commands
                if ask.lower().strip() in ["reset", "clear history", "clear"]:
                    self.action_reset()
                    continue
                    
                # Print spoken transcription to textbox
                self.text_queue.put(f"\nYou: {ask}\n")
                
                # Add user input to conversation history
                bone_Brain.conversation_history.append({"role": "user", "content": ask})
                bone_Brain.save_history()
            
            # Step 2: Query the LLM
            self.status_queue.put(("THINKING", "🧠", "#FAB387"))
            self.text_queue.put("Bone: ")
            
            try:
                # Check remote or local host
                if bone_Brain.OLLAMA_HOST:
                    client = ollama.Client(
                        host=bone_Brain.OLLAMA_HOST,
                        headers={"ngrok-skip-browser-warning": "true"}
                    )
                else:
                    client = ollama
                    
                response_stream = client.chat(
                    model=bone_Brain.OLLAMA_MODEL,
                    messages=bone_Brain.conversation_history,
                    stream=True,
                )
                
                assistant_reply = ""
                for chunk in response_stream:
                    # Check for GUI thread interruption
                    if self.interrupt_event.is_set():
                        raise KeyboardInterrupt()
                        
                    token = chunk['message']['content']
                    # Stream tokens straight to the GUI textbox safely!
                    self.text_queue.put(token)
                    assistant_reply += token
                    
                self.text_queue.put("\n")
                
                # Add assistant's reply to history
                bone_Brain.conversation_history.append({"role": "assistant", "content": assistant_reply})
                bone_Brain.save_history()
                
                # Scan assistant's response for a terminal background command [RUN: command]
                match = re.search(r'\[RUN:\s*(.*?)\]', assistant_reply, re.DOTALL)
                if match:
                    cmd_string = match.group(1).strip()
                    
                    # 1. Print message to chat transcript
                    self.text_queue.put(f"\n📂 [System Console] Dispatching background task: \"{cmd_string}\"\n")
                    
                    # 2. Transition visual state to active command execution
                    self.status_queue.put(("EXECUTING", "⚙️", "#CBA6F7"))
                    
                    # 3. Launch the task and wait for callback to complete
                    self.task_done_event.clear()
                    action.execute_command(cmd_string, callback=self.on_task_completed)
                    
                    # Block run_assistant thread until command completes (callback sets task_done_event)
                    self.task_done_event.wait()
                    continue # Loop back to query brain with context of the task results!
                
                # Step 3: Speak Response locally (if no command has been executed)
                if not self.voice_muted:
                    self.status_queue.put(("SPEAKING", "🗣️", "#89DCEB"))
                    final_reply = bone_Brain.clean_reply(assistant_reply)
                    
                    try:
                        speak(final_reply, self.interrupt_event)
                    except KeyboardInterrupt as e:
                        # User interrupted mid-speech
                        self.text_queue.put("\n[Interrupted!]\n")
                        spoken_so_far = str(e).strip()
                        if spoken_so_far:
                            # Context update
                            if bone_Brain.conversation_history and bone_Brain.conversation_history[-1]["role"] == "assistant":
                                bone_Brain.conversation_history[-1]["content"] = spoken_so_far
                                bone_Brain.save_history()
                                
            except KeyboardInterrupt:
                # User interrupted during thinking phase
                self.text_queue.put("\n[Interrupted!]\n")
                if bone_Brain.conversation_history and bone_Brain.conversation_history[-1]["role"] == "user":
                    bone_Brain.conversation_history.pop()
                    bone_Brain.save_history()
                    
            except Exception as e:
                # General error handling (e.g. server disconnected mid-chat)
                self.text_queue.put(f"\n[System Error] Chat session failed: {e}\n")
                self.status_queue.put(("ERROR", "🔴", "#F38BA8"))
                time.sleep(2)

    # =====================================================================
    # THE FUTURISTIC CORE CANVAS ANIMATION
    # =====================================================================
    def animate_core(self):
        """Dynamic rendering loop for the futuristic Canvas AI Core."""
        # Safeguard if canvas is destroyed
        try:
            state = self.current_state
            self.canvas.delete("all")
        except Exception:
            return
            
        cx, cy = 73, 52 # Center coordinates of the canvas
        t = time.time()
        
        # We can draw different effects depending on the state
        if state == "BOOTING" or state == "TESTING":
            # Testing/Booting: Outer tech ring spinning
            color = "#F9E2AF" if state == "TESTING" else "#A6ADC8"
            
            # Draw rotating dash circle
            angle_offset = int(t * 120) % 360
            self.canvas.create_arc(cx - 35, cy - 35, cx + 35, cy + 35, start=angle_offset, extent=60, outline=color, width=2, style="arc")
            self.canvas.create_arc(cx - 35, cy - 35, cx + 35, cy + 35, start=angle_offset+120, extent=60, outline=color, width=2, style="arc")
            self.canvas.create_arc(cx - 35, cy - 35, cx + 35, cy + 35, start=angle_offset+240, extent=60, outline=color, width=2, style="arc")
            
            # Central breathing core
            pulse = 15 + 4 * math.sin(t * 5)
            self.canvas.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse, outline=color, width=1)
            self.canvas.create_oval(cx - pulse*0.6, cy - pulse*0.6, cx + pulse*0.6, cy + pulse*0.6, fill=color, outline="")
            self.canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="#11111B", outline="")
            
        elif state == "READY":
            # Ready: A calm blue breathing sphere with an orbit ring
            color = "#89B4FA"
            
            # Orbit ring
            pulse_ring = 36 + 2 * math.sin(t * 2)
            self.canvas.create_oval(cx - pulse_ring, cy - pulse_ring, cx + pulse_ring, cy + pulse_ring, outline="#313244", width=1)
            
            # Orbit particle
            angle = t * 1.5
            px = cx + pulse_ring * math.cos(angle)
            py = cy + pulse_ring * math.sin(angle)
            self.canvas.create_oval(px - 3, py - 3, px + 3, py + 3, fill=color, outline="")
            
            # Central breathing sphere with layered outlines to simulate glow
            pulse_inner = 18 + 2 * math.sin(t * 2.5)
            for r in range(int(pulse_inner), int(pulse_inner) + 10, 2):
                self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=1)
                
            self.canvas.create_oval(cx - pulse_inner*0.8, cy - pulse_inner*0.8, cx + pulse_inner*0.8, cy + pulse_inner*0.8, fill=color, outline="")
            self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#FFFFFF", outline="")
            
        elif state == "LISTENING":
            # Listening: Soft glowing green sphere with expanding radar rings
            color = "#A6E3A1"
            
            # Radar rings
            radar_t1 = (t * 0.8) % 1.0
            radar_t2 = ((t * 0.8) + 0.5) % 1.0
            
            for rt in [radar_t1, radar_t2]:
                r = 15 + rt * 36
                w = max(1, int(3 * (1.0 - rt)))
                self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=w)
                
            # Central core
            pulse = 16 + 2 * math.sin(t * 15)
            self.canvas.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse, fill=color, outline="")
            self.canvas.create_oval(cx - pulse*0.7, cy - pulse*0.7, cx + pulse*0.7, cy + pulse*0.7, fill="#181825", outline="")
            self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=color, outline="")
            
        elif state == "THINKING":
            # Thinking: High energy pulsating peach core with rotating satellites
            color = "#FAB387"
            
            # Satellite rings
            rot_t = t * 6
            r_sat = 28
            for i in range(3):
                angle = rot_t + (i * 2 * math.pi / 3)
                sx = cx + r_sat * math.cos(angle)
                sy = cy + r_sat * math.sin(angle)
                # Orbit path
                self.canvas.create_oval(cx - r_sat, cy - r_sat, cx + r_sat, cy + r_sat, outline="#1E1E2E", width=1)
                # Satellite
                self.canvas.create_oval(sx - 3, sy - 3, sx + 3, sy + 3, fill=color, outline="")
                
            # Pulsing core
            pulse = 20 + 5 * math.sin(t * 12)
            self.canvas.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse, fill="#313244", outline="")
            self.canvas.create_oval(cx - pulse*0.7, cy - pulse*0.7, cx + pulse*0.7, cy + pulse*0.7, fill=color, outline="")
            self.canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="#FFFFFF", outline="")
            
        elif state == "SPEAKING":
            # Speaking: Glowing sky-blue core with sound wave bars
            color = "#89DCEB"
            
            # Sound waves on left and right
            wave_count = 4
            for i in range(wave_count):
                h = 8 + 20 * abs(math.sin(t * 10 - i * 1.0))
                x_offset = 20 + i * 8
                # Left side
                self.canvas.create_line(cx - x_offset, cy - h/2, cx - x_offset, cy + h/2, fill=color, width=2)
                # Right side
                self.canvas.create_line(cx + x_offset, cy - h/2, cx + x_offset, cy + h/2, fill=color, width=2)
                
            # Pulsing central mouth orb
            pulse = 14 + 3 * math.sin(t * 10)
            self.canvas.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse, fill=color, outline="")
            self.canvas.create_oval(cx - pulse*0.6, cy - pulse*0.6, cx + pulse*0.6, cy + pulse*0.6, fill="#11111B", outline="")
            
        elif state == "EXECUTING":
            # Executing: A glowing dual rotating cyan/purple sci-fi tech ring
            color_cyan = "#89DCEB"
            color_purple = "#CBA6F7"
            
            # Dual multi-speed, opposite rotating arcs
            angle_offset1 = int(t * 160) % 360
            angle_offset2 = int(-t * 200) % 360
            
            # Outer cyan arcs
            self.canvas.create_arc(cx - 38, cy - 38, cx + 38, cy + 38, start=angle_offset1, extent=90, outline=color_cyan, width=3, style="arc")
            self.canvas.create_arc(cx - 38, cy - 38, cx + 38, cy + 38, start=angle_offset1+180, extent=90, outline=color_cyan, width=3, style="arc")
            
            # Inner purple arcs
            self.canvas.create_arc(cx - 28, cy - 28, cx + 28, cy + 28, start=angle_offset2, extent=120, outline=color_purple, width=2, style="arc")
            
            # High frequency breathing core
            pulse = 13 + 3 * math.sin(t * 18)
            self.canvas.create_oval(cx - pulse, cy - pulse, cx + pulse, cy + pulse, fill="#1E1E2E", outline=color_cyan)
            self.canvas.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill=color_purple, outline="")
            
        else: # OFFLINE / ERROR
            color = "#F38BA8"
            # Offline: Dim static red circle with alert ticks
            self.canvas.create_oval(cx - 18, cy - 18, cx + 18, cy + 18, fill=color, outline="")
            self.canvas.create_oval(cx - 14, cy - 14, cx + 14, cy + 14, fill="#11111B", outline="")
            
            self.canvas.create_line(cx, cy - 6, cx, cy + 2, fill=color, width=2)
            self.canvas.create_oval(cx - 1.5, cy + 4, cx + 1.5, cy + 7, fill=color, outline="")
            
        # Re-schedule animation in 40ms (~25 FPS)
        self.after(40, self.animate_core)

if __name__ == "__main__":
    app = BoneApp()
    app.mainloop()
