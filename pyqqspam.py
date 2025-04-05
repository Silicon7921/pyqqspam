from pynput import keyboard
import pyautogui
import time
import pyperclip
import threading
import ctypes

pyautogui.PAUSE = 0.0001
pyautogui.FAILSAFE = False
MINIMUM_SLEEP = 0.0

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
    
    def win32_event_filter(self,data):
            if data.vkCode == 0x43 and (data.flags & 0x80) and self.ctrl_pressed:
                self.terminate()
            return True

    def start_listener(self):
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release, win32_event_filter=self.win32_event_filter)
        self.listener.start()
        print("listener started.")

    def terminate(self):
        self.running = False
        ctypes.windll.kernel32.ExitProcess(1)

def precise_sleep(duration:float):
    if duration <= 0:
        return
    kernel32 = ctypes.windll.kernel32
    timer = kernel32.CreateWaitableTimerExW(None, None, 0x00000002, 0x1F0003)
    delay = ctypes.c_longlong(int(-1 * duration * 10000000))
    kernel32.SetWaitableTimer(timer, ctypes.byref(delay), 0, None, None, 0)
    kernel32.WaitForSingleObject(timer, 0xFFFFFFFF)
    kernel32.CloseHandle(timer)

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
                precise_sleep(interval)
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
        ctypes.windll.winmm.timeBeginPeriod(1)
        start_cycle = time.perf_counter()
        spam_count = int(input("number of msg per trigger: "))
        pyperclip.copy(input("spam message: "))
        interval = float(input("delay between msgs (sec): "))
        manager.start_listener()
        while manager.running:
            if manager.f4_pressed and not manager.is_spamming:
                threading.Thread(target=spam_cycle,args=(manager, spam_count, interval),daemon=True).start()
            precise_sleep(0.01)
    except KeyboardInterrupt:
        manager.terminate()
    finally:
        ctypes.windll.winmm.timeEndPeriod(1)
        print("program exited successfully.")