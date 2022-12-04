import getpass
import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from lib.utils.DataKeeper import DataKeeper
from lib.cli.LerrixCLI import LerrixCLI

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ler-down.py')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-na', '--new-account', help='Create a new account file, it can be used for lerrix.py', action='store_true')
    parser.add_argument("-out", "--output", help="Output directory path")
    args = parser.parse_args()
    if args.new_account:
        if not args.output:
            print("Please specify the output file path")
            exit(1)
        usr = input("Username: ")
        out_file = os.path.join(args.output, f"{usr}")
        print("Output file will be saved at: " + os.path.abspath(out_file))
        pwd = getpass.getpass("Password: ")
        dkeeper = DataKeeper(out_file, LerrixCLI.ENC_KEY) # TODO enc_key should be retrieved from somewhere else
        dkeeper.store(pwd)
    else:
        print("Please give me something to do... (use -h param for help)")
else:
    print("This script is not meant to be imported")