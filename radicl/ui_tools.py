# coding: utf-8

import textwrap
from colorama import init
from termcolor import colored
import sys
import coloredlogs, logging

class Messages():
    init()

    def msg(self,str_msg,context_str=None):
        msg = colored(str_msg,'white')
        print('\n'+msg)

    def dbg(self,str_msg):
        final_msg = colored('[DEBUG]: ','magenta',attrs=['bold'])
        final_msg += colored(str_msg,'white')
        print('\n'+final_msg)

    def warn(self,str_msg):
        final_msg = colored('WARNING: ','yellow',attrs=['bold'])
        final_msg += colored(str_msg,'white')
        print('\n'+final_msg)


    def error(self,str_msg):
        final_msg = colored('ERROR: ','red',attrs=['bold'])
        final_msg += colored(str_msg,'red')
        print('\n'+final_msg)

    def critical(self,str_msg):
        final_msg = colored('ERROR: ','red',attrs=['bold'])
        final_msg += colored(str_msg+'\nExiting program...','red')
        print('\n'+final_msg)
        sys.exit()

    def respond(self,str_msg):
        final_msg = colored(str_msg,'green')
        print('\t'+final_msg)

    def headline(self,str_msg):
        str_msg = str_msg.upper()
        final_msg = colored(str_msg,'blue',attrs=['bold','underline'])
        print('\t'+final_msg)


def parse_func_list(func_lst, identify_lst, ignore_keywords = []):
    """
    Reads through a list of available methods and retrieves the methods that have
    matching words in the identify list, then it removes those key words and Returns
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
    for f_name,fn in func_lst:
        #Return a list of true when a word is found
        words_found = [True for w in identify_lst if w in f_name]
        #If the number of the matches matches the number of keywords were looking for
        if len(words_found) == len(identify_lst) and 'RAD' not in f_name:
            #Remove the keywords to form the simplified method name
            name = f_name
            for word in identify_lst:
                #print(f_name,word)
                name = name.replace(word,'')
            ignores = [True for ign in ignore_keywords if ign in name.lower()]
            if len(ignores) == 0:
                options[name.lower()]=fn

    return options

def parse_help(help_str):
    """
    Auto parses the help dialogs provided by developers in the doc strings.
    This is denoted by helpme - text and then a blank line.

    e.g.

    Function doc string
    helpme - more end user friendly message about what this will do

    my arguments...

    """
    result = None

    if help_str != None:
        if 'helpme' in help_str:
            z = help_str.split('helpme')
            result = z[-1].split('-')[-1].strip()

    return result

def columnize_str(entrie,width):
    """
    Takes a long string that cannot be formatted correctly into a column
    """
    pass

def print_helpme(help_str,help_dict):
    """
    Trys to help the user on request for help.
    """
    out_str = ""
    show_all = False
    no_help = 0
    no_doc = False
    # User provides specific help request
    if help_dict != None:
        if "-" in help_str:
            h = help_str.split("-")
            k = ("".join(h[1:]).strip()).lower()
            if k in help_dict:
                formatted = textwrap.fill(long_str,width = width)

                for i,line in enumerate(formatted.split('\n')):
                    if i != 0:
                        k = ""
                    result += "\n{0:<20} {1:<20}\n".format(k,v)
            else:
                show_all = True
        else:
            show_all= True

        if show_all:
            for k,v in help_dict.items():
                if v == None:
                    no_help +=1
                    v = ('No help documentation.')

                out_str +='\n{0:<25} {1:<25}\n'.format(k,v)
        if no_help == len(help_dict.keys()):
            no_doc = True
    else:
        no_doc = True

    if no_doc:
        out_str = ('\nNo help documentation.\nPlease email micah@adventuredata.com\n')
        print(help_dict)
    t = '\n{0:<20} {1:<20}\n'.format('OPTIONS','DESCRIPTION')
    print_able='\n{0}'.format(colored(t,'magenta',attrs=['bold']))
    print_able+=out_str
    print(print_able)

def get_logger(name, level='DEBUG', ext_logger=None,):
    """

    """
    fmt = fmt='%(name)s %(levelname)s %(message)s'
    if ext_logger == None:
        log = logging.getLogger(name)
    else:
        log = ext_logger

    coloredlogs.install(fmt=fmt,level=level, logger=log)
    return log
