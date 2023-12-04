#!/usr/bin/env python
"""
This takes doctest files and turns them into standalone scripts.
"""

import doctest, sys, os

__author__ = "Gavin Huttley"
__copyright__ = "Copyright 2007-2011, The Cogent Project"
__contributors__ = ["Gavin Huttley", "Peter Maxwell"]
__license__ = "BSD"
__version__ = "1.3.0.dev"
__maintainer__ = "Gavin Huttley"
__email__ = "gavin.huttley@anu.edu.au"
__status__ = "Production"

for filename in sys.argv[1:]:
    print(filename)
    (name, suffix) = os.path.splitext(filename)
    if suffix != ".rst":
        print("not a .rst file")
        continue
    with open(filename, "r") as f:
        s = "".join(f.readlines())
    s = doctest.script_from_examples(s)
    with open(f"{name}.py", "w") as f:
        f.write(s)
    print("->", f"{name}.py")
