from pynput import keyboard
import pyautogui
import time
import pyperclip
import threading

f4_pressed = False

class HotkeyManager:
    def __init__(self):
        self.ctrl_pressed = False
        self.listener = None
        self.running = True
        print("init.")

    def on_press(self, key):
        global f4_pressed
        try:
            if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
                self.ctrl_pressed = True
            elif key == keyboard.KeyCode.from_char('c') and self.ctrl_pressed:
                self.terminate()
            if key == keyboard.Key.f4:
                f4_pressed = True
        except AttributeError:
            pass

    def on_release(self, key):
        global f4_pressed
        if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            self.ctrl_pressed = False
        if key == keyboard.Key.f4:
            f4_pressed = False

    def start_listener(self):
        self.listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.listener.start()
        print("listener started.")

    def terminate(self):
        self.running = False
        if self.listener is not None:
            self.listener.stop()
        print("Exiting...")

if __name__ == "__main__":
    manager = HotkeyManager()
    print("pyqqspam")
    print("if <F4> is pressed spam will begin. <ctrl>+c to quit.")
    spam_num = int(input("how many times do you want to spam? : "))
    pyperclip.copy(input("input spam message: "))
    interval = float(input("input spam delay (second): "))

    def spam_keys():
        while manager.running:
            if f4_pressed:
                for _ in range(spam_num):
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.001)
                    pyautogui.press("enter")
                    print(f"msg {_+1} of {spam_num} sent, sleeping...")
                    time.sleep(interval)

    spam_thread = threading.Thread(target=spam_keys, daemon=True)
    manager.start_listener()
    spam_thread.start()

    try:
        while manager.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        manager.terminate()