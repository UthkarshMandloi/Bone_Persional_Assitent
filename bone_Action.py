# Asynchronous Background Subprocess Execution Engine for Bone
# Designed to safely run workspace commands, capture logs, and manage threads without blocks.

import os
import sys
import subprocess
import threading
import time

# Thread-safe global dictionary to track active processes
active_tasks = {}
task_counter = 0
task_lock = threading.Lock()

class BackgroundTask:
    def __init__(self, task_id, command):
        self.task_id = task_id
        self.command = command
        self.status = "RUNNING"  # RUNNING, COMPLETED, FAILED
        self.exit_code = None
        self.stdout = ""
        self.stderr = ""
        self.process = None
        self.start_time = time.time()
        self.end_time = None
        self.stdout_lock = threading.Lock()
        self.stderr_lock = threading.Lock()

    def execute(self, callback=None):
        """Starts a background thread to execute the command non-blockingly."""
        def run():
            try:
                self.process = subprocess.Popen(
                    self.command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,  # Line-buffered output
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                
                # Dedicated threads to read output streams concurrently
                # This guarantees that the OS buffer never fills up, preventing process locks.
                def read_stdout():
                    try:
                        for line in self.process.stdout:
                            with self.stdout_lock:
                                self.stdout += line
                    except Exception:
                        pass

                def read_stderr():
                    try:
                        for line in self.process.stderr:
                            with self.stderr_lock:
                                self.stderr += line
                    except Exception:
                        pass

                t_stdout = threading.Thread(target=read_stdout, daemon=True)
                t_stderr = threading.Thread(target=read_stderr, daemon=True)
                
                t_stdout.start()
                t_stderr.start()

                # Poll and verify command status dynamically ("verify it again and again")
                while self.process.poll() is None:
                    time.sleep(0.1)

                # Wait for readers to finish writing everything
                t_stdout.join(timeout=1.0)
                t_stderr.join(timeout=1.0)

                self.exit_code = self.process.returncode
                self.end_time = time.time()
                
                with task_lock:
                    if self.status == "RUNNING": # If not forced terminated
                        self.status = "COMPLETED" if self.exit_code == 0 else "FAILED"
                        
            except Exception as e:
                with task_lock:
                    self.status = "FAILED"
                    self.stderr = f"Subprocess creation error: {str(e)}"
                    self.exit_code = -1
                self.end_time = time.time()

            # Trigger optional task completed callback
            if callback:
                try:
                    callback(self)
                except Exception as callback_err:
                    print(f"[bone_Action.py Exception] Callback failed: {callback_err}")

        # Dispatch standard background execution thread
        threading.Thread(target=run, daemon=True).start()

def execute_command(command, callback=None):
    """Launches a shell command in the background, tracks it globally, and returns the Task object."""
    global task_counter
    with task_lock:
        task_counter += 1
        task_id = task_counter
        task = BackgroundTask(task_id, command)
        active_tasks[task_id] = task
        
    task.execute(callback)
    return task

def terminate_all_tasks():
    """Forcibly terminates all currently running background tasks."""
    terminated_count = 0
    with task_lock:
        for task_id, task in list(active_tasks.items()):
            if task.status == "RUNNING" and task.process:
                print(f"[bone_Action.py] Terminating background task {task_id}: '{task.command}'")
                task.status = "FAILED"
                task.stderr += "\n[System Alert: Task forcibly terminated by user interrupt.]"
                task.exit_code = -9
                task.end_time = time.time()
                try:
                    # Terminate process and its children using OS taskkill on Windows
                    if sys.platform == "win32":
                        subprocess.run(f"taskkill /F /T /PID {task.process.pid}", shell=True, capture_output=True)
                    else:
                        task.process.terminate()
                    terminated_count += 1
                except Exception as err:
                    print(f"[bone_Action.py Alert] Error terminating process: {err}")
    return terminated_count
