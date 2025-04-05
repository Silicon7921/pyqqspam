import ctypes
import time
import threading
from ctypes import wintypes

MINIMUM_SLEEP = 0.0
kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32
CF_UNICODETEXT = 13

if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_uint64
else:
    ULONG_PTR = ctypes.c_uint32

kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.restype = wintypes.BOOL
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.CloseClipboard.restype = wintypes.BOOL

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
                ("dwExtraInfo", ULONG_PTR),
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
            # Ensure lParam is cast to ctypes.c_void_p
            return user32.CallNextHookEx(None, nCode, wParam, ctypes.c_void_p(lParam))

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

        def set_clipboard_text(text):
            user32.OpenClipboard(0)
            try:
                user32.EmptyClipboard()
                encoded_text = text.encode("utf-16-le") + b'\x00\x00'
                h_clip_mem = kernel32.GlobalAlloc(0x0042, len(encoded_text))  # GMEM_MOVEABLE | GMEM_ZEROINIT
                if not h_clip_mem:
                    raise ctypes.WinError(ctypes.get_last_error())

                p_clip_mem = kernel32.GlobalLock(h_clip_mem)
                if not p_clip_mem:
                    error_code = ctypes.GetLastError()  # 获取错误代码
                    kernel32.GlobalFree(h_clip_mem)
                    raise MemoryError(f"Failed to lock global memory. Error code: {error_code}")

                try:
                    ctypes.memmove(p_clip_mem, encoded_text, len(encoded_text))
                finally:
                    kernel32.GlobalUnlock(h_clip_mem)

                if not user32.SetClipboardData(CF_UNICODETEXT, h_clip_mem):
                    kernel32.GlobalFree(h_clip_mem)
                    raise OSError("Failed to set clipboard data.")
            finally:
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