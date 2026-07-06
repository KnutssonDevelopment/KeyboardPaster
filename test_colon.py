#!/usr/bin/env python3
"""Wrapper — brug: python3 test_char.py --char ':'"""
import sys

if __name__ == "__main__":
    sys.argv = ["test_char.py", "--char", ":"] + sys.argv[1:]
    from test_char import main

    main()
