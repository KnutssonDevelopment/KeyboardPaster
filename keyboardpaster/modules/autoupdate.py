import subprocess
import requests
import pkg_resources
import sys


def check_for_update(package_name):
    """Check PyPI for the latest version of the package."""
    response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
    if response.status_code == 200:
        latest_version = response.json()['info']['version']
        return latest_version
    else:
        raise Exception("Failed to fetch package information from PyPI.")


def update_package(package_name):
    """Update the package using pip."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", package_name])


def autoupdate(package_name='keyboardpaster'):
    """Main function to check and update package."""
    try:
        installed_version = pkg_resources.get_distribution(package_name).version
        latest_version = check_for_update(package_name)

        print(f"Installed version: {installed_version}")
        print(f"Latest version: {latest_version}")

        if latest_version > installed_version:
            print(f"Updating {package_name} from version {installed_version} to {latest_version}...")
            update_package(package_name)
            print(f"{package_name} has been updated.")
        else:
            print(f"{package_name} is already up to date.")

    except Exception as e:
        print(f"Warning: {e}")
