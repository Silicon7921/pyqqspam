import ctypes
import time
import threading

MINIMUM_SLEEP = 0.0

class HotkeyManager:
    def __init__(self):
        self.ctrl_pressed = False
        self.f4_pressed = False
        self.running = True
        self.is_spamming = False
        self.lock = threading.Lock()
        print("initializing...")

    def terminate(self):
        self.running = False
        ctypes.windll.user32.PostQuitMessage(0)
        with self.lock:
            self.is_spamming = False

    def start_listener(self):
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        byref = ctypes.byref

        WH_KEYBOARD_LL = 13
        WM_KEYDOWN = 0x0100
        WM_KEYUP = 0x0101

        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("vkCode", wintypes.DWORD),
                ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", wintypes.ULONG_PTR),
            ]

        def low_level_keyboard_proc(nCode, wParam, lParam):
            if nCode == 0:
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if wParam == WM_KEYDOWN:
                    if kb.vkCode == 0x11:  # Ctrl key
                        self.ctrl_pressed = True
                    elif kb.vkCode == 0x43 and self.ctrl_pressed:  # Ctrl+C
                        self.terminate()
                        return -1  # Stop further processing
                    elif kb.vkCode == 0x73:  # F4 key
                        with self.lock:
                            self.f4_pressed = True
                elif wParam == WM_KEYUP:
                    if kb.vkCode == 0x11:  # Ctrl key
                        self.ctrl_pressed = False
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        HOOKPROC = ctypes.WINFUNCTYPE(wintypes.LPARAM, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM)
        self.hook_proc = HOOKPROC(low_level_keyboard_proc)
        self.hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self.hook_proc, None, 0)

        msg = ctypes.wintypes.MSG()
        while self.running:
            if user32.PeekMessageW(byref(msg), None, 0, 0, 1):
                user32.TranslateMessage(byref(msg))
                user32.DispatchMessageW(byref(msg))


def precise_sleep(duration: float):
    if duration <= 0:
        return
    kernel32 = ctypes.windll.kernel32
    timer = kernel32.CreateWaitableTimerExW(None, None, 0x00000002, 0x1F0003)
    delay = ctypes.c_longlong(int(-1 * duration * 10000000))
    kernel32.SetWaitableTimer(timer, ctypes.byref(delay), 0, None, None, 0)
    kernel32.WaitForSingleObject(timer, 0xFFFFFFFF)
    kernel32.CloseHandle(timer)


def send_message():
    user32 = ctypes.windll.user32
    user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
    user32.keybd_event(0x56, 0, 0, 0)  # V down
    user32.keybd_event(0x56, 0, 2, 0)  # V up
    user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
    user32.keybd_event(0x0D, 0, 0, 0)  # Enter down
    user32.keybd_event(0x0D, 0, 2, 0)  # Enter up


def spam_cycle(manager, count: float, interval: float):
    with manager.lock:
        manager.is_spamming = True
        manager.f4_pressed = False

    try:
        start_cycle = time.perf_counter()
        print(f"start spam cycle with {count} msg.")
        for i in range(count):
            if not manager.running:
                break
            send_message()
            print(f"msg{i + 1} sent, {count - i - 1} msg(s) remain")
            if i < count - 1:
                precise_sleep(interval)
        cycle_time = time.perf_counter() - start_cycle
        print(f"sent {count} msg in {cycle_time:.3f}s "f", expected {count * interval:.3f}s")
    finally:
        with manager.lock:
            manager.is_spamming = False


if __name__ == "__main__":
    manager = HotkeyManager()
    print("---pyqqspam---")
    print("<F4> triggers spamming, <ctrl>+c to quit.")
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
        spam_count = int(input("number of msg per trigger: "))
        spam_message = input("spam message: ")
        interval = float(input("delay between msgs (sec): "))

        # Copy message to clipboard
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        CF_UNICODETEXT = 13

        def set_clipboard_text(text):
            user32.OpenClipboard(0)
            user32.EmptyClipboard()
            h_clip_mem = kernel32.GlobalAlloc(0x2000, len(text.encode("utf-16-le")) + 2)
            p_clip_mem = kernel32.GlobalLock(h_clip_mem)
            ctypes.memmove(p_clip_mem, text.encode("utf-16-le"), len(text.encode("utf-16-le")))
            kernel32.GlobalUnlock(h_clip_mem)
            user32.SetClipboardData(CF_UNICODETEXT, h_clip_mem)
            user32.CloseClipboard()

        set_clipboard_text(spam_message)

        threading.Thread(target=manager.start_listener, daemon=True).start()
        while manager.running:
            if manager.f4_pressed and not manager.is_spamming:
                threading.Thread(target=spam_cycle, args=(manager, spam_count, interval), daemon=True).start()
            precise_sleep(0.01)
    except KeyboardInterrupt:
        manager.terminate()
    finally:
        ctypes.windll.winmm.timeEndPeriod(1)
        print("program exited successfully.")