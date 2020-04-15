#!/bin/bash
python3 -m venv "venv"
venv/bin/python3 -m pip install --upgrade setuptools wheel
venv/bin/python3 setup.py sdist bdist_wheel

