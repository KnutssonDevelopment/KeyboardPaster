# KeyboardPaster

A Python package to type text using the keyboard module. This is useful in situation where copy and paste is prohibited

## Features
- Paste 10 different strings using the keyboard
- Save string for future usage

## Install (Linux / pipx)

```bash
pipx install keyboardpaster
```

KivyMD is pinned to 1.x so pipx does not need to compile `pycairo`.

If you install KivyMD 2.x yourself, or a dependency pulls in `pycairo`, install Cairo headers first:

```bash
sudo apt install libcairo2-dev pkg-config
```

On GNOME Wayland you also need `ydotool` / `ydotoold` for typing into other apps.

## Future features
- Paste images as base64 code

## Changes
### v0.1.26
- BUGFIX: Pin KivyMD to 1.x so pipx install does not require pycairo/Cairo headers

### v0.1.25
- BUGFIX: Dropbox menu resulted in crash when multiple profiles were available

### v0.1.24
- BUGFIX: Corrected Python requirement

### v0.1.23
- BUGFIX: Corrected Python requirement

### v0.1.22
- FEATURE: Added Python 3.13 support

### v0.1.21
- BUGFIX: Would not correctly load secret settings
- BUGFIX: Multiple profiles would not load

### v0.1.20
- UPDATE: Changed requirement to python version 3.12

### v0.1.19
- BUGFIX: Version Bump

### v0.1.18
- FEATURE: Added a possibility to have multiple profiles.

### v0.1.17
- FEATURE: Added a button to put text into clipboard
- UPDATE: Changed the keyboard paste option into an icon

### v0.1.16
- FEATURE: Changes the launcher to run as a gui application and not show the command line when executed

### v0.1.15
- BUGFIX: Fixed the issue where the app would not start when the saved_inputs could not load

### v0.1.14
- FEATURE: Passwords can not be hidden in the UI

### v0.1.13
- BUGFIX: Python executable was not correctly found by autoupdate

### v0.1.12
- BUGFIX: Moved version to a shared location, and added it to the title

### v0.1.11
- FEATURE: Added autoupdate feature

### v0.1.10
- FEATURE: Added a modifier delay to accommodate slow connects and bad remote applications
- BUGFIX: Fixed the none-working sliders and buttons

### v0.1.9
- FEATURE: Added the ability to send a return press after the text was typed
- BUGFIX: You are not able to click anything in the app if the app does not have focus 