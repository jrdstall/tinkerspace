"""CLI entrypoint module for python -m iw.cli."""

import sys
from iw.cli.main import main

if __name__ == "__main__":
    sys.exit(main())
