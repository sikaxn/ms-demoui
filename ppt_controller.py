import time
import psutil
import pyautogui
from inputs import get_gamepad, UnpluggedError
import sys
import subprocess

def is_ppt_running():
    for process in psutil.process_iter(['name']):
        if process.info['name'] and 'powerpnt' in process.info['name'].lower():
            return True
    return False

def main():
    print("Controller mapping script started.")
    while is_ppt_running():
        try:
            events = get_gamepad()
            for event in events:
                if event.ev_type == "Key" and event.state == 1:
                    if event.code == "BTN_SOUTH":  # A button
                        pyautogui.press("pagedown")  # Previous slide
                    elif event.code == "BTN_EAST":  # B button
                        # Exit PowerPoint and the script
                        pyautogui.press("esc")  # Exit slideshow
                        time.sleep(1)  # Wait for PowerPoint to exit
                        if is_ppt_running():
                            subprocess.call("taskkill /f /im POWERPNT.EXE", shell=True)
                        print("Exiting controller mapping script.")
                        sys.exit(0)
                    elif event.code == "BTN_WEST":  # X button
                        pyautogui.press("pagedown")  # Next slide
                elif event.ev_type == "Absolute":
                    if event.code == "ABS_HAT0Y":
                        if event.state == -1:
                            pyautogui.press("pageup")  # D-pad Up
                        elif event.state == 1:
                            pyautogui.press("pagedown")  # D-pad Down
        except UnpluggedError:
            print("Controller disconnected. Waiting for reconnection...")
            time.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)
        time.sleep(0.1)
    print("PowerPoint has exited. Exiting controller mapping script.")

if __name__ == "__main__":
    main()
