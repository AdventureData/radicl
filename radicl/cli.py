# coding: utf-8

import os
from radicl.radicl import RADICL
from radicl.ui_tools import Messages
debug = False

# Get the screen outputter
out=Messages()


logo = """\
██████╗  █████╗ ██████╗
██╔══██╗██╔══██╗██╔══██╗
██████╔╝███████║██║  ██║
██╔══██╗██╔══██║██║  ██║
██║  ██║██║  ██║██████╔╝
╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝

 ██████╗ ██████╗ ███╗   ███╗███╗   ███╗ █████╗ ███╗   ██╗██████╗
██╔════╝██╔═══██╗████╗ ████║████╗ ████║██╔══██╗████╗  ██║██╔══██╗
██║     ██║   ██║██╔████╔██║██╔████╔██║███████║██╔██╗ ██║██║  ██║
██║     ██║   ██║██║╚██╔╝██║██║╚██╔╝██║██╔══██║██║╚██╗██║██║  ██║
╚██████╗╚██████╔╝██║ ╚═╝ ██║██║ ╚═╝ ██║██║  ██║██║ ╚████║██████╔╝
 ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝

██╗     ██╗███╗   ██╗███████╗
██║     ██║████╗  ██║██╔════╝
██║     ██║██╔██╗ ██║█████╗
██║     ██║██║╚██╗██║██╔══╝
███████╗██║██║ ╚████║███████╗
╚══════╝╚═╝╚═╝  ╚═══╝╚══════╝

██╗███╗   ██╗████████╗███████╗██████╗ ███████╗ █████╗  ██████╗███████╗
██║████╗  ██║╚══██╔══╝██╔════╝██╔══██╗██╔════╝██╔══██╗██╔════╝██╔════╝
██║██╔██╗ ██║   ██║   █████╗  ██████╔╝█████╗  ███████║██║     █████╗
██║██║╚██╗██║   ██║   ██╔══╝  ██╔══██╗██╔══╝  ██╔══██║██║     ██╔══╝
██║██║ ╚████║   ██║   ███████╗██║  ██║██║     ██║  ██║╚██████╗███████╗
╚═╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝
"""

def main():
    #Clear the screen in console
    if 'nt' in os.name:
        os.system('cls')  # for Windows
    else:
        os.system('clear')  # for Linux/OS X

    out.msg("")
    out.msg(logo)

    #Information
    out.headline("\nWELCOME TO THE LYTE PROBE CLI")
    out.warn("\n\tWarning: This CLI is not meant to run with the mobile app."
            "\n\tPlease make sure your RAD app is closed out.")
    out.msg("\nThings you can do with this tool:\n",'header')
    out.msg("\t* Plot various data from the probe."+
            "\n\t* Write various data to a file. (In development)"+
            "\n\t* Modify probe settings.  (In development)"+
            "\n\t* Update the firmware (In development)\n")

    # try:
    cli = RADICL()
    cli.run()


if __name__ == '__main__':
    main()
