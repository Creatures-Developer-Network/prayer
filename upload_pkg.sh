#!/bin/bash
python3 -m venv "venv"
venv/bin/python3 -m pip install --upgrade twine
venv/bin/python3 -m twine upload dist/*
