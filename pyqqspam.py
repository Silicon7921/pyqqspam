import ctypes
import time
import threading
from ctypes import wintypes

CF_UNICODETEXT = 13

if ctypes.sizeof(ctypes.c_void_p) == 8:
    ULONG_PTR = ctypes.c_uint64
else:
    ULONG_PTR = ctypes.c_uint32

kernel32 = ctypes.windll.kernel32
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL

user32 = ctypes.windll.user32
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
        print("Initializing hotkey manager...")

    def stop(self):
        self.running = False
        ctypes.windll.user32.PostQuitMessage(0)
        with self.lock:
            self.is_spamming = False

    def listen_for_hotkeys(self):
        WH_KEYBOARD_LL = 13
        WM_KEYDOWN = 0x0100
        WM_KEYUP = 0x0101

        class KeyboardInput(ctypes.Structure):
            _fields_ = [
                ("vkCode", wintypes.DWORD),
                ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ULONG_PTR),
            ]

        def process_keyboard_event(nCode, wParam, lParam):
            if nCode == 0:
                keyboard_data = ctypes.cast(lParam, ctypes.POINTER(KeyboardInput)).contents
                if wParam == WM_KEYDOWN:
                    if keyboard_data.vkCode == 0x11:
                        self.ctrl_pressed = True
                    elif keyboard_data.vkCode == 0x43 and self.ctrl_pressed:
                        self.stop()
                        return -1
                    elif keyboard_data.vkCode == 0x73:
                        with self.lock:
                            self.f4_pressed = True
                elif wParam == WM_KEYUP:
                    if keyboard_data.vkCode == 0x11:
                        self.ctrl_pressed = False
            return user32.CallNextHookEx(None, nCode, wParam, ctypes.c_void_p(lParam))

        HOOKPROC = ctypes.WINFUNCTYPE(wintypes.LPARAM, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM)
        self.hook_proc = HOOKPROC(process_keyboard_event)
        self.hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self.hook_proc, None, 0)

        message = ctypes.wintypes.MSG()
        while self.running:
            if user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))

def sleep_precisely(duration):
    if duration <= 0:
        return
    timer = kernel32.CreateWaitableTimerExW(None, None, 0x00000002, 0x1F0003)
    delay = ctypes.c_longlong(int(-1 * duration * 10000000))
    kernel32.SetWaitableTimer(timer, ctypes.byref(delay), 0, None, None, 0)
    kernel32.WaitForSingleObject(timer, 0xFFFFFFFF)
    kernel32.CloseHandle(timer)

def simulate_message_send():
    user32.keybd_event(0x11, 0, 0, 0)
    user32.keybd_event(0x56, 0, 0, 0)
    user32.keybd_event(0x56, 0, 2, 0)
    user32.keybd_event(0x11, 0, 2, 0)
    user32.keybd_event(0x0D, 0, 0, 0)
    user32.keybd_event(0x0D, 0, 2, 0)

def execute_spam_cycle(manager, message_count, delay_between_messages):
    with manager.lock:
        manager.is_spamming = True
        manager.f4_pressed = False

    try:
        start_time = time.perf_counter()
        for i in range(message_count):
            if not manager.running:
                break
            simulate_message_send()
            if i < message_count - 1:
                sleep_precisely(delay_between_messages)
        elapsed_time = time.perf_counter() - start_time
        estimated_time = (delay_between_messages + 0.001) * (message_count - 1) + 0.001
        print(f"Sent {message_count} messages in {elapsed_time:.3f} secs, Expected {estimated_time} secs.")
    finally:
        with manager.lock:
            manager.is_spamming = False

def update_clipboard(text):
    user32.OpenClipboard(0)
    try:
        user32.EmptyClipboard()
        encoded_text = text.encode("utf-16-le") + b"\x00\x00"
        memory_handle = kernel32.GlobalAlloc(0x0042, len(encoded_text))
        if not memory_handle:
            raise ctypes.WinError(ctypes.get_last_error())

        memory_pointer = kernel32.GlobalLock(memory_handle)
        if not memory_pointer:
            error_code = ctypes.GetLastError()
            kernel32.GlobalFree(memory_handle)
            raise MemoryError(f"Failed to lock memory. Error code: {error_code}")

        try:
            ctypes.memmove(memory_pointer, encoded_text, len(encoded_text))
        finally:
            kernel32.GlobalUnlock(memory_handle)

        if not user32.SetClipboardData(CF_UNICODETEXT, memory_handle):
            kernel32.GlobalFree(memory_handle)
            raise OSError("Failed to set clipboard data.")
    finally:
        user32.CloseClipboard()

if __name__ == "__main__":
    manager = HotkeyManager()
    print("---PyQQSpam---")
    print("Press F4 to start spamming, Ctrl+C to quit.")
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
        message_count = int(input("Number of messages per trigger: "))
        spam_message = input("Spam message: ")
        delay_between_messages = float(input("Delay between messages (seconds): "))

        update_clipboard(spam_message)

        threading.Thread(target=manager.listen_for_hotkeys, daemon=True).start()
        while manager.running:
            if manager.f4_pressed and not manager.is_spamming:
                threading.Thread(
                    target=execute_spam_cycle,
                    args=(manager, message_count, delay_between_messages),
                    daemon=True
                ).start()
            sleep_precisely(0.01)
    except KeyboardInterrupt:
        manager.stop()
    finally:
        ctypes.windll.winmm.timeEndPeriod(1)
        print("Program exited successfully.")