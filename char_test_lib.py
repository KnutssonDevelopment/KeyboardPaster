"""Shared console helpers for ydotool character tests."""

from __future__ import annotations

import os
import select
import subprocess
import sys
import termios
import time
import tty

YDOTOOL_SOCKET = os.environ.get(
    "YDOTOOL_SOCKET",
    "/tmp/.ydotool_socket" if os.path.exists("/tmp/.ydotool_socket") else "",
)


def ydotool_env() -> dict[str, str]:
    env = os.environ.copy()
    if YDOTOOL_SOCKET:
        env["YDOTOOL_SOCKET"] = YDOTOOL_SOCKET
    return env


def run_ydotool_key(args: list[str], delay_ms: int = 0, key_delay_ms: int = 0) -> tuple[int, str]:
    cmd = ["ydotool", "key"]
    if delay_ms:
        cmd.extend(["--delay", str(delay_ms)])
    if key_delay_ms:
        cmd.extend(["--key-delay", str(key_delay_ms)])
    cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True, env=ydotool_env())
    err = (result.stderr or result.stdout or "").strip()
    return result.returncode, err


def run_ydotool_type(text: str) -> tuple[int, str]:
    result = subprocess.run(
        ["ydotool", "type", "--file", "-"],
        input=text,
        capture_output=True,
        text=True,
        env=ydotool_env(),
    )
    err = (result.stderr or result.stdout or "").strip()
    return result.returncode, err


def run_ydotool_type_us_layout_backslash() -> tuple[int, str]:
    try:
        from keyboardpaster.keyboard_input import (
            _temporary_gnome_us_keyboard,
            _ydotool_env,
            _ydotool_type_gnome_backslash,
            ensure_ydotoold,
        )

        env = _ydotool_env(ensure_ydotoold())
        _ydotool_type_gnome_backslash(env, 12)
        return 0, ""
    except Exception as exc:
        return 1, str(exc)


def run_pynput_script(script: str) -> tuple[int, str]:
    venv_python = os.path.join(os.path.dirname(__file__), "venv", "bin", "python")
    python = venv_python if os.path.isfile(venv_python) else sys.executable
    result = subprocess.run([python, "-c", script], capture_output=True, text=True)
    err = (result.stderr or result.stdout or "").strip()
    return result.returncode, err


def countdown(seconds: int, message: str) -> None:
    if seconds <= 0:
        print(f"{message} — kører nu.", flush=True)
        return
    for remaining in range(seconds, 0, -1):
        print(f"\r{message} — starter om {remaining}s ...   ", end="", flush=True)
        time.sleep(1)
    print(f"\r{message} — kører nu.          ", flush=True)


def normalize_captured(text: str) -> str:
    return "".join(ch for ch in text if ch.isprintable())


def matches_expected(got: str, expected: str) -> bool:
    got = normalize_captured(got)
    return got == expected or expected in got


def flush_stdin() -> None:
    termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)


def capture_typed(
    send,
    timeout: float = 0.35,
    idle_exit_s: float = 0.06,
) -> str:
    """Put terminal in raw mode, run send(), read keys until idle or timeout."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        flush_stdin()
        exit_code, err = send()
        if err and not err.startswith("ydotool: notice"):
            label = "fejl" if exit_code else "info"
            print(f"  ({label}: {err.splitlines()[0][:80]})", flush=True)

        chars: list[str] = []
        deadline = time.monotonic() + timeout
        last_read: float | None = None
        while time.monotonic() < deadline:
            wait = min(0.03, deadline - time.monotonic())
            if wait <= 0:
                break
            ready, _, _ = select.select([sys.stdin], [], [], wait)
            if ready:
                chars.append(sys.stdin.read(1))
                last_read = time.monotonic()
            elif chars and last_read is not None and time.monotonic() - last_read >= idle_exit_s:
                break
        return "".join(chars)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        print()


def wait_for_focus(
    probe_char: str = "a",
    attempts: int = 5,
    pause_s: float = 0.4,
    capture_timeout: float = 0.35,
) -> bool:
    print("\n=== Fokus-check ===")

    for attempt in range(1, attempts + 1):
        print(f"[fokus] forsøg {attempt}/{attempts} ...", flush=True)
        got = capture_typed(
            lambda: run_ydotool_type(probe_char),
            timeout=capture_timeout,
        )
        print(f"  modtaget: {got!r}", flush=True)
        if probe_char in got:
            print("FOKUS OK\n", flush=True)
            return True
        if attempt < attempts:
            time.sleep(pause_s)

    print("FOKUS FEJL — ydotool når ikke terminalen. Tjek ydotoold.", flush=True)
    return False


def run_char_tests(
    expected: str,
    methods: list[tuple[str, str, callable]],
    pause_between_s: float = 0.15,
    capture_timeout: float = 0.35,
    stop_on_first_ok: bool = False,
) -> list[tuple[str, str, str]]:
    print(f"=== Tester {expected!r} ===\n")
    results: list[tuple[str, str, str]] = []

    for i, (method_id, description, send_fn) in enumerate(methods, 1):
        print(f"--- {i}/{len(methods)}: {description} ---")
        got = capture_typed(send_fn, timeout=capture_timeout)
        got_clean = normalize_captured(got)
        ok = matches_expected(got, expected)
        status = "OK" if ok else "FAIL"
        print(f"  {status}  {method_id}: got {got_clean!r} (forventet {expected!r})")
        results.append((method_id, got_clean, status))
        if ok and stop_on_first_ok:
            print("\n=== Første OK — stopper ===")
            print(f"  Brug: {method_id}")
            return results
        if i < len(methods):
            time.sleep(pause_between_s)

    print("\n=== Resultat ===")
    winners = []
    for method_id, got, status in results:
        print(f"  {status}  {method_id}: {got!r}")
        if status == "OK":
            winners.append(method_id)
    if winners:
        print(f"\nBrug: {winners[0]}")
    else:
        print("\nIngen metode virkede.")
    return results
