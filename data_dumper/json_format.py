#!/usr/bin/env python3

import json
import sys


json.dump(json.load(sys.stdin), sys.stdout, indent = "\t", sort_keys = True)
