import re
import json
import subprocess
import importlib.resources
import keyboardpaster

from keyboardpaster.bootstrap import configure_kivy_environment

configure_kivy_environment()

from kivymd.app import MDApp
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.uix.textinput import TextInput
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.metrics import dp
from kivy.uix.dropdown import DropDown
from kivymd.uix.selectioncontrol.selectioncontrol import MDCheckbox
from kivymd.uix.button.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField

from keyboardpaster.keyboard_input import type_string
from keyboardpaster.keyboard_layout_detector import get_keyboard_layout
from keyboardpaster.modules.autoupdate import autoupdate
from keyboardpaster.shared_resources import app_version, app_icon_path
from keyboardpaster.desktop import ensure_user_desktop_entry

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
        '&': '6', '/': '7', '(': '8', ')': '9', '=': '0',
        '?': '+', '`': '§', ':': ';', ';': ',', '>': '<', '_': '/',
        '*': '\\'
    }
}

SPECIAL_CHARS_ALT_GR = {
    'EN_US': {},
    'DA_DK': {
        '$': '4', '£': '3', '@': '2', '{': '7', '}': '0', '[': '8',
        ']': '9', '|': '´', '€': 'E',
        # ¨ key (physical ]); used by pynput path. ydotool uses DA_DK_YDOTOOL_COMBO.
        '~': ']',
    }
}

# Dynamic window sizing around slots (matches keyboardpaster_app.kv dp values)
WINDOW_WIDTH = int(dp(960))
HEADER_HEIGHT = int(dp(68))
FOOTER_HEIGHT = int(dp(72))
BODY_TOP_PADDING = int(dp(12))
SLOT_HEIGHT = int(dp(56))
SLOT_SPACING = int(dp(10))
SLOT_AREA_PADDING_V = int(dp(16))  # container padding top+bottom
MAX_WINDOW_HEIGHT = int(dp(720))

"""
SPECIAL_CHARS_SPACE = {
    'EN_US': {},
    'DA_DK': {
        '^': '¨'
    }
}
"""

def type_string_with_delay(
    text: str,
    start_delay: float = 3.0,
    mod_delay: float = 0.1,
    keypress_delay: float = 0.1,
    layout: str = 'EN_US',
    end_line: bool = False,
    on_error=None,
) -> None:
    """
    Types the given text using the keyboard module after a defined start delay, with an optional delay between keypresses.

    :param text: The text to be typed.
    :param start_delay: The delay before typing starts in seconds. Default is 3.0 seconds.
    :param keypress_delay: The delay between keypresses in seconds. Default is 0.1 seconds.
    :param layout: The keyboard layout to use. Default is 'EN_US'.
    :param end_line: Should end the paste with a ENTER press.
    :param on_error: Optional callback invoked if typing fails after the start delay.
    """

    def type_with_delay_callback(dt):
        try:
            special_chars_shift = SPECIAL_CHARS_SHIFT.get(layout, SPECIAL_CHARS_SHIFT["EN_US"])
            special_chars_alt_gr = SPECIAL_CHARS_ALT_GR.get(layout, SPECIAL_CHARS_ALT_GR["EN_US"])
            type_string(
                text,
                delay=keypress_delay,
                mod_delay=mod_delay,
                layout=layout,
                end_line=end_line,
                special_chars_shift=special_chars_shift,
                special_chars_alt_gr=special_chars_alt_gr,
            )
        except Exception as error:
            if on_error:
                on_error(error)
            else:
                raise

    Clock.schedule_once(type_with_delay_callback, start_delay)


class KeyboardPasterApp(MDApp):
    layout = StringProperty('EN_US')
    version_text = StringProperty(f"v{app_version}")
    start_delay = ObjectProperty(None)
    layout = 'EN_US'
    _updating_slots = BooleanProperty(False)

    def __init__(self):
        super().__init__()
        self.config = None
        self.json_config = 'saved_inputs.json'
        # Strong ref: KV ids only keep a WeakProxy, so DropDown was GC'd after dismiss.
        self.profile_dropdown = DropDown()

    def build(self):
        self.theme_cls.primary_palette = "Amber"
        self.theme_cls.accent_palette = "Orange"
        self.theme_cls.theme_style = "Dark"
        Window.clearcolor = (0.08, 0.08, 0.08, 1)

        self.read_config()

        self.detect_keyboard_layout()
        Clock.schedule_once(self.set_profile, 1)
        self.title = f"Keyboard Paster v{app_version}"
        Window.size = (WINDOW_WIDTH, self._height_for_slot_count(1))
        icon = app_icon_path()
        if icon is not None:
            Window.set_icon(str(icon))

        with importlib.resources.path(keyboardpaster, "keyboardpaster_app.kv") as kv_file_path:
            return Builder.load_file(str(kv_file_path))

    def on_stop(self):
        pass

    @staticmethod
    def _height_for_slot_count(slot_count: int) -> int:
        n = max(1, slot_count)
        slots_area = SLOT_AREA_PADDING_V + n * SLOT_HEIGHT + max(0, n - 1) * SLOT_SPACING
        return HEADER_HEIGHT + BODY_TOP_PADDING + slots_area + FOOTER_HEIGHT

    def update_window_height(self):
        desired = self._height_for_slot_count(len(self._ordered_slots()))
        height = min(desired, MAX_WINDOW_HEIGHT)
        if Window.size[0] != WINDOW_WIDTH or Window.size[1] != height:
            Window.size = (WINDOW_WIDTH, height)

    def _slot_container(self):
        return self.root.ids["input_fields_container"]

    def _ordered_slots(self):
        # Kivy children are reverse insertion order.
        return list(reversed(self._slot_container().children))

    @staticmethod
    def _slot_text_input(slot):
        for child in slot.children:
            if isinstance(child, TextInput):
                return child
        return None

    @staticmethod
    def _slot_secret_checkbox(slot):
        for child in slot.children:
            if isinstance(child, MDCheckbox) and getattr(child, "secret_checkbox", False):
                return child
        return None

    def _renumber_slots(self):
        for index, slot in enumerate(self._ordered_slots()):
            slot.text_input_id = f"input_text_{index}"

    def add_slot(self, text: str = "", secret: bool = False):
        container = self._slot_container()
        index = len(container.children)
        slot = Factory.InputFieldButton()
        slot.text_input_id = f"input_text_{index}"
        container.add_widget(slot)

        text_input = self._slot_text_input(slot)
        secret_cb = self._slot_secret_checkbox(slot)

        previous = self._updating_slots
        self._updating_slots = True
        try:
            if text_input is not None:
                text_input.text = text
                text_input.password = bool(secret)
            if secret_cb is not None:
                secret_cb.active = bool(secret)
        finally:
            self._updating_slots = previous

        return slot

    def clear_slots(self):
        self._slot_container().clear_widgets()

    def ensure_trailing_empty_slot(self, *_args):
        if self._updating_slots:
            return

        self._updating_slots = True
        try:
            slots = self._ordered_slots()
            if not slots:
                self.add_slot()
                self._renumber_slots()
                return

            # Remove extra trailing empty slots (keep exactly one empty at the end).
            while len(slots) > 1:
                last = slots[-1]
                prev = slots[-2]
                last_text = self._slot_text_input(last)
                prev_text = self._slot_text_input(prev)
                last_empty = last_text is None or not last_text.text.strip()
                prev_empty = prev_text is None or not prev_text.text.strip()
                if last_empty and prev_empty:
                    self._slot_container().remove_widget(last)
                    slots = self._ordered_slots()
                    continue
                break

            last = self._ordered_slots()[-1]
            last_text = self._slot_text_input(last)
            if last_text is not None and last_text.text.strip():
                self.add_slot()

            self._renumber_slots()
        finally:
            self._updating_slots = False
        self.update_window_height()

    def on_slot_text(self, _instance, _value):
        self.ensure_trailing_empty_slot()

    def read_config(self):
        try:
            with open(self.json_config, "r", encoding='utf-8') as file:
                self.config = json.load(file)
        except FileNotFoundError:
            self.config = None
        except AttributeError:
            self.config = None
        except json.JSONDecodeError:
            self.config = None
        except ValueError:
            self.config = None
        except KeyError:
            self.config = None

        if not self.config:
            self.config = {'profiles': {'DEFAULT': {}}}
        elif 'profiles' in self.config:
            pass
        elif 'input_text_0' in self.config:
            values = self.config
            self.config = {'profiles': {'DEFAULT': values}}
        else:
            self.config = {'profiles': {'DEFAULT': {}}}

    def write_config(self):
        with open(self.json_config, "w", encoding='utf-8') as file:
            json.dump(self.config, file)

    @staticmethod
    def close_dialog(button_instance):
        # Navigate up the widget tree until we find an MDDialog instance
        current_widget = button_instance
        while current_widget and not isinstance(current_widget, MDDialog):
            current_widget = current_widget.parent

        # If we found an MDDialog instance, dismiss it
        if isinstance(current_widget, MDDialog):
            current_widget.dismiss()

    def add_profile(self, profile_name, button_instance):
        # Access the text from the input box
        print(f"New profile name: {profile_name}")
        self.config['profiles'][profile_name] = dict()
        self.set_profile(None, profile_name)

        # Close the dialog using the button instance
        self.close_dialog(button_instance)

    def create_new_profile(self):
        self.close_dropdown()

        profile_input = MDTextField(
            hint_text="Enter profile name",
            size_hint_x=0.8,
            pos_hint={"center_x": 0.5}
        )

        dialog = MDDialog(
            title="New Profile",
            type="custom",
            content_cls=profile_input,
            buttons=[
                MDRaisedButton(
                    text="CANCEL",
                    on_release=self.close_dialog
                ),
                MDRaisedButton(
                    text="OK",
                    on_release=lambda x: self.add_profile(profile_input.text, x)
                )
            ],
        )
        dialog.open()

    def close_dropdown(self):
        self.profile_dropdown.dismiss()

    def handle_dropdown(self, profile):
        self.set_profile(None, profile)
        self.close_dropdown()

    def generate_profile_selector(self):
        profile_dropdown = self.profile_dropdown
        profile_selector = self.root.ids['profile_selector']
        try:
            profiles = list(self.config['profiles'].keys())
        except KeyError:
            profiles = ['DEFAULT']
        max_length = 7

        profile_dropdown.clear_widgets()

        btn = MDRaisedButton()
        btn.text = '- New -'
        btn.size_hint_y = None
        btn.bind(on_release=lambda x: self.create_new_profile())
        profile_dropdown.add_widget(btn)

        for profile in profiles:
            if len(profile) > max_length:
                max_length = len(profile)

            if profile != profile_selector.text.strip():
                btn = MDRaisedButton()
                btn.text = profile
                btn.size_hint_y = None
                btn.bind(on_release=lambda x, p=profile: self.handle_dropdown(p))
                profile_dropdown.add_widget(btn)

        number_of_whitespaces = max_length - len(profile_selector.text.strip())
        profile_selector.text = profile_selector.text + (number_of_whitespaces + 1) * " "

    def set_profile(self, dt=None, profile=None):
        profile_selector = self.root.ids['profile_selector']

        if not self.config or 'profiles' not in self.config or not self.config['profiles']:
            self.config = self.config or {}
            self.config['profiles'] = {'DEFAULT': {}}

        if profile is None:
            profile_name = list(self.config['profiles'].keys())[0]
        else:
            profile_name = profile

        profile_selector.text = profile_name
        self.load_inputs()
        self.generate_profile_selector()

    def load_inputs(self):
        profile_selector = self.root.ids['profile_selector']
        profile_name = profile_selector.text.strip()

        profile_values = {}
        if self.config and profile_name in self.config.get('profiles', {}):
            profile_values = self.config['profiles'][profile_name] or {}

        def sort_key(item):
            key = item[0]
            try:
                return int(str(key).rsplit("_", 1)[-1])
            except ValueError:
                return 0

        filled = []
        for _name, value in sorted(profile_values.items(), key=sort_key):
            if isinstance(value, (list, tuple)) and len(value) >= 2:
                text, secret_state = value[0], value[1]
            else:
                text, secret_state = value, False
            if text:
                filled.append((text, bool(secret_state)))

        self.clear_slots()
        self._updating_slots = True
        try:
            for text, secret_state in filled:
                self.add_slot(text=text, secret=secret_state)
        finally:
            self._updating_slots = False
        self.ensure_trailing_empty_slot()
        self.update_window_height()

    def save_inputs(self):
        profile_selector = self.root.ids['profile_selector']
        profile_name = profile_selector.text.strip()

        input_fields = {}
        for slot in self._ordered_slots():
            text_input = self._slot_text_input(slot)
            if text_input is None or not text_input.text:
                continue
            secret_cb = self._slot_secret_checkbox(slot)
            secret_state = bool(secret_cb.active) if secret_cb is not None else False
            input_fields[slot.text_input_id] = (text_input.text, secret_state)

        if not self.config:
            self.config = {'profiles': {}}
        if 'profiles' not in self.config:
            self.config['profiles'] = {}
        self.config['profiles'][profile_name] = input_fields
        self.write_config()

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
        type_string_with_delay(
            input_text,
            start_delay=start_delay,
            mod_delay=mod_delay,
            keypress_delay=0.02,
            layout=self.layout,
            end_line=end_line,
            on_error=self.show_type_error,
        )

    def show_type_error(self, error):
        MDDialog(title="Kan ikke sende tastaturinput", text=str(error)).open()

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

        if bool(re.match(r'da|dk', layout_code, re.I)):
            self.layout = 'DA_DK'
        else:  # Default to English (US) layout
            self.layout = 'EN_US'


def main():
    ensure_user_desktop_entry()
    autoupdate()
    KeyboardPasterApp().run()


if __name__ == "__main__":
    main()
