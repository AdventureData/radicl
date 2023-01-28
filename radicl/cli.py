# coding: utf-8

import argparse
import os

from radicl import __version__
from radicl.interface import RADICL
from radicl.ui_tools import Messages

debug = False

# Get the screen outputter
out = Messages()


def main():
    logo = 'RADICL - RAD INTERFACE TO THE COMMANDLINE'
    hdr = '=' * len(logo)
    hdr = logo + '\n' + hdr
    parser = argparse.ArgumentParser(
        description="CLI script for live interactions with the Lyte probe.")
    parser.add_argument('--version', action='version',
                        version=('%(prog)s {version}'
                                 '').format(version=__version__))
    parser.add_argument('-d', '--debug', action='store_true', help='Log debug statements')
    args = parser.parse_args()

    # Clear the screen in console
    if 'nt' in os.name:
        os.system('cls')  # for Windows
    else:
        os.system('clear')  # for Linux/OS X

    out.msg("")
    out.msg(hdr)

    # Information
    out.headline("\nWELCOME TO THE LYTE PROBE CLI")
    out.warn("\n\tWarning: This CLI is not meant to run with the mobile app."
             "\n\tPlease make sure your RAD app is closed out.")
    out.msg("\nThings you can do with this tool:\n", 'header')
    out.msg("\t* Plot various data from the probe." +
            "\n\t* Write various data to a file. (In development)" +
            "\n\t* Modify probe settings.  (In development)" +
            "\n\t* Update the firmware (In development)\n")

    # try:
    cli = RADICL(debug=args.debug)
    cli.run()


if __name__ == '__main__':
    main()
