# coding: utf-8

import sys
import time
from matplotlib import pyplot as plt
import os
from termcolor import colored
import inspect
import pandas as pd
from radicl.ui_tools import Messages, parse_func_list, print_helpme, parse_help
import datetime

from radicl import probe
from radicl import serial
from radicl import api
import radicl

out = Messages()

class RADICL:
    def __init__(self,**kwargs):

        self.tasks = ['daq','settings','update']
        self.task_help = {'daq':"Data acquisition using the probe.",
                          'settings':'Interface for modifying the behavior of the probe',
                          'update': 'Firmware update dialog for the probe.'}

        self.probe = probe.RAD_Probe()
        self.running = True

        self.settings = dir(self.probe.api)

        # Get all the functions available in api and probe
        settings_funcs = inspect.getmembers(self.probe.api, predicate=inspect.ismethod)
        data_funcs = inspect.getmembers(self.probe, predicate=inspect.ismethod)
        # Dictionary of the options available that can be auto parsed
        # Each option type has keys word that searched for in the api and probe classes
        self.options_keywords = {'data':{'parseable':['read','Data']},
                        'settings':{'parseable':['Meas','Set']}
                        }
        self.options = {'data':{},
                       'settings':{}}
        # Assign all functions with keys word to auto gather settings and data packages
        self.options['data'] = parse_func_list(data_funcs,['read','Data'],
                                             ignore_keywords = ['correlation'])
        self.options['settings'] = parse_func_list(settings_funcs,['Meas','Set'])
        self.options['settings']["show"] = self.print_settings

        self.options['getters'] = parse_func_list(settings_funcs,['Meas','Get'])

        # User runtime preferences
        self.output_preference = None
        self.filename = None
        self.daq = None


        # Gather help dialogs
        self.help_dialog= {}

        for s in self.options.keys():
            # We haven't added the category yet
            if s not in self.help_dialog:
                self.help_dialog[s] = {}

            # Add in all the functions
            for k,fn in self.options[s].items():
                self.help_dialog[s][k] = parse_help(fn.__doc__)

    def run(self):
        """
        Main running loop for the command line Interface
        """

        self.state = 0
        plot = False
        write = False
        both = False
        filename_used = False
        data_attempts = 1

        # Create the probe command with an arbitrary command to have access to help
        while self.running:
            pstate = self.probe.getProbeMeasState()

            if self.state == 0:
                #If probe is not ready.
                if pstate != 0:
                    pstate = self.probe.resetMeasurement()

                else:
                    #Request type of operation
                    self.task = self.ask_user("What do you want to do with the"
                                                      " probe?", self.tasks,
                                                      helpme = self.task_help)

            elif self.state >= 1:
                self.tasking()

            else:
                pass

    def tasking(self):
        """
        Handles tasks from the user, specifically any member function who
        contains the keyword task_ in it. This means currently we are looking
        for a daq, settings, upgrade task function.
        """
        # Auto look for task_functions
        task_at = "task_%s" % self.task
        fn = getattr(self,task_at)

        # Call task_function
        out.dbg("Using task function {0}".format(fn.__name__))
        fn()


    def take_a_reading(self,data_request):

        input("Press any key to begin a measurement.\n")
        response = self.probe.startMeasurement()

        input("Press any key to stop the measurement.\n")
        response = self.probe.stopMeasurement()


        fn = self.options['data'][data_request]
        out.dbg("Requesting data using function {0}".format(fn.__name__))

        self.probe.wait_for_state(3)

        temp = self.probe.readMeasurementTemperature()
        if (temp != None):
            out.dbg("Temp = %i" % temp)
        else:
            out.error("Error reading temp")

        data = fn()

        response = self.probe.resetMeasurement()
        data = self.dataframe_this(data,data_request)

        return data

    def dataframe_this(self,data,name):
        """
        Takes the data returned from a function and converts it into a DataFrame
        There appears to be two scenarios so we cover it here.
        """
        t = type(data)
        if t == dict:
            data = pd.DataFrame(data, columns = data.keys())

        elif t == list:
            if type(data[0])==tuple:
                data = [d[0] for d in data]

            data = pd.DataFrame(data, columns = [name])
        return data


    def task_daq(self):
        """
        The state machine for request to do daq
        """
        # Data Selection
        if self.state==1:
            pstate = self.probe.getProbeMeasState()
            out.msg("Checking to see if probe is ready...")
            out.dbg("Probe State = {0}".format(pstate))

            # Make sure probe is ready
            if pstate==0 or pstate==5:
                self.daq = self.ask_user("What data do you want?",
                                    list(self.options['data'].keys()),
                                    helpme = self.help_dialog['data'])

        # Method for outputting data
        elif self.state == 2:
            self.output_preference = self.ask_user("How do you want to output"
                                       " {0} data?".format(self.daq),
                                       ['plot','write','both'],
                                       default_answer = self.output_preference)

        # Take Measurements
        elif self.state == 3:
            self.data = self.take_a_reading(self.daq)
            self.state = 4

        # Data output and options
        elif self.state == 4:
            if self.output_preference == 'write' or self.output_preference == 'both':
                valid = False
                #  Wait for real path
                while not valid:
                    t = datetime.datetime.now()
                    fstr = "{0}-{1:02d}-{2:02d}--{3:02d}{4:02d}{5:02d}"
                    fname = fstr.format(t.year,t.month,t.day,t.hour,t.minute,t.second)
                    out.msg("Enter in a filepath for the data to be saved:")
                    filename = input("\nPress enter to use default:"
                                    "\n(Default: ./{0}.csv)".format(fname))

                    # Recieve a default request
                    if filename == '':
                        filename = os.path.expanduser('./{0}.csv'.format(fname))
                    else:
                        filename = os.path.expanduser(filename)
                    # Make it absolute
                    filename = os.path.abspath(filename)
                    real_path = os.path.isdir( os.path.dirname(filename))

                    # Double check a real path was given
                    if not real_path:
                        out.warn("Path provided does not exist.")
                        valid = False
                    else:
                        self.filename = filename
                        valid = True
                        out.msg("Saving Data to :\n{0}".format(self.filename))

                        if not self.data.empty:
                            # Write the header so we knwo things about this
                            with open(self.filename,'w') as fp:
                                final = self.probe.getProbeHeader()
                                fp.writelines(final)
                                fp.close()
                            # Write data
                            self.data.to_csv(self.filename, mode = 'a')
                            self.state = 5

            if self.output_preference == 'plot' or self.output_preference =='both':
                self.data.plot()
                plt.show()
                self.state = 5

        elif self.state==5:
            pos_ans = self.ask_user("Take another measurement?")
            if pos_ans:
                self.state = 3
            elif not pos_ans:
                self.state = 1


    def task_settings(self):
        """
        Routine for handling users requests for modifying probe settings settings
        """

        # Data Selection
        if self.state == 1:
            pstate = self.probe.getProbeMeasState()
            out.msg("Checking to see if probe is ready...")
            out.dbg("Probe State = {0}".format(pstate))

            # Make sure probe is ready
            if pstate == 0 or pstate == 5:
                print( self.help_dialog['settings'])
                self.setting_request = self.ask_user("What settings do you want"
                                                     " to adjust?",
                               list(self.options['settings'].keys()),
                                helpme = self.help_dialog['settings'])

        # Get current setting
        elif self.state == 2:

            if self.setting_request == 'calibdata':
                out.error("Calibration method are under developed at this time")
                self.state = 1

            elif self.setting_request == 'show':
                self.options['settings'][self.setting_request]()
                self.state = 1

            else:
                self.current_setting_value = \
                        self.probe.getSetting(setting_name=self.setting_request)
                self.state += 1

        # Set settings
        elif self.state == 3:

                if self.setting_request == 'calibdata':
                    out.error("Calibration method are under developed at this time")
                    self.state = 1

                else:
                    msg = ("Currently {0} = {1}\nEnter value to change probe {0}\n"
                           "".format(self.setting_request,self.current_setting_value))
                    valid = False

                    # All entries have to be numeric. Ensure this is the case.
                    while not valid:
                        self.new_value = input(msg)
                        try:
                            self.new_value = int(self.new_value)
                            valid = True
                        except Exception as e:
                            print(e)
                            out.error("Value must be numeric!")

                    # Call the function to change the setting
                    self.probe.setSetting(setting_name = self.setting_request,
                                          value = self.new_value)
                    time.sleep(0.2)

                    # Confirm the value was changed
                    test_value = self.probe.getSetting(
                                            setting_name = self.setting_request)

                    if test_value == self.new_value:
                        out.respond("{0} was changed from {1} to {2}!\n"
                                    "".format(self.setting_request,
                                              self.current_setting_value,
                                              self.new_value))
                    # Go back to settings menu
                    self.state = 1

    def print_settings(self):
        """
        print all the current settings

        helpme - Prints out all the settings fro the probe

        """

        msg = "\n===== Current Probe Settings =====\n"

        for s, fn in self.options['getters'].items():

            if s.lower() not in ['calibdata','numsegments']:
                value = self.probe.getSetting(setting_name=s)
                msg += "{} = {}\n".format(s, value)
        out.msg(msg)
        time.sleep(2)

    def increment_fnumber(self,filename):
        """
        Check for a file numbering. Increment if there is one. Otherwise add one
        """
        if self.is_numbered(filename):
            fcount = int(filename[-1])+1

        else:
            fcount = 1

        s = -1*len(str(fcount)) + pos_num
        filename = filename[0:s] + str(fcount)

        return filename

    def is_numbered(self, filename):
        """
        Checks if the filename is numbered. Returns true or false.
        """
        if filename[-4] in [str(i) for i in range(0,9)]:
            result = True

        else:
            result = False

        return result

    def check_ext(self,filename):
        """
        Check to see if the user provided the .csv ext in the filename
        and add it
        """
        if filename[-4:] != '.csv':
            f = filename.split('.')
            # Did the user try to add an ext
            if len(f) == 2:
                filename = f[0]+'.csv'
            else:
                filename +='.csv'

        return filename


    def ask_user(self,question_str, answer_lst = None, helpme = None, next_state = True, default_answer = None):
        """
        Function is used to wait for an appropriate response from user and handle unknown answers
        """

        # Ask user for a yes no question
        if answer_lst == None:
            answer_lst = ['y','n']
            question_boolean = True
        else:
            question_boolean = False

        # Keep question to one line if small number of options
        lower_lst = [i.lower() for i in sorted(answer_lst)]
        lower_lst.append('exit')
        lower_lst.append('home')

        # Help documentation
        if helpme != None:
            lower_lst.append("help")

        if len(lower_lst) <= 5:
            print_able=" ("
            print_able += ", ".join(lower_lst)
            print_able+=")"
        # Create a column of choices
        else:
            print_able='\n{0}'.format(colored('[OPTIONS]','magenta',attrs=['bold']))
            for s in lower_lst:
                print_able+= '\n  {0}'.format(s)

        question_str+=print_able

        # Provide prompt for default options
        if default_answer != None:
            if default_answer not in answer_lst:
                raise ValueError("default answer must be a member of the acceptable answers list in ask_user function")

            question_str += '(Default: {0})'.format(default_answer)

        out.msg(question_str)

        acceptable_answer=False

        while acceptable_answer==False:
            user_answer = input('\n')
            response = user_answer.lower()

            # User requests help with options
            if "help" in response:
                print_helpme(response,helpme)
                acceptable_answer=False
                out.msg(question_str)

            # Request to leave the program
            elif response=='exit':
                out.respond("Exiting the RAD CLI.")
                self.running = False
                sys.exit()

            elif response=='home':
                out.respond("Returning to the main menu.")
                self.running = True
                acceptable_answer=True
                self.state = 0

            # Default Picked
            elif response == '':
                response = default_answer

            # User provided a potential acceptable answer
            elif response in lower_lst:
                acceptable_answer=True
                response = lower_lst[lower_lst.index(response)]
                if question_boolean:
                    if response == 'y' or response =='yes':
                        response = True
                    else:
                        response = False

                if next_state:
                    self.state +=1


            else:
                out.error('Only acceptable answers are:')
                out.msg(print_able)
                acceptable_answer=False

        return response
