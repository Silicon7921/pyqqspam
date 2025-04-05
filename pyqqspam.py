from pynput import keyboard
import pyautogui
import time
import pyperclip
import threading
import sys

pyautogui.PAUSE = 0.001
pyautogui.FAILSAFE = False

class HotkeyManager:
    def __init__(self):
        self.ctrl_pressed = False
        self.f4_pressed = False
        self.listener = None
        self.running = True
        self.is_spamming = False
        self.lock = threading.Lock()
        print("initializing...")

    def on_press(self, key):
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = True
            elif key == keyboard.KeyCode.from_char('c') and self.ctrl_pressed:
                self.terminate()
            if key == keyboard.Key.f4 and not self.is_spamming:
                with self.lock:
                    self.f4_pressed = True
        except AttributeError:
            pass

    def on_release(self, key):
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            self.ctrl_pressed = False

    def start_listener(self):
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        print("listener started.")

    def terminate(self,graceful:bool):
        if not graceful:
            print("interrupted.")
            sys.exit(1)
        else:
            self.running = False
            if self.listener:
                self.listener.stop()
            sys.exit(0)

def precise_sleep(duration:float,manager):
    start = time.perf_counter()
    target_end = start + duration
    if duration > 0.1:
        while time.perf_counter() < target_end and manager.running:
            remaining = target_end - time.perf_counter()
            sleep_time = min(remaining, 0.05)
            time.sleep(sleep_time)
    else:
        while time.perf_counter() < target_end and manager.running:
            pass

def spam_cycle(manager, count:float, interval:float):
    with manager.lock:
        manager.is_spamming = True
        manager.f4_pressed = False
    
    try:
        start_cycle = time.perf_counter()
        print(f"start spam cycle with {count} msg.")
        for i in range(count):
            if not manager.running:
                break
            pyautogui.hotkey('ctrl', 'v')
            pyautogui.press('enter')
            print(f"msg{i+1} sent, {count-i-1} msg(s) remain")
            if i < count - 1:
                precise_sleep(interval, manager=manager)
        cycle_time = time.perf_counter() - start_cycle
        print(f"sent {count} msg in {cycle_time:.3f}s "f", expected {count*interval:.3f}s")
    finally:
        with manager.lock:
            manager.is_spamming = False

if __name__ == "__main__":
    manager = HotkeyManager()
    print("---pyqqspam---")
    print("<F4> triggers spamming, <ctrl>+c to quit.")
    try:
        start_cycle = time.perf_counter()
        spam_count = int(input("number of msg per trigger: "))
        pyperclip.copy(input("spam message: "))
        interval = float(input("delay between msgs (sec): "))
        manager.start_listener()
        while manager.running:
            if manager.f4_pressed and not manager.is_spamming:
                threading.Thread(target=spam_cycle,args=(manager, spam_count, interval),daemon=True).start()
            precise_sleep(0.01,manager)
    except KeyboardInterrupt:
        manager.terminate(True)
    finally:
        print("program exited successfully.")