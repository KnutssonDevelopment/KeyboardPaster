import time
import re
import json
import pkg_resources
import subprocess
from pynput.keyboard import Controller, Key

from kivymd.app import MDApp
from kivy.properties import ObjectProperty, StringProperty
from kivy.uix.textinput import TextInput
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivymd.uix.selectioncontrol.selectioncontrol import MDCheckbox

from keyboardpaster.keyboard_layout_detector import get_keyboard_layout
from keyboardpaster.modules.autoupdate import autoupdate
from keyboardpaster.shared_resources import app_version

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
        self.title = f"Keyboard Paster v{app_version}"
        Window.size = (1000, 700)

        kv_file_path = pkg_resources.resource_filename(__name__, "keyboardpaster_app.kv")
        return Builder.load_file(kv_file_path)

    def on_stop(self):
        # self.save_inputs()
        pass

    def load_inputs(self, dt):
        try:
            with open("saved_inputs.json", "r") as file:
                saved_inputs = json.load(file)

            input_field_buttons = sum([x.children for x in self.root.ids['input_fields_container'].children], [])
            input_fields = [x for x in input_field_buttons if isinstance(x, TextInput)]
            checkboxes = [x for x in input_field_buttons if isinstance(x, MDCheckbox) and getattr(x, 'secret_checkbox', False)]

            for name, (text, secret_state) in saved_inputs.items():
                # Set text for TextInput
                for input_field in input_fields:
                    if input_field.parent.text_input_id == name:
                        input_field.text = text
                        break  # Found the matching input field, no need to continue the loop

                # Set state for corresponding checkbox and adjust text visibility
                for checkbox in checkboxes:
                    if checkbox.parent.text_input_id == name:
                        checkbox.active = secret_state
                        # Assuming MDTextField is a sibling or accessible as input_field here
                        # and setting its "password" property based on checkbox state
                        if secret_state:
                            input_field.password = True  # Hide text if checkbox is checked
                        else:
                            input_field.password = False  # Show text otherwise
                        break  # Found the matching checkbox, no need to continue the loop

        except FileNotFoundError:
            pass
        except AttributeError:
            pass
        except json.JSONDecodeError:
            # Handle cases where the JSON file is empty or corrupted
            pass
        except ValueError:
            # Handle cases where the JSON file is empty or corrupted
            pass

    def save_inputs(self):
        # Assuming `input_field_buttons` contains all relevant child widgets,
        # including both TextInput and MDCheckbox widgets.
        input_field_buttons = sum([x.children for x in self.root.ids['input_fields_container'].children], [])

        # Build a dictionary with `text_input_id` as keys.
        # The values will now be a tuple (or dict) with the text and the checkbox state.
        input_fields = {}
        for child in input_field_buttons:
            if isinstance(child, TextInput) and child.text:
                # Find the corresponding MDCheckbox for 'secret' state by looking at siblings or parent's children.
                # Assuming MDCheckbox with secret_checkbox set to true is a sibling or closely located.
                cb_secret = next((x for x in child.parent.children if isinstance(x, MDCheckbox) and getattr(x, 'secret_checkbox', False)), None)
                if cb_secret is not None:
                    secret_state = cb_secret.active  # Or use `.state` based on your checkbox implementation.
                else:
                    secret_state = False  # Default state if not found.

                # Store the tuple of text and secret_state in the dictionary.
                input_fields[child.parent.text_input_id] = (child.text, secret_state)

        # Save the dictionary to a JSON file.
        with open("saved_inputs.json", "w") as file:
            json.dump(input_fields, file)

    def type_text(self, input_text, _checkbox):
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

    @staticmethod
    def copy_text(input_text, _checkbox):
        if not input_text:
            # print("No text found")
            return

        cmd = 'echo ' + input_text.strip() + '|clip'
        subprocess.check_call(cmd, shell=True)

    @staticmethod
    def hide_text(_input_text, _checkbox):
        if _checkbox.state == "down":
            _input_text.password = True
        else:
            _input_text.password = False

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
