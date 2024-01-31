## Building on Windows

To build an .exe on windows follow these steps to avoid having the exe flagged as a virus.

This follows the instructions listed here to avoid having the .exe flagged as a virus.

https://plainenglish.io/blog/pyinstaller-exe-false-positive-trojan-virus-resolved-b33842bd3184

1. Ensure you have visual studio installed on your computer.
2. `git clone https://github.com/pyinstaller/pyinstaller.git`
3. `cd pyinstaller/bootloader`
4. `python.exe ./waf all --target-arch=64bit`
6. `pip install .`
5. `cd ../`
7. run `./windows_build.bat`
8. Upload the .exe to https://www.virustotal.com/ to check


* Note last pyinstaller git commit hash to work `249d8fc84fc3707fe47b1a5b9a006baf3b3657ec`
