from pathlib import Path

app_version = "0.1.26"
APP_WM_CLASS = "keyboardpaster"


def app_icon_path() -> Path | None:
    package_dir = Path(__file__).resolve().parent
    for candidate in (
        package_dir / "res/images/keyboardpaster.png",
        package_dir.parent / "res/images/keyboardpaster.png",
    ):
        if candidate.is_file():
            return candidate
    return None
