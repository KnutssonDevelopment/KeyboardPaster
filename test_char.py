#!/usr/bin/env python3
"""
Automatisk console-test af enkelttegn via ydotool (dansk tastatur, Wayland).

Klik i terminalen ved nedtælling — programmet sender taster og læser selv resultatet.

  python3 test_char.py --char ':'
  python3 test_char.py --char '$'
  python3 test_char.py --char ':' --method shift_dot_char
  python3 test_char.py --char '$' --focus-only
  python3 test_char.py --char '+'
  python3 test_char.py --char '|' --fast --skip-focus
"""

import argparse
import os
import sys

from char_test_lib import (
    YDOTOOL_SOCKET,
    countdown,
    run_char_tests,
    run_pynput_script,
    run_ydotool_key,
    run_ydotool_type,
    run_ydotool_type_us_layout_backslash,
    wait_for_focus,
)

ALTGR_4_KEYCODES = ["100:1", "5:1", "5:0", "100:0"]

CHAR_METHODS: dict[str, dict[str, tuple[str, callable]]] = {
    ":": {
        "type": ("ydotool type ':'", lambda: run_ydotool_type(":")),
        "shift_dot": ("ydotool key shift+dot", lambda: run_ydotool_key(["shift+dot"])),
        "shift_period": ("ydotool key shift+period", lambda: run_ydotool_key(["shift+period"])),
        "shift_dot_char": ("ydotool key shift+.", lambda: run_ydotool_key(["shift+."])),
        "keycodes": (
            "ydotool key 42:1 52:1 52:0 42:0",
            lambda: run_ydotool_key(["42:1", "52:1", "52:0", "42:0"]),
        ),
        "pynput": (
            "pynput shift + ';'",
            lambda: run_pynput_script(
                "import time\nfrom pynput.keyboard import Controller, Key\n"
                "k = Controller()\nwith k.pressed(Key.shift):\n"
                "    time.sleep(0.05)\n    k.press(';')\n    k.release(';')\n"
            ),
        ),
    },
    ";": {
        "type": ("ydotool type ';'", lambda: run_ydotool_type(";")),
        "shift_comma": ("ydotool key shift+,", lambda: run_ydotool_key(["shift+,"])),
        "shift_comma_name": ("ydotool key shift+comma", lambda: run_ydotool_key(["shift+comma"])),
        "keycodes": (
            "ydotool key 42:1 51:1 51:0 42:0",
            lambda: run_ydotool_key(["42:1", "51:1", "51:0", "42:0"]),
        ),
        "pynput": (
            "pynput shift + ','",
            lambda: run_pynput_script(
                "import time\nfrom pynput.keyboard import Controller, Key\n"
                "k = Controller()\nwith k.pressed(Key.shift):\n"
                "    time.sleep(0.05)\n    k.press(',')\n    k.release(',')\n"
            ),
        ),
    },
    "$": {
        "alt_r_4": ("ydotool key alt_r+4", lambda: run_ydotool_key(["alt_r+4"])),
        "ALT_R_4": ("ydotool key ALT_R+4", lambda: run_ydotool_key(["ALT_R+4"])),
        "alt_r_4_delay": (
            "ydotool key --delay 50 alt_r+4",
            lambda: run_ydotool_key(["alt_r+4"], delay_ms=50, key_delay_ms=50),
        ),
        "type": ("ydotool type '$'", lambda: run_ydotool_type("$")),
        "altgr_4": ("ydotool key altgr+4", lambda: run_ydotool_key(["altgr+4"])),
        "rightalt_4": ("ydotool key rightalt+4", lambda: run_ydotool_key(["rightalt+4"])),
        "ctrl_alt_4": ("ydotool key ctrl+alt+4", lambda: run_ydotool_key(["ctrl+alt+4"])),
        "keycodes": (
            f"ydotool key {' '.join(ALTGR_4_KEYCODES)}",
            lambda: run_ydotool_key(ALTGR_4_KEYCODES, key_delay_ms=50),
        ),
        "pynput": (
            "pynput AltGr + '4'",
            lambda: run_pynput_script(
                "import time\nfrom pynput.keyboard import Controller, Key\n"
                "k = Controller()\nwith k.pressed(Key.alt_gr):\n"
                "    time.sleep(0.05)\n    k.press('4')\n    k.release('4')\n"
            ),
        ),
    },
    "*": {
        "type": ("ydotool type '*'", lambda: run_ydotool_type("*")),
        "shift_backslash": (
            "ydotool key shift+backslash",
            lambda: run_ydotool_key(["shift+backslash"]),
        ),
        "shift_backslash_char": (
            "ydotool key shift+\\\\",
            lambda: run_ydotool_key(["shift+\\"]),
        ),
        "shift_quote": ("ydotool key shift+'", lambda: run_ydotool_key(["shift+'"])),
        "shift_apostrophe": ("ydotool key shift+apostrophe", lambda: run_ydotool_key(["shift+apostrophe"])),
        "shift_acute": ("ydotool key shift+´", lambda: run_ydotool_key(["shift+´"])),
        "keycodes": (
            "ydotool key 42:1 43:1 43:0 42:0",
            lambda: run_ydotool_key(["42:1", "43:1", "43:0", "42:0"]),
        ),
        "pynput": (
            "pynput shift + \"'\"",
            lambda: run_pynput_script(
                "import time\nfrom pynput.keyboard import Controller, Key\n"
                "k = Controller()\nwith k.pressed(Key.shift):\n"
                "    time.sleep(0.05)\n    k.press(\"'\")\n    k.release(\"'\")\n"
            ),
        ),
    },
    "?": {
        "shift_minus": ("ydotool key shift+-", lambda: run_ydotool_key(["shift+-"])),
        "shift_minus_name": ("ydotool key shift+minus", lambda: run_ydotool_key(["shift+minus"])),
        "shift_section": ("ydotool key shift+§", lambda: run_ydotool_key(["shift+§"])),
        "type": ("ydotool type '?'", lambda: run_ydotool_type("?")),
    },
    "-": {
        "slash": ("ydotool key /", lambda: run_ydotool_key(["/"])),
        "slash_name": ("ydotool key slash", lambda: run_ydotool_key(["slash"])),
        "KEY_SLASH": ("ydotool key KEY_SLASH", lambda: run_ydotool_key(["KEY_SLASH"])),
        "type": ("ydotool type '-'", lambda: run_ydotool_type("-")),
        "minus": ("ydotool key -- -", lambda: run_ydotool_key(["--", "-"])),
    },
    "+": {
        "type": ("ydotool type '+'", lambda: run_ydotool_type("+")),
        "base_minus": ("ydotool key -", lambda: run_ydotool_key(["-"])),
        "base_minus_name": ("ydotool key minus", lambda: run_ydotool_key(["minus"])),
        "base_minus_literal": ("ydotool key -- -", lambda: run_ydotool_key(["--", "-"])),
        "shift_acute": ("ydotool key shift+´", lambda: run_ydotool_key(["shift+´"])),
        "shift_grave": ("ydotool key shift+`", lambda: run_ydotool_key(["shift+`"])),
        "shift_equal": ("ydotool key shift+=", lambda: run_ydotool_key(["shift+="])),
        "shift_plus": ("ydotool key shift+plus", lambda: run_ydotool_key(["shift+plus"])),
        "keycodes": (
            "ydotool key 42:1 40:1 40:0 42:0",
            lambda: run_ydotool_key(["42:1", "40:1", "40:0", "42:0"]),
        ),
        "pynput": (
            "pynput shift + ´",
            lambda: run_pynput_script(
                "import time\nfrom pynput.keyboard import Controller, Key\n"
                "k = Controller()\nwith k.pressed(Key.shift):\n"
                "    time.sleep(0.05)\n    k.press('´')\n    k.release('´')\n"
            ),
        ),
    },
    "\\": {
        "us_layout_type": (
            "gsettings US + ydotool type '\\'",
            lambda: run_ydotool_type_us_layout_backslash(),
        ),
        "type": ("ydotool type '\\\\'", lambda: run_ydotool_type("\\")),
        "alt_r_backslash": ("ydotool key alt_r+\\", lambda: run_ydotool_key(["alt_r+\\"])),
        "alt_r_backslash_name": ("ydotool key alt_r+backslash", lambda: run_ydotool_key(["alt_r+backslash"])),
        "alt_r_key_backslash": ("ydotool key alt_r+KEY_BACKSLASH", lambda: run_ydotool_key(["alt_r+KEY_BACKSLASH"])),
        "alt_r_102nd": ("ydotool key alt_r+102nd", lambda: run_ydotool_key(["alt_r+102nd"])),
        "ALT_R_102ND": ("ydotool key ALT_R+102ND", lambda: run_ydotool_key(["ALT_R+102ND"])),
        "alt_r_key_102nd": ("ydotool key alt_r+KEY_102ND", lambda: run_ydotool_key(["alt_r+KEY_102ND"])),
        "ctrl_alt_102nd": ("ydotool key ctrl+alt+102nd", lambda: run_ydotool_key(["ctrl+alt+102nd"])),
        "alt_r_lt": ("ydotool key alt_r+<", lambda: run_ydotool_key(["alt_r+<"])),
        "alt_r_less": ("ydotool key alt_r+less", lambda: run_ydotool_key(["alt_r+less"])),
        "backslash": ("ydotool key -- \\", lambda: run_ydotool_key(["--", "\\"])),
        "shift_backslash": ("ydotool key shift+\\", lambda: run_ydotool_key(["shift+\\"])),
        "keycodes": (
            "ydotool key 100:1 86:1 86:0 100:0",
            lambda: run_ydotool_key(["100:1", "86:1", "86:0", "100:0"]),
        ),
        "pynput": (
            "pynput AltGr + '<'",
            lambda: run_pynput_script(
                "import time\nfrom pynput.keyboard import Controller, Key\n"
                "k = Controller()\nwith k.pressed(Key.alt_gr):\n"
                "    time.sleep(0.05)\n    k.press('<')\n    k.release('<')\n"
            ),
        ),
    },
    "|": {
        "alt_r_equal": ("ydotool key alt_r+=", lambda: run_ydotool_key(["alt_r+="])),
        "alt_r_equal_name": ("ydotool key alt_r+equal", lambda: run_ydotool_key(["alt_r+equal"])),
        "alt_r_KEY_EQUAL": ("ydotool key alt_r+KEY_EQUAL", lambda: run_ydotool_key(["alt_r+KEY_EQUAL"])),
        "alt_r_acute": ("ydotool key alt_r+´", lambda: run_ydotool_key(["alt_r+´"])),
        "alt_r_grave": ("ydotool key alt_r+`", lambda: run_ydotool_key(["alt_r+`"])),
        "type": ("ydotool type '|'", lambda: run_ydotool_type("|")),
        "alt_r_bar": ("ydotool key alt_r+bar", lambda: run_ydotool_key(["alt_r+bar"])),
        "alt_r_pipe": ("ydotool key alt_r+|", lambda: run_ydotool_key(["alt_r+|"])),
        "keycodes": (
            "ydotool key 100:1 13:1 13:0 100:0",
            lambda: run_ydotool_key(["100:1", "13:1", "13:0", "100:0"]),
        ),
        "pynput": (
            "pynput AltGr + ´",
            lambda: run_pynput_script(
                "import time\nfrom pynput.keyboard import Controller, Key\n"
                "k = Controller()\nwith k.pressed(Key.alt_gr):\n"
                "    time.sleep(0.05)\n    k.press('´')\n    k.release('´')\n"
            ),
        ),
    },
}


def main():
    parser = argparse.ArgumentParser(description="Automatisk ydotool tegn-test")
    parser.add_argument("--char", required=True, choices=list(CHAR_METHODS))
    parser.add_argument("--method", help="Kør kun én metode")
    parser.add_argument("--focus-only", action="store_true")
    parser.add_argument("--skip-focus", action="store_true", help="Spring fokus-check over")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Hurtig: countdown 1s, stop ved første OK metode",
    )
    parser.add_argument("--countdown", type=int, default=2, help="Sekunder før start (default 2)")
    args = parser.parse_args()

    if args.fast:
        args.countdown = min(args.countdown, 1)

    expected = args.char
    all_methods = CHAR_METHODS[expected]

    print(f"Tegn-test: {expected!r} (automatisk)")
    print(f"YDOTOOL_SOCKET={YDOTOOL_SOCKET or '(not set)'}")
    print(f"XDG_SESSION_TYPE={os.environ.get('XDG_SESSION_TYPE')}")
    if not YDOTOOL_SOCKET:
        print("Advarsel: ydotoold socket ikke fundet.")

    if args.method:
        if args.method not in all_methods:
            print(f"Ukendt metode {args.method!r}. Valg: {', '.join(all_methods)}", file=sys.stderr)
            sys.exit(2)
        selected = {args.method: all_methods[args.method]}
    else:
        selected = all_methods

    print("\nKlik i dette terminalvindue.")
    countdown(args.countdown, f"Tester {expected!r}")

    if not args.skip_focus and not wait_for_focus():
        sys.exit(1)

    if args.focus_only:
        return

    methods = [(mid, desc, fn) for mid, (desc, fn) in ((k, selected[k]) for k in selected)]
    run_char_tests(expected, methods, stop_on_first_ok=args.fast)


if __name__ == "__main__":
    main()
