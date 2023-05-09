from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="KeyboardPaster",
    version="0.1.6",
    author="Brian Knutsson",
    author_email="development@knutsson.it",
    description="A Python package to type text using the keyboard module",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/KnutssonDevelopment/KeyboardPaster",
    packages=find_packages(),
    package_data={
        "keyboardpaster": ["keyboardpaster_app.kv"],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.10",
    install_requires=[
        "pynput",
        "kivy",
        "kivymd",
    ],
    extras_require={
        "windows": ["pywin32"],
        "linux": ["setuptools"],
        "macos": ["setuptools"],
    },
    entry_points={
        "console_scripts": [
            "keyboardpaster=keyboardpaster.app:main",
        ],
    },
)