import platform
import subprocess
import ctypes
from ctypes import wintypes
from kivy.logger import Logger


def get_operating_system():
    os_name = platform.system()
    if os_name == "Linux":
        return "Linux"
    elif os_name == "Windows":
        return "Windows"
    elif os_name == "Darwin":
        return "MacOS"
    else:
        raise Exception(f"Unsupported operating system: {os_name}")


def get_keyboard_layout_windows():
    user32 = ctypes.WinDLL('user32', use_last_error=True)

    HKL = wintypes.HKL
    user32.GetKeyboardLayoutNameW.restype = wintypes.BOOL
    user32.GetKeyboardLayoutNameW.argtypes = [wintypes.LPWSTR]

    layout_name = ctypes.create_unicode_buffer(9)
    try:
        if not user32.GetKeyboardLayoutNameW(layout_name):
            err = ctypes.get_last_error()
            raise ctypes.WinError(err)
    except Exception as e:
        Logger.error(f"Error detecting keyboard layout on Windows: {e}. Defaulting to English (US).")
        return "EN_US"

    layout_code = layout_name.value
    return layout_code


def get_keyboard_layout_linux():
    try:
        output = subprocess.check_output(["setxkbmap", "-query"]).decode("utf-8")
        for line in output.splitlines():
            if line.startswith("layout:"):
                return line.split(" ")[-1]
    except Exception as e:
        Logger.error(f"Error detecting keyboard layout on Linux: {e}. Defaulting to English (US).")
        return "EN_US"


def get_keyboard_layout_macos():
    try:
        output = subprocess.check_output(
            ["defaults", "read", "/Library/Preferences/com.apple.HIToolbox.plist", "AppleSelectedInputSources"]
        ).decode("utf-8")
        start_index = output.find('"KeyboardLayout Name"')
        if start_index != -1:
            start_index = output.find('"', start_index + 22) + 1
            end_index = output.find('"', start_index)
            return output[start_index:end_index]
    except Exception as e:
        Logger.error(f"Error detecting keyboard layout on MacOS: {e}. Defaulting to English (US).")
        return "EN_US"


def get_keyboard_layout():
    try:
        os_name = get_operating_system()
        if os_name == "Linux":
            return get_keyboard_layout_linux()
        elif os_name == "Windows":
            return get_keyboard_layout_windows()
        elif os_name == "MacOS":
            return get_keyboard_layout_macos()
        else:
            raise Exception(f"Unsupported operating system: {os_name}")
    except Exception as e:
        Logger.error(f"Error detecting operating system or keyboard layout: {e}. Defaulting to English (US).")
        return "EN_US"