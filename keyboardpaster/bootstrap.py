import os

from keyboardpaster.shared_resources import APP_WM_CLASS, app_icon_path


def configure_kivy_environment() -> None:
    if getattr(configure_kivy_environment, "_done", False):
        return

    os.environ["SDL_MOUSE_FOCUS_CLICKTHROUGH"] = "1"
    os.environ.setdefault("SDL_VIDEO_X11_WMCLASS", APP_WM_CLASS)
    os.environ.setdefault("SDL_VIDEO_WAYLAND_WMCLASS", APP_WM_CLASS)

    icon = app_icon_path()
    if icon is not None:
        from kivy.config import Config

        Config.set("kivy", "window_icon", str(icon))

    configure_kivy_environment._done = True  # type: ignore[attr-defined]
