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


def _ensure_hicolor_theme_index(icon_theme_root: Path) -> None:
    index_file = icon_theme_root / "index.theme"
    if index_file.exists():
        return
    index_file.write_text(
        "\n".join(
            [
                "[Icon Theme]",
                "Name=Hicolor",
                "Comment=Fallback icon theme",
                "Directories=256x256/apps",
                "",
                "[256x256/apps]",
                "Size=256",
                "Context=Applications",
                "Type=Fixed",
                "",
            ]
        ),
        encoding="utf-8",
    )


def ensure_user_desktop_entry() -> None:
    if sys.platform != "linux":
        return

    icon = app_icon_path()
    if icon is None:
        return

    apps_dir = Path.home() / ".local/share/applications"
    icon_theme_root = Path.home() / ".local/share/icons/hicolor"
    icon_dir = icon_theme_root / "256x256/apps"
    apps_dir.mkdir(parents=True, exist_ok=True)
    icon_dir.mkdir(parents=True, exist_ok=True)
    _ensure_hicolor_theme_index(icon_theme_root)

    installed_icon = icon_dir / f"{APP_WM_CLASS}.png"
    icon_changed = (
        not installed_icon.exists()
        or icon.read_bytes() != installed_icon.read_bytes()
    )
    if icon_changed:
        shutil.copy2(icon, installed_icon)
        if shutil.which("gtk-update-icon-cache"):
            subprocess.run(
                ["gtk-update-icon-cache", "-f", "-t", str(icon_theme_root)],
                check=False,
                capture_output=True,
            )

    desktop_path = apps_dir / f"{APP_WM_CLASS}.desktop"
    desktop_text = "\n".join(
        [
            "[Desktop Entry]",
            "Version=1.0",
            "Type=Application",
            "Name=Keyboard Paster",
            "Comment=Type text using simulated keyboard input",
            f"Exec={_desktop_exec_command()}",
            f"Icon={APP_WM_CLASS}",
            "Terminal=false",
            "Categories=Utility;",
            f"StartupWMClass={APP_WM_CLASS}",
            "",
        ]
    )
    if desktop_path.read_text(encoding="utf-8") if desktop_path.exists() else "" != desktop_text:
        desktop_path.write_text(desktop_text, encoding="utf-8")
        if shutil.which("update-desktop-database"):
            subprocess.run(
                ["update-desktop-database", str(apps_dir)],
                check=False,
                capture_output=True,
            )
