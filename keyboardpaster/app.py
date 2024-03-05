import time
import re
import json
import pkg_resources
from pynput.keyboard import Controller, Key

from kivymd.app import MDApp
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.textinput import TextInput
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window

from keyboardpaster.keyboard_layout_detector import get_keyboard_layout
from keyboardpaster.modules.autoupdate import autoupdate

# Fix Focus Behaviour
import os
os.environ["SDL_MOUSE_FOCUS_CLICKTHROUGH"] = '1'

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
        '?': '§', '`': '§', ':': ';', ';': ',', '>': '<', '_': '-',
        '*': "'"
    }
}

SPECIAL_CHARS_ALT_GR = {
    'EN_US': {},
    'DA_DK': {
        '$': '4', '£': '3', '@': '2', '{': '7', '}': '0', '[': '8',
        ']': '9', '|': '´', '€': 'E'
    }
}

"""
SPECIAL_CHARS_SPACE = {
    'EN_US': {},
    'DA_DK': {
        '^': '¨'
    }
}
"""

keyboard = Controller()


def type_string(text: str, delay: float = 0.1, mod_delay: float = 0.1, layout: str = 'EN_US', end_line=False) -> None:
    """
    Types the given text using the keyboard module with an optional delay between keypresses.

    :param text: The text to be typed.
    :param delay: The delay between keypresses in seconds. Default is 0.1 seconds.
    :param mod_delay: An extra delay added when using modifiers like shift and alt_gr. Default is 0.1 seconds.
    :param layout: The keyboard layout to use. Default is 'EN_US'.
    :param end_line: Should end the paste with a ENTER press.
    """

    # print(f"{layout=}")
    special_chars_shift = SPECIAL_CHARS_SHIFT.get(layout, SPECIAL_CHARS_SHIFT[layout])
    special_chars_alt_gr = SPECIAL_CHARS_ALT_GR.get(layout, SPECIAL_CHARS_ALT_GR[layout])

    # print(f"{special_chars_alt_gr}")

    for char in text:
        if char in special_chars_shift:
            with keyboard.pressed(Key.shift):
                time.sleep(mod_delay)
                keyboard.press(special_chars_shift[char])
                keyboard.release(special_chars_shift[char])
        elif char in special_chars_alt_gr:
            # print("Using ALT_GR")
            with keyboard.pressed(Key.alt_gr):
                time.sleep(mod_delay)
                keyboard.press(special_chars_alt_gr[char])
                keyboard.release(special_chars_alt_gr[char])
        elif char.isupper():
            with keyboard.pressed(Key.shift):
                time.sleep(mod_delay)
                keyboard.press(char.lower())
                keyboard.release(char.lower())
        else:
            keyboard.press(char)
            keyboard.release(char)
        time.sleep(delay)

    if end_line:
        keyboard.press(Key.enter)
        keyboard.release(Key.enter)


def type_string_with_delay(text: str, start_delay: float = 3.0, mod_delay: float = 0.1, keypress_delay: float = 0.1, layout: str = 'EN_US', end_line=False) -> None:
    """
    Types the given text using the keyboard module after a defined start delay, with an optional delay between keypresses.

    :param text: The text to be typed.
    :param start_delay: The delay before typing starts in seconds. Default is 3.0 seconds.
    :param keypress_delay: The delay between keypresses in seconds. Default is 0.1 seconds.
    :param layout: The keyboard layout to use. Default is 'EN_US'.
    :param end_line: Should end the paste with a ENTER press.
    """
    # print(f"Starting to type in {start_delay} seconds...")

    def type_with_delay_callback(dt):
        # print(f"Typing: {text}")
        type_string(text, delay=keypress_delay, mod_delay=mod_delay, layout=layout, end_line=end_line)

    Clock.schedule_once(type_with_delay_callback, start_delay)


class KeyboardPasterApp(MDApp):
    layout = StringProperty('EN_US')
    start_delay = ObjectProperty(None)
    layout = 'EN_US'

    def build(self):
        self.theme_cls.primary_palette = "DeepPurple"  # Change to your desired primary color
        self.theme_cls.accent_palette = "Amber"  # Change to your desired accent color
        self.theme_cls.theme_style = "Light"  # Set the theme to either "Light" or "Dark"

        self.detect_keyboard_layout()
        Clock.schedule_once(self.load_inputs, 1)
        Window.size = (1000, 700)

        kv_file_path = pkg_resources.resource_filename(__name__, "keyboardpaster_app.kv")
        return Builder.load_file(kv_file_path)

    def on_stop(self):
        #self.save_inputs()
        pass

    def load_inputs(self, dt):
        try:
            with open("saved_inputs.json", "r") as file:
                saved_inputs = json.load(file)

            input_field_buttons = sum([x.children for x in self.root.ids['input_fields_container'].children], [])
            input_fields = {x for x in input_field_buttons if isinstance(x, TextInput)}
            for _, name in enumerate(saved_inputs):
                for input_field in input_fields:
                    if input_field.parent.text_input_id == name:
                        input_field.text = saved_inputs[name]

        except FileNotFoundError:
            pass

        except AttributeError:
            pass

    def save_inputs(self):
        input_field_buttons = sum([x.children for x in self.root.ids['input_fields_container'].children], [])
        input_fields = {x.parent.text_input_id:x.text for x in input_field_buttons if isinstance(x, TextInput) and x.text}
        with open("saved_inputs.json", "w") as file:
            json.dump(input_fields, file)

    def paste_text(self, input_text, _checkbox):
        if not input_text:
            # print("No text found")
            return

        if _checkbox.state == "down":
            end_line = True
        else:
            end_line = False

        start_delay = float(self.root.ids["start_delay"].value)
        mod_delay = float(self.root.ids["mod_delay"].value)
        type_string_with_delay(input_text, start_delay=start_delay, mod_delay=mod_delay, layout=self.layout, end_line=end_line)

    def set_layout(self, layout):
        self.layout = layout

    def update_slider_label(self, value):
        rounded_value = round(value, 1)
        self.root.ids["mod_delay"].value = rounded_value

    def detect_keyboard_layout(self):
        layout_code = get_keyboard_layout()

        if bool(re.match('da', layout_code, re.I)):  # Danish layout
            self.layout = 'DA_DK'
        else:  # Default to English (US) layout
            self.layout = 'EN_US'


def main():
    autoupdate()
    KeyboardPasterApp().run()


if __name__ == "__main__":
    main()
