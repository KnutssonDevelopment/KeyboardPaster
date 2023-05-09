import time
import keyboard
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
from keyboardpaster.keyboard_layout_detector import get_keyboard_layout

SPECIAL_CHARS_SHIFT = {
    'EN_US': {
        '~': '`', '!': '1', '@': '2', '#': '3', '$': '4',
        '%': '5', '^': '6', '&': '7', '*': '8', '(': '9',
        ')': '0', '_': '-', '+': '=', '{': '[', '}': ']',
        '|': '\\', ':': ';', '"': "'", '<': ',', '>': '.',
        '?': '/'
    },
    'DA_DK': {
        '½': '§', '!': '1', '"': '2', '#': '3', '¤': '4', '%': '5',
        '&': '6', '/': '7', '(': '8', ')': '9', '=': '0', '+': '´',
        '?': '§', '`': '§', '@': '2', '£': '3', '$': '4', '€': '5',
        '{': '[', '[': '8', ']': '9', '}': ']', ':': ';', ';': ',',
        '|': '\\', '<': ',', '>': '.', '_': '-', '^': '¨', '*': "'"
    }
}

def type_string(text: str, delay: float = 0.1, layout: str = 'EN_US') -> None:
    """
    Types the given text using the keyboard module with an optional delay between keypresses.

    :param text: The text to be typed.
    :param delay: The delay between keypresses in seconds. Default is 0.1 seconds.
    :param layout: The keyboard layout to use. Default is 'EN_US'.
    """
    special_chars_shift = SPECIAL_CHARS_SHIFT.get(layout, SPECIAL_CHARS_SHIFT['EN_US'])

    for char in text:
        if char in special_chars_shift:
            keyboard.press('shift')
            keyboard.press(special_chars_shift[char])
            keyboard.release(special_chars_shift[char])
            keyboard.release('shift')
        elif char.isupper():
            keyboard.press('shift')
            keyboard.press(char.lower())
            keyboard.release(char.lower())
            keyboard.release('shift')
        else:
            keyboard.press(char)
            keyboard.release(char)
        time.sleep(delay)


def type_string_with_delay(text: str, start_delay: float = 3.0, keypress_delay: float = 0.1, layout: str = 'EN_US') -> None:
    """
    Types the given text using the keyboard module after a defined start delay, with an optional delay between keypresses.

    :param text: The text to be typed.
    :param start_delay: The delay before typing starts in seconds. Default is 3.0 seconds.
    :param keypress_delay: The delay between keypresses in seconds. Default is 0.1 seconds.
    :param layout: The keyboard layout to use. Default is 'EN_US'.
    """
    print(f"Starting to type in {start_delay} seconds...")
    time.sleep(start_delay)
    type_string(text, delay=keypress_delay, layout=layout)


class KeyboardPasterApp(App):
    layout = 'EN_US'

    def build(self):
        self.detect_keyboard_layout()
        return Builder.load_file("KeyboardPaster/keyboardpaster.kv")

    def paste_text(self):
        text_to_paste = self.root.ids.input_text.text
        type_string_with_delay(text_to_paste, layout=self.layout)

    def set_layout(self, layout):
        self.layout = layout

    def detect_keyboard_layout(self):
        layout_code = get_keyboard_layout()

        if layout_code.startswith('da'):  # Danish layout
            self.layout = 'DA_DK'
        else:  # Default to English (US) layout
            self.layout = 'EN_US'


def main():
    KeyboardPasterApp().run()


if __name__ == "__main__":
    main()
