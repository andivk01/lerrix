import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from lib.cli.LerrixCLI import LerrixCLI

def main():
    LerrixCLI().run()
if __name__ == "__main__":
    main()