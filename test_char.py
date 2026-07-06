#!/usr/bin/env python3
"""
Automatisk console-test af enkelttegn via ydotool (dansk tastatur, Wayland).

Klik i terminalen ved nedtælling — programmet sender taster og læser selv resultatet.

  python3 test_char.py --char ':'
  python3 test_char.py --char '$'
  python3 test_char.py --char ':' --method shift_dot_char
  python3 test_char.py --char '$' --focus-only
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
}


def main():
    parser = argparse.ArgumentParser(description="Automatisk ydotool tegn-test")
    parser.add_argument("--char", required=True, choices=list(CHAR_METHODS))
    parser.add_argument("--method", help="Kør kun én metode")
    parser.add_argument("--focus-only", action="store_true")
    parser.add_argument("--countdown", type=int, default=5, help="Sekunder før start (default 5)")
    args = parser.parse_args()

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

    if not wait_for_focus():
        sys.exit(1)

    if args.focus_only:
        return

    methods = [(mid, desc, fn) for mid, (desc, fn) in ((k, selected[k]) for k in selected)]
    run_char_tests(expected, methods)


if __name__ == "__main__":
    main()
