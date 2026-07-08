import os
import shutil
import socket
import subprocess
import time
from contextlib import contextmanager


def _patch_python_xlib_randr_errors() -> None:
    """Work around pip python-xlib 0.33 RandR errors missing XError base.

    Without this, pynput can raise AttributeError when using AltGr (e.g. '{' on DA_DK).
    """
    try:
        from Xlib.error import XError
        from Xlib.ext import randr
    except ImportError:
        return

    for name in ("BadRROutputError", "BadRRCrtcError", "BadRRModeError"):
        cls = getattr(randr, name, None)
        if cls is None or issubclass(cls, XError):
            continue
        setattr(randr, name, type(name, (XError,), {}))


_patch_python_xlib_randr_errors()

from pynput.keyboard import Controller, Key

keyboard = Controller()

GNOME_YDOTOOL_HELP = (
    "GNOME på Wayland kræver ydotool med en kørende daemon:\n\n"
    "sudo apt install ydotool ydotoold\n"
    "sudo usermod -aG input $USER\n"
    "(log ud og ind igen)\n\n"
    "Start daemonen:\n"
    'ydotoold --socket-path="$XDG_RUNTIME_DIR/.ydotool_socket" '
    '--socket-own="$(id -u):$(id -g)" &\n\n'
    'export YDOTOOL_SOCKET="$XDG_RUNTIME_DIR/.ydotool_socket"'
)


def is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def is_gnome() -> bool:
    return "gnome" in os.environ.get("XDG_CURRENT_DESKTOP", "").lower()


def is_wtype_available() -> bool:
    return shutil.which("wtype") is not None


def is_ydotool_available() -> bool:
    return shutil.which("ydotool") is not None


def is_ydotoold_installed() -> bool:
    return shutil.which("ydotoold") is not None


def _ydotool_socket_candidates() -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        if path and path not in seen:
            seen.add(path)
            candidates.append(path)

    if os.environ.get("YDOTOOL_SOCKET"):
        add(os.environ["YDOTOOL_SOCKET"])
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        add(os.path.join(runtime_dir, ".ydotool_socket"))
    add(os.path.join(os.path.expanduser("~"), ".ydotool_socket"))
    # Last resort only; often a stale socket from an old root-run daemon.
    add("/tmp/.ydotool_socket")
    return candidates


def _default_ydotool_socket() -> str:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir:
        return os.path.join(runtime_dir, ".ydotool_socket")
    return os.path.join(os.path.expanduser("~"), ".ydotool_socket")


def _ydotool_env(socket_path: str) -> dict[str, str]:
    env = os.environ.copy()
    env["YDOTOOL_SOCKET"] = socket_path
    return env


def _run_command(args: list[str], env: dict[str, str] | None = None) -> None:
    result = subprocess.run(args, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        message = stderr or (result.stdout or "").strip()
        if not message:
            message = f"Kommandoen fejlede: {' '.join(args)}"
        raise RuntimeError(message)


def _socket_owned_by_us(path: str) -> bool:
    try:
        return os.stat(path).st_uid == os.geteuid()
    except OSError:
        return False


def _ydotoold_backend_available(socket_path: str) -> bool:
    if not os.path.exists(socket_path) or not _socket_owned_by_us(socket_path):
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            sock.connect(socket_path)
        return True
    except OSError:
        return False


def _ydotoold_error_message(socket_path: str) -> str:
    tmp_socket = "/tmp/.ydotool_socket"
    if os.path.exists(tmp_socket) and not _socket_owned_by_us(tmp_socket):
        return (
            "ydotoold kører ikke. En gammel root-socket blokerer opstart:\n\n"
            "sudo rm /tmp/.ydotool_socket\n"
            f'ydotoold --socket-path="{socket_path}" '
            f'--socket-own="{os.getuid()}:{os.getgid()}" &\n\n'
            f'export YDOTOOL_SOCKET="{socket_path}"'
        )
    return GNOME_YDOTOOL_HELP


def _remove_stale_socket(path: str) -> None:
    if not os.path.exists(path) or not _socket_owned_by_us(path):
        return
    if _ydotoold_backend_available(path):
        return
    try:
        os.unlink(path)
    except OSError:
        pass


def _try_start_ydotoold_service() -> bool:
    if not shutil.which("systemctl"):
        return False
    for unit in ("ydotoold.service", "ydotoold.socket"):
        result = subprocess.run(
            ["systemctl", "--user", "start", unit],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            time.sleep(0.2)
            return True
    return False


def _start_ydotoold(socket_path: str) -> None:
    socket_dir = os.path.dirname(socket_path)
    if socket_dir:
        os.makedirs(socket_dir, exist_ok=True)
    _remove_stale_socket(socket_path)
    subprocess.Popen(
        [
            "ydotoold",
            f"--socket-path={socket_path}",
            f"--socket-own={os.getuid()}:{os.getgid()}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def ensure_ydotoold() -> str:
    def first_available_socket() -> str | None:
        for candidate in _ydotool_socket_candidates():
            if _ydotoold_backend_available(candidate):
                return candidate
        return None

    existing = first_available_socket()
    if existing:
        os.environ["YDOTOOL_SOCKET"] = existing
        return existing

    socket_path = _default_ydotool_socket()
    if not is_ydotoold_installed():
        raise RuntimeError(_ydotoold_error_message(socket_path))

    _try_start_ydotoold_service()
    started = first_available_socket()
    if not started:
        _start_ydotoold(socket_path)

    for _ in range(50):
        time.sleep(0.1)
        started = first_available_socket()
        if started:
            os.environ["YDOTOOL_SOCKET"] = started
            return started

    raise RuntimeError(_ydotoold_error_message(socket_path))


def _pynput_alt_gr_keys() -> tuple:
    # On Linux/X11, AltGr is Ctrl+Alt; Key.alt_gr triggers X11 RandR errors in pynput.
    if os.name == "nt":
        return (Key.alt_gr,)
    return (Key.ctrl, Key.alt)


def _type_char_pynput(
    char: str,
    delay: float,
    mod_delay: float,
    special_chars_shift: dict | None,
    special_chars_alt_gr: dict | None,
    layout: str = "EN_US",
) -> None:
    if layout == "DA_DK" and char in DA_DK_PLAIN_CHAR_KEYS:
        key = DA_DK_PLAIN_CHAR_KEYS[char]
        keyboard.press(key)
        keyboard.release(key)
    elif special_chars_shift and char in special_chars_shift:
        with keyboard.pressed(Key.shift):
            time.sleep(mod_delay)
            keyboard.press(special_chars_shift[char])
            keyboard.release(special_chars_shift[char])
    elif special_chars_alt_gr and char in special_chars_alt_gr:
        with keyboard.pressed(*_pynput_alt_gr_keys()):
            time.sleep(mod_delay)
            keyboard.press(special_chars_alt_gr[char])
            keyboard.release(special_chars_alt_gr[char])
    elif len(char) == 1 and char.isascii() and char.isupper():
        with keyboard.pressed(Key.shift):
            time.sleep(mod_delay)
            keyboard.press(char.lower())
            keyboard.release(char.lower())
    else:
        keyboard.press(char)
        keyboard.release(char)
    time.sleep(delay)


def type_string_pynput(
    text: str,
    delay: float = 0.1,
    mod_delay: float = 0.1,
    layout: str = "EN_US",
    end_line: bool = False,
    special_chars_shift: dict | None = None,
    special_chars_alt_gr: dict | None = None,
) -> None:
    for char in text:
        _type_char_pynput(char, delay, mod_delay, special_chars_shift, special_chars_alt_gr, layout)

    if end_line:
        keyboard.press(Key.enter)
        keyboard.release(Key.enter)


def type_string_wtype(text: str, delay: float = 0.1, end_line: bool = False) -> None:
    delay_ms = max(0, int(delay * 1000))
    args = ["wtype"]
    if delay_ms:
        args.extend(["-d", str(delay_ms)])
    args.append(text)

    _run_command(args)

    if end_line:
        _run_command(["wtype", "-k", "Return"])


SHIFT_KEYCODE = 42
ALTGR_KEYCODE = 100
ENTER_KEYCODE = 28

DA_DK_BASE_KEYCODE = {
    "§": 41,
    "1": 2,
    "2": 3,
    "3": 4,
    "4": 5,
    "5": 6,
    "6": 7,
    "7": 8,
    "8": 9,
    "9": 10,
    "0": 11,
    "´": 40,
    ";": 51,
    ",": 51,
    "<": 86,
    "-": 12,
    ".": 52,
}

EN_US_BASE_KEYCODE = {
    "`": 41,
    "1": 2,
    "2": 3,
    "3": 4,
    "4": 5,
    "5": 6,
    "6": 7,
    "7": 8,
    "8": 9,
    "9": 10,
    "0": 11,
    "-": 12,
    "=": 13,
    "[": 26,
    "]": 27,
    "\\": 43,
    ";": 39,
    "'": 40,
    ",": 51,
    ".": 52,
    "/": 53,
}

DA_DK_PLAIN_CHAR_KEYS = {
    # On Danish layout, apostrophe is on the physical backslash key (not the ø key).
    "'": "\\",
}

DA_DK_YDOTOOL_COMBO = {
    # ydotool 0.1.x: use literal key chars, not key names (dot/comma/period)
    ":": "shift+.",
    ";": "shift+,",
    # Danish * is shift on the physical backslash key; use literal \ not "backslash"
    "*": "shift+\\",
    # Danish ' is on the same physical key as * (xkb BKSL)
    "'": "\\",
    # Danish + key must be passed literally (ydotool key -- -)
    "+": "-",
    # Danish ? is shift on the same key as +
    "?": "shift+-",
    "=": "shift+0",
    # AltGr bracket/digit keys (verified: alt_r+4 works for $)
    "{": "alt_r+7",
    "}": "alt_r+0",
    "[": "alt_r+8",
    "]": "alt_r+9",
    # Danish | is AltGr on the key next to + (ydotool exposes it as '=')
    "|": "alt_r+=",
}


def _altgr_to_ydotool_combo(base: str) -> str | None:
    # ydotool 0.1.x: use ALT_R, not altgr/rightalt (verified for $ = alt_r+4)
    if len(base) == 1 and base.isascii() and base.isalnum():
        return f"alt_r+{base.lower()}"
    return None


def _keycode_press(modifier: int | None, keycode: int) -> list[str]:
    if modifier is None:
        return [f"{keycode}:1", f"{keycode}:0"]
    return [f"{modifier}:1", f"{keycode}:1", f"{keycode}:0", f"{modifier}:0"]


def _use_keycodes_for_modifier_base(base: str) -> bool:
    # ydotool combos (alt_r+7, shift+0) work for alnum keys; raw keycodes only for punctuation.
    return len(base) == 1 and not (base.isascii() and base.isalnum())


def _char_keycode_sequence(
    char: str,
    layout: str,
    special_chars_shift: dict | None,
    special_chars_alt_gr: dict | None,
) -> list[str] | None:
    if layout == "DA_DK" and char in DA_DK_YDOTOOL_COMBO:
        return None

    base_map = DA_DK_BASE_KEYCODE if layout == "DA_DK" else EN_US_BASE_KEYCODE

    if special_chars_shift and char in special_chars_shift:
        base = special_chars_shift[char]
        if _use_keycodes_for_modifier_base(base):
            keycode = base_map.get(base)
            if keycode is not None:
                return _keycode_press(SHIFT_KEYCODE, keycode)
        return None

    if special_chars_alt_gr and char in special_chars_alt_gr:
        base = special_chars_alt_gr[char]
        if _use_keycodes_for_modifier_base(base):
            keycode = base_map.get(base)
            if keycode is not None:
                return _keycode_press(ALTGR_KEYCODE, keycode)
        return None

    return None


YDOTOOL_KEY_NAME = {
    **{letter: letter for letter in "abcdefghijklmnopqrstuvwxyz"},
    **{str(digit): str(digit) for digit in range(10)},
}

DA_DK_YDOTOOL_BASE = dict(YDOTOOL_KEY_NAME)
EN_US_YDOTOOL_BASE = dict(YDOTOOL_KEY_NAME)


def _is_safe_ydotool_key(key: str) -> bool:
    return len(key) == 1 and key.isalnum()


def _layout_base_map(layout: str) -> dict[str, str]:
    if layout == "DA_DK":
        return DA_DK_YDOTOOL_BASE
    return EN_US_YDOTOOL_BASE


def _base_to_ydotool_key(base: str, layout: str) -> str:
    if len(base) == 1 and base.isascii() and base.isalnum():
        return base.lower()
    return _layout_base_map(layout).get(base, base)


def _char_to_ydotool_combo(
    char: str,
    layout: str,
    special_chars_shift: dict | None,
    special_chars_alt_gr: dict | None,
) -> str | None:
    if layout == "DA_DK" and char in DA_DK_YDOTOOL_COMBO:
        return DA_DK_YDOTOOL_COMBO[char]

    if special_chars_alt_gr and char in special_chars_alt_gr:
        return _altgr_to_ydotool_combo(special_chars_alt_gr[char])

    if special_chars_shift and char in special_chars_shift:
        base = special_chars_shift[char]
        if len(base) == 1:
            if base.isascii() and base.isalnum():
                return f"shift+{base.lower()}"
            # literal key char: shift+, shift+., shift+´, etc.
            return f"shift+{base}"
        return None

    if len(char) == 1 and char.isascii() and char.isupper():
        return f"shift+{char.lower()}"

    if len(char) == 1 and char.isascii() and char.islower():
        return char

    if len(char) == 1 and char.isascii() and char.isdigit():
        return char

    return None


def _ydotool_press_keycodes(
    keycodes: list[str],
    env: dict[str, str],
    key_delay_ms: int,
    mod_delay_ms: int = 0,
) -> None:
    if not keycodes:
        return
    args = ["ydotool", "key"]
    if mod_delay_ms:
        args.extend(["--delay", str(mod_delay_ms)])
    if key_delay_ms:
        args.extend(["--key-delay", str(key_delay_ms)])
    args.extend(keycodes)
    _run_command(args, env=env)


def _ydotool_press_combos(
    combos: list[str],
    env: dict[str, str],
    key_delay_ms: int,
    mod_delay_ms: int = 0,
) -> None:
    if not combos:
        return
    args = ["ydotool", "key"]
    if mod_delay_ms:
        args.extend(["--delay", str(mod_delay_ms)])
    if key_delay_ms:
        args.extend(["--key-delay", str(key_delay_ms)])
    # Needed for literal keys that look like options (e.g. "-").
    args.append("--")
    args.extend(combos)
    _run_command(args, env=env)


def _ydotool_type_plain(text: str, env: dict[str, str], key_delay_ms: int) -> None:
    if not text:
        return
    args = ["ydotool", "type"]
    if key_delay_ms:
        args.extend(["--key-delay", str(key_delay_ms)])
    args.extend(["--file", "-"])
    result = subprocess.run(
        args,
        input=text,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        message = stderr or (result.stdout or "").strip()
        if not message:
            message = f"Kommandoen fejlede: {' '.join(args)}"
        raise RuntimeError(message)


@contextmanager
def _temporary_gnome_us_keyboard():
    saved_sources = subprocess.check_output(
        ["gsettings", "get", "org.gnome.desktop.input-sources", "sources"],
        text=True,
    ).strip()
    saved_current = subprocess.check_output(
        ["gsettings", "get", "org.gnome.desktop.input-sources", "current"],
        text=True,
    ).strip()
    try:
        subprocess.run(
            [
                "gsettings", "set",
                "org.gnome.desktop.input-sources", "sources",
                "[('xkb', 'us')]",
            ],
            check=True,
        )
        subprocess.run(
            [
                "gsettings", "set",
                "org.gnome.desktop.input-sources", "current",
                "0",
            ],
            check=True,
        )
        # GNOME needs a moment to apply the layout before ydotool sends keys.
        time.sleep(0.25)
        yield
        time.sleep(0.05)
    finally:
        subprocess.run(
            [
                "gsettings", "set",
                "org.gnome.desktop.input-sources", "sources",
                saved_sources,
            ],
            check=True,
        )
        subprocess.run(
            [
                "gsettings", "set",
                "org.gnome.desktop.input-sources", "current",
                saved_current,
            ],
            check=True,
        )


def _ydotool_type_gnome_backslash(env: dict[str, str], key_delay_ms: int) -> None:
    # ydotool 0.1.x cannot hit Danish backslash; briefly switch to US layout.
    with _temporary_gnome_us_keyboard():
        _ydotool_type_plain("\\", env, key_delay_ms)


def _ydotool_send_backslash(
    env: dict[str, str],
    key_delay_ms: int,
    mod_delay_ms: int,
) -> None:
    if is_gnome():
        # Physical keyboard is Danish; layout spinner may still say EN_US.
        time.sleep(0.1)
        _ydotool_type_gnome_backslash(env, key_delay_ms)
        time.sleep(0.1)
        return
    _ydotool_press_combos(["\\"], env, key_delay_ms, mod_delay_ms)


def type_string_ydotool(
    text: str,
    delay: float = 0.1,
    mod_delay: float = 0.1,
    end_line: bool = False,
    special_chars_shift: dict | None = None,
    special_chars_alt_gr: dict | None = None,
    layout: str = "EN_US",
) -> None:
    socket_path = ensure_ydotoold()
    env = _ydotool_env(socket_path)
    key_delay_ms = max(12, int(delay * 1000))
    mod_delay_ms = max(0, int(mod_delay * 1000))
    pending: list[str] = []

    def flush_pending() -> None:
        if pending:
            _ydotool_press_combos(pending, env, key_delay_ms, mod_delay_ms)
            pending.clear()

    for char in text:
        if char == "\\":
            flush_pending()
            _ydotool_send_backslash(env, key_delay_ms, mod_delay_ms)
            continue

        keycodes = _char_keycode_sequence(char, layout, special_chars_shift, special_chars_alt_gr)
        if keycodes:
            flush_pending()
            _ydotool_press_keycodes(keycodes, env, key_delay_ms, mod_delay_ms)
            continue

        combo = _char_to_ydotool_combo(char, layout, special_chars_shift, special_chars_alt_gr)
        if combo is None:
            flush_pending()
            _ydotool_type_plain(char, env, key_delay_ms)
            continue

        pending.append(combo)

    flush_pending()

    if end_line:
        _run_command(
            ["ydotool", "key", f"{ENTER_KEYCODE}:1", f"{ENTER_KEYCODE}:0"],
            env=env,
        )


def _wayland_backend() -> str:
    if is_gnome():
        if is_ydotool_available():
            return "ydotool"
        raise RuntimeError(GNOME_YDOTOOL_HELP)

    if is_wtype_available():
        return "wtype"
    if is_ydotool_available():
        return "ydotool"

    raise RuntimeError(
        "Wayland kræver 'wtype' eller 'ydotool' for at sende tastaturinput. "
        "Installér med: sudo apt install ydotool ydotoold"
    )


def _input_backend() -> str:
    if is_wayland():
        return _wayland_backend()
    if is_ydotool_available():
        return "ydotool"
    return "pynput"


def type_string(
    text: str,
    delay: float = 0.1,
    mod_delay: float = 0.1,
    layout: str = "EN_US",
    end_line: bool = False,
    special_chars_shift: dict | None = None,
    special_chars_alt_gr: dict | None = None,
) -> None:
    backend = _input_backend()
    if backend == "wtype":
        type_string_wtype(text, delay=delay, end_line=end_line)
    elif backend == "ydotool":
        type_string_ydotool(
            text,
            delay=delay,
            mod_delay=mod_delay,
            end_line=end_line,
            special_chars_shift=special_chars_shift,
            special_chars_alt_gr=special_chars_alt_gr,
            layout=layout,
        )
    else:
        type_string_pynput(
            text,
            delay=delay,
            mod_delay=mod_delay,
            layout=layout,
            end_line=end_line,
            special_chars_shift=special_chars_shift,
            special_chars_alt_gr=special_chars_alt_gr,
        )
