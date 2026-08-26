#!/usr/bin/env python3
#
# config.py — Application configuration, CLI parsing, CSS/strings loading
#
# (c) 2022–2026, Rosandi & Arief Ritonga
#

import sys
import os
import json

_HERE = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(_HERE, 'assets')

if not os.path.isdir(ASSETS_DIR):
    ASSETS_DIR = _HERE

LOGO_PATH = os.path.join(ASSETS_DIR, 'newlogo.png')

config = {
    'gui': {
        'filter': False,
        'low_freq': 10.0,
        'high_freq': 30.0,
        'order': 2,
        'zoom': 200,
        'threshold': 0.0,
        'css': 'seismolog.css',
        'lang': 'en',
        'winmode': 'max',
        'hold_init_screen': 1,
    }
}

file_to_open = ''
css = ''
strings = {}
doc_url = ''


def load_config(path):
    """Load a JSON config file and merge into `config`. Returns True on success."""
    try:
        with open(path) as f:
            data = json.load(f)
        if 'gui' in data:
            config.update(data)
            return True
    except Exception as e:
        print(f'[config] failed to load {path}: {e}')
    return False


def save_config(path):
    """Persist `config` to a JSON file."""
    with open(path, 'w') as f:
        json.dump(config, f, indent=2)


def parse_cli_args(argv):
    """Parse sys.argv-style arguments and update `config` / `file_to_open`."""
    global file_to_open
    for arg in argv[1:]:
        if arg.startswith('gui='):
            # format: gui=key:value
            sarg = arg.replace('gui=', '').split(':')
            if len(sarg) == 2:
                config['gui'][sarg[0]] = sarg[1]
        elif os.path.exists(arg):
            file_to_open = arg


def load_assets():
    """Load CSS stylesheet and UI strings. Call once at startup."""
    global css, strings, doc_url

    basepath = os.path.dirname(os.path.realpath(__file__))
    lang = config['gui']['lang']

    css_name = config['gui']['css']
    css_candidates = [
        os.path.join(ASSETS_DIR, css_name),
        os.path.join(basepath, css_name),
        css_name,
    ]
    for candidate in css_candidates:
        if os.path.exists(candidate):
            with open(candidate) as c:
                css = c.read()
            break

    strings_candidates = [
        os.path.join(ASSETS_DIR, 'strings.json'),
        os.path.join(basepath, 'strings.json'),
    ]
    for candidate in strings_candidates:
        if os.path.exists(candidate):
            with open(candidate) as fl:
                all_strings = json.load(fl)
            strings = all_strings.get(lang, all_strings.get('en', {}))
            break

    doc_path = os.path.join(basepath, f'doc-{lang}', 'index.html')
    doc_url = f'file://{doc_path}'
