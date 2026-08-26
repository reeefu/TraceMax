#!/usr/bin/env python3

#---------------------------------
# Seismic Manual And Automatic Picking "TRACEMAX"
#
# (c) 2022–2026, Rosandi & Arief Ritonga
#
# ariefrahman5317@gmail.com
#


import sys
import os

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from main import main

if __name__ == '__main__':
    main()
