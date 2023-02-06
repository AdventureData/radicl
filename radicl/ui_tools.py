# coding: utf-8

import logging
import sys
import textwrap
import coloredlogs
from colorama import init
from termcolor import colored
from threading import Timer


class Messages:
    init()

    def msg(self, str_msg, context_str=None):
        msg = colored(str_msg, 'white')
        print('\n' + msg)

    def dbg(self, str_msg):
        final_msg = colored('[DEBUG]: ', 'magenta', attrs=['bold'])
        final_msg += colored(str_msg, 'white')
        print('\n' + final_msg)

    def warn(self, str_msg):
        final_msg = colored('WARNING: ', 'yellow', attrs=['bold'])
        final_msg += colored(str_msg, 'white')
        print('\n' + final_msg)

    def error(self, str_msg):
        final_msg = colored('ERROR: ', 'red', attrs=['bold'])
        final_msg += colored(str_msg, 'red')
        print('\n' + final_msg)

    def critical(self, str_msg):
        final_msg = colored('ERROR: ', 'red', attrs=['bold'])
        final_msg += colored(str_msg + '\nExiting program...', 'red')
        print('\n' + final_msg)
        sys.exit()

    def respond(self, str_msg):
        final_msg = colored(str_msg, 'green')
        print('\t' + final_msg)

    def headline(self, str_msg):
        str_msg = str_msg.upper()
        final_msg = colored(str_msg, 'blue', attrs=['bold', 'underline'])
        print('\t' + final_msg)


def parse_func_list(func_list, identify_lst, ignore_keywords=[]):
    """
    Reads through a list of available methods and retrieves the methods that have
    matching words in the identify list, then it removes those keywords and Returns
    a dictionary of simplified method names with values as their corresponding
    method

    Args:
        func_list: A list of function names and functions
        identify_lst: A list of keywords to match with
        ignore_keywords: List contain keywords that will ignore functions with that keyword
    Returns:
        options: A dictionary that has keys that are simplified names of the methods, and values are the methods
    """
    options = {}
    ignore_keywords = [w.lower() for w in ignore_keywords]

    for f_name, fn in func_list:
        # Return a list of true when a word is found
        words_found = [True for w in identify_lst if w.lower()
                       in f_name.lower()]
        # If the number of the matches the number of keywords were
        # looking for
        if len(words_found) == len(identify_lst) and 'RAD' not in f_name:
            # Remove the keywords to form the simplified method name
            name = f_name
            for word in identify_lst:
                # print(f_name,word)
                name = name.replace(word, '')
            ignores = [True for ign in ignore_keywords if ign in name.lower()]
            if len(ignores) == 0:
                options[name.lower()] = fn

    return options


def parse_help(help_str):
    """
    Auto parses the help dialogs provided by developers in the doc strings.
    This is denoted by helpme - text and then a blank line.

    e.g.

    Function doc string
    helpme - more end user-friendly message about what this will do

    my arguments...

    """
    result = None

    if help_str is not None:
        if 'helpme' in help_str:
            z = help_str.split('helpme')
            result = z[-1].split('-')[-1].strip()

    return result


def print_helpme(help_str, help_dict):
    """
    Tries to help the user on request for help.

    Args:
        help_str -
        help_dict -
    """
    out_str = ""
    show_all = False
    no_help = 0
    no_doc = False

    # User provides specific help request
    if help_dict is not None:
        if "-" in help_str:
            h = help_str.split("-")
            k = ("".join(h[1:]).strip()).lower()
            if k in help_dict:
                formatted = textwrap.fill(long_str, width=width)

                for i, line in enumerate(formatted.split('\n')):
                    if i != 0:
                        k = ""
                    result += "\n{0:<20} {1:<20}\n".format(k, v)
            else:
                show_all = True
        else:
            show_all = True

        if show_all:
            for k, v in help_dict.items():
                if v is None:
                    no_help += 1
                    v = 'No help documentation.'

                out_str += '\n{0:<25} {1:<25}\n'.format(k, v)
        if no_help == len(help_dict.keys()):
            no_doc = True
    else:
        no_doc = True

    if no_doc:
        out_str = (
            '\nNo help documentation.\nPlease email info@adventuredata.com or file an issue at '
            'https://github.com/Adventuredata/radicl/issues\n')
        print(help_dict)

    # Doctor up the printout
    t = '\n{0:<20} {1:<20}\n'.format('OPTIONS', 'DESCRIPTION')
    print_able = '\n{0}'.format(colored(t, 'magenta', attrs=['bold']))
    print_able += out_str
    print(print_able)


def get_logger(name, debug=False, ext_logger=None):
    """
    Args:
        name: Name of the logger.
        debug: Bool whether to show debug statements
        ext_logger: Use ext logger to pass an already instantiated logger

    Returns:
        log: Instantiated logger
    """
    fmt = fmt = '%(name)s %(levelname)s %(message)s'
    if ext_logger is None:
        log = logging.getLogger(name)
    else:
        log = ext_logger
    if debug:
        level = 'DEBUG'
    else:
        level = 'INFO'

    coloredlogs.install(fmt=fmt, level=level, logger=log)
    return log


def exit_requested():
    ans = input('\nPress enter to begin listening for probe (type exit to quit): ')
    if ans.strip().lower() in ['exit', 'quit']:
        return True
    else:
        return False


def get_index_from_ratio(idx, ratio, n_samples):
    """
    Sometimes we have an index and we want something
    slightly near it. This manages grabbing those with
    consideration for the max value
    Args:
        idx: idx of interest
        ratio: scaling ratio (e.g. 1.1)
        n_samples: max allowable number of samples

    Returns:
        result: Scaled integer of the index
    """
    result = int(idx*ratio)
    if result > n_samples:
        result = n_samples-1
    return result
