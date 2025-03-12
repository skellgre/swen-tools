import sys
import time
import threading
import subprocess


class ProgressBar:
    def __init__(self, total=100, start_bracket="[", end_bracket="]", empty_bar="-", filled_bar="█"):
        self.start_bracket = start_bracket
        self.end_bracket = end_bracket
        self.empty_bar = empty_bar
        self.filled_bar = filled_bar
        self.total = total  # Total progress units
        self.running = False
        self.thread = None  # Thread for the progress bar

    def _progress_bar(self, progress):
        """Prints the progress bar based on the given progress value."""
        percent = f"{(progress / self.total) * 100:.1f}"
        filled_length = int(50 * progress // self.total)
        empty_length = 50 - filled_length

        bar = f"{self.start_bracket}{self.filled_bar * filled_length}{self.empty_bar * empty_length}{self.end_bracket} {percent}%"
        sys.stdout.write(f"\r{bar}")
        sys.stdout.flush()

    def _run(self, duration):
        """Runs the progress bar over the given duration and stops when complete."""
        start_time = time.time()
        while self.running:
            elapsed = time.time() - start_time
            progress = min(self.total, int((elapsed / duration) * self.total))

            self._progress_bar(progress)

            if progress >= self.total:
                break  # Stop when complete

            time.sleep(0.1)  # Prevent excessive CPU usage



    def start(self, duration):
        """Starts the progress bar in a separate thread."""
        self.running = True
        self.thread = threading.Thread(target=self._run, args=(duration,))
        self.thread.start()

    def stop(self, done = True):
        """Stops the progress bar thread."""
        if done:
            self._progress_bar(100)
            print()
        self.running = False
        if self.thread:
            self.thread.join()

if __name__ == "__main__":
    bar = ProgressBar()
    
    # Start progress for an estimated duration 
    duration = 10
    bar.start(duration)

    # Main task
    time.sleep(6)

    bar.stop()

    print("Main task completed!")
