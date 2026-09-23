import shutil
import subprocess
import sys
from pathlib import Path

from keyboardpaster.shared_resources import APP_WM_CLASS, app_icon_path


def _desktop_exec_command() -> str:
    project_root = Path(__file__).resolve().parent.parent
    main_py = project_root / "main.py"
    if main_py.is_file() and (project_root / "setup.py").is_file():
        return f"{sys.executable} {main_py}"

    entry_point = shutil.which("keyboardpaster")
    if entry_point:
        return entry_point

    return sys.executable


def _remove_broken_hicolor_override() -> None:
    """Remove incomplete user hicolor index that breaks other apps' icons."""
    icon_theme_root = Path.home() / ".local/share/icons/hicolor"
    index_file = icon_theme_root / "index.theme"
    if not index_file.is_file():
        return

    try:
        text = index_file.read_text(encoding="utf-8")
    except OSError:
        return

    # Only remove the incomplete theme we previously generated.
    if "Directories=256x256/apps" not in text:
        return
    if "16x16/apps" in text or "scalable/apps" in text:
        return

    try:
        index_file.unlink()
    except OSError:
        pass

    cache_file = icon_theme_root / "icon-theme.cache"
    try:
        cache_file.unlink()
    except OSError:
        pass


def ensure_user_desktop_entry() -> None:
    if sys.platform != "linux":
        return

    icon = app_icon_path()
    if icon is None:
        return

    _remove_broken_hicolor_override()

    apps_dir = Path.home() / ".local/share/applications"
    data_dir = Path.home() / ".local/share/keyboardpaster"
    apps_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    # Keep our icon outside the hicolor theme tree so we never break system icons.
    installed_icon = data_dir / "keyboardpaster.png"
    if not installed_icon.exists() or icon.read_bytes() != installed_icon.read_bytes():
        shutil.copy2(icon, installed_icon)

    desktop_path = apps_dir / f"{APP_WM_CLASS}.desktop"
    desktop_text = "\n".join(
        [
            "[Desktop Entry]",
            "Version=1.0",
            "Type=Application",
            "Name=Keyboard Paster",
            "Comment=Type text using simulated keyboard input",
            f"Exec={_desktop_exec_command()}",
            f"Icon={installed_icon}",
            "Terminal=false",
            "Categories=Utility;",
            f"StartupWMClass={APP_WM_CLASS}",
            "",
        ]
    )
    existing = desktop_path.read_text(encoding="utf-8") if desktop_path.exists() else ""
    if existing != desktop_text:
        desktop_path.write_text(desktop_text, encoding="utf-8")
        if shutil.which("update-desktop-database"):
            subprocess.run(
                ["update-desktop-database", str(apps_dir)],
                check=False,
                capture_output=True,
            )
