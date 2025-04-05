from pynput import keyboard
import pyautogui
import sys
import time
import pyperclip
listener=None

print("pyqqspam")
print("if <F4> is pressed spam will begin. <ctrl>+c to quit.")
spam_num=int(input("how many times do you want to spam? : "))
pyperclip.copy(input("input spam message: "))
interval=float(input("input spam delay (second): "))

def F4_down():
    print("F4 is pressed, start spamming.")
    for _ in range(spam_num):
            pyautogui.hotkey("ctrl","v")
            time.sleep(0.001)
            pyautogui.press("enter")
            print("msg number",_,"sent, total count is",spam_num,"sleeping...")
            time.sleep(interval)

def ctrlc_shutdown():
    global listener
    listener.stop()
    print("ctrl+c, quit.")
    sys.exit(0)
    return False

with keyboard.GlobalHotKeys({"<F4>":F4_down,"<ctrl>+c":ctrlc_shutdown}) as listener_obj:
    listener=listener_obj
    time.sleep(1)
    print("ready to spam. listening...")
    listener.join()