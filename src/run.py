#!/usr/bin/env python3.8
"""
Shortcut script for calling app's main() function.
"""
import os

from app import main

if os.environ.get('RUN_MAIN') == 'true':
    HOST_IP = os.environ.get('EXTERNAL_IP')
    import pydevd_pycharm

    pydevd_pycharm.settrace(HOST_IP, port=8001, stdoutToServer=True, stderrToServer=True)
main.main()
