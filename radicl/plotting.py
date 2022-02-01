#!/usr/bin/env python

import argparse
import os
import sys
import platform
import numpy as np
import pandas as pd
import time
from matplotlib import pyplot as plt
import matplotlib
from study_lyte.detect import get_acceleration_start, get_acceleration_stop, get_nir_surface
from study_lyte.io import read_csv


matplotlib.rcParams['agg.path.chunksize'] = 100000


def plot_events(ax, start=None, surface=None, stop=None, plot_type='normal'):
    """
    Plots the hline or vline for each event on a plot
    Args:
        ax: matplotlib.Axes to add horizontal or vertical lines to
        start: Array indicie to represent start of motion
        surface: Array index to reprsent snow surface
        stop: Array index to represent stop of motion
        plot_type: string indicating whether the index is on the y (vertical) or the x (normal)
    """
    event_alpha = 0.6
    if plot_type == 'vertical':
        line_fn = ax.axhline
    elif plot_type == 'normal':
        line_fn = ax.axvline
    else:
        raise ValueError(f'Unrecognized plot type {plot_type}, options are vertical or normal!')
    if start is not None:
        line_fn(start, linestyle='dashed', color='lime', label='Start', alpha=event_alpha)
    if surface is not None:
        line_fn(surface, linestyle='dashdot', color='cornflowerblue', label='Surface', alpha=event_alpha)
    if stop is not None:
        line_fn(stop, linestyle='dashed',  color='red', label='Stop', alpha=event_alpha)


def plot_hi_res(fname=None, df=None):
    """
    Plots the timeseries, the depth corrected, accelerometer and depth data.
    Plot from a dataframe or from an file. Use auto close to auto close the figure
    after an some amount of time.

    Args:
        fname: Path to csv containing hi resolution data
        df: Optional pandas dataframe instead of a file
    """
    if 'Linux' in platform.platform():
        matplotlib.use('TkAgg')

    if fname is not None:
        df, meta = read_csv(fname)
        print(f"Filename: {fname}")

    # Setup a panel of plots
    fig = plt.figure(constrained_layout=True)
    gs = fig.add_gridspec(2, 5)

    # Grab all the estimates on the typical events of interest
    start = get_acceleration_start(df['acceleration'])
    stop = get_acceleration_stop(df['acceleration'])
    cropped = df.iloc[start:stop].copy()
    print(start,stop)
    surface = get_nir_surface(cropped['Sensor2'], cropped['Sensor3'])
    # Re-zero the depth
    cropped['depth'] = cropped['depth'] - cropped['depth'].iloc[0]

    # Calculate some travel distances
    travel_delta = df['depth'].iloc[start] - df['depth'].iloc[stop]
    snow_travel_delta = cropped['depth'].iloc[surface] - cropped['depth'].iloc[-1]

    # print out some handy numbers
    print(f"* Number of samples: {len(df.index)}")
    print(f"* Max depth achieved: {df['depth'].min():0.1f} cm")
    print(f"* Distance traveled between start/stop: {travel_delta:0.1f} cm")
    print(f"* Distance traveled in the snow surface/stop: {snow_travel_delta:0.1f} cm")

    # Provide depth shifts
    ambient_shift = 6 # cm
    active_shift = 4.5 # cm

    # Plot time series data force data
    ax = fig.add_subplot(gs[:, 0])
    plot_events(ax, start=start, surface=start + surface, stop=stop, plot_type='vertical')
    ax.plot(df['Sensor1'], df.index, color='k')
    ax.set_title("Raw Force Timeseries")
    ax.legend()
    ax.set_ylabel('Time [s]')
    ax.set_xlim(0, 4096)
    ax.invert_yaxis()

    # plot time series NIR data
    ax = fig.add_subplot(gs[:, 1])
    plot_events(ax, start=start, surface=start + surface, stop=stop, plot_type='vertical')
    ax.plot(df['Sensor2'], df.index, color='darkorange', label='Ambient')
    ax.plot(df['Sensor3'], df.index, color='crimson', label='Active')
    ax.set_title("NIR Timeseries")
    ax.legend()
    ax.invert_yaxis()

    # plot the depth correct Force
    ax = fig.add_subplot(gs[:, 2])
    plot_events(ax, surface=cropped['depth'].iloc[surface], plot_type='vertical')
    ax.plot(cropped['Sensor1'], cropped['depth'], color='k', label='Inverted Force (RAW)')
    ax.set_title("Depth Corrected")
    ax.legend()
    ax.set_xlim((0, 4096))
    ax.set_ylabel('Force Depth [cm]')

    # plot depth corrected NIR data
    ax = fig.add_subplot(gs[:, 3])
    plot_events(ax, surface=cropped['depth'].iloc[surface] + active_shift, plot_type='vertical')
    ax.plot(cropped['Sensor2'], cropped['depth'] + ambient_shift, color='darkorange', label='Ambient')
    ax.plot(cropped['Sensor3'], cropped['depth'] + active_shift, color='crimson', label='Active')
    ax.set_title("NIR Depth Corrected")
    ax.set_ylabel('Depth [cm]')
    ax.legend()

    # plot the acceleration as a sub-panel with events
    ax = fig.add_subplot(gs[0, 4])
    plot_events(ax, start, start + surface, stop, plot_type='normal')
    ax.plot(df.index, df['acceleration'], color='darkslategrey')
    ax.set_ylabel("Acceleration [g's]")
    ax.set_xlabel('Time [s]')
    ax.set_title('Accelerometer')

    # plot the depth as a sub-panel with events
    ax = fig.add_subplot(gs[1, 4])
    ax.set_title('Depth')
    plot_events(ax, start, start + surface, stop, plot_type='normal')
    ax.plot(df.index, df['depth'], color='navy')
    ax.set_ylabel('Depth from Max Height [cm]')

    # Make the figure full screen
    manager = plt.get_current_fig_manager()
    manager.full_screen_toggle()
    plt.show()


def plot_hi_res_cli():
    files = sys.argv[1:]

    for f in files:
        plot_hi_res(fname=f)


def main():
    parser = argparse.ArgumentParser(
        description='Plot various versions of probe data.')
    parser.add_argument('file', help='path to measurement', nargs='+')

    parser.add_argument('--smooth''-sm', dest='smooth',
                        help='Provide a integer to describing number of windows to smooth over')

    parser.add_argument('--avg', '-a', dest='average', action='store_true',
                        help='Average all three sensors together')
    parser.add_argument('--compare', '-c', dest='compare', action='store_true',
                        help='Plots before and after sensors')
    parser.add_argument('--sensor', '-sn', dest='sensor', type=int,
                        help='plots only a specific sensor, must be between 1-4')

    args = parser.parse_args()

    # Provide a opportunity to look at lots
    filenames = []
    if args.file is not None and not isinstance(args.file, list):
        if os.path.isdir(args.file):
            filenames = os.listdir(args.file)
        elif os.path.isfile(args.file):
            filenames = [args.file]

    elif isinstance(args.file, list):
        filenames = args.file
    else:
        print("Please provide a directory or filename")
        sys.exit()

    for f in filenames:
        try:
            post_processed = False
            print('\n' + os.path.basename(f))
            print('=' * len(f))
            # Open the file and set the index to depth
            df_o, meta = read_csv(f)
            df = df_o.copy()

            if args.smooth is not None:
                df = df.rolling(window=int(args.smooth)).mean()
                post_processed = True

            # Remove the ambient signal
            if args.ambient:
                if enough_ambient(df):
                    df = shift_ambient_sensor(df)
                    df = ambient_removed(df)
                post_processed = True

            print("Pre-processed profile:")
            print("\tNum of samples: {0}".format(len(df_o.index)))
            print("\tDepth achieved: {0:.1f}".format(min(df_o.index)[-1]))
            print("\tResolution: {0:.1f} pts/cm".format(
                abs(len(df_o.index) / min(df_o.index)[1] - max(df_o.index)[1])))

            if post_processed:
                print("\nPost-processed profile:")
                print("\tNum of samples: {0}".format(len(df.index)))
                print("\tDepth achieved: {0:.1f}".format(min(df.index)))
                print(
                    "\tResolution: {0:.1f} pts/cm".format(abs(len(df.index) / min(df.index) - max(df.index))))

            # Plot
            data = {}
            if args.average:
                data['Average'] = df[['Sensor 1',
                                      'Sensor 2', 'Sensor 3']].mean(axis=1)

            elif args.sensor is not None:
                if args.sensor in [1, 2, 3, 4]:
                    col = "SENSOR {0}".format(args.sensor)
                    data[col] = df[[col]]
            else:
                for i, c in enumerate(df.columns):
                    data[c] = df[c].copy()

            if args.compare:
                if args.average:
                    data['Orig. Average'] = df_o.mean(axis=1)
                else:
                    for i in range(1, 5):
                        col = 'SENSOR %s' % i
                        new_col = 'Orig. %s' % col
                        data[new_col] = df_o[col]

            # Parse the datetime
            for k, d in data.items():
                plt.plot(d, d.index, label=k)

            plt.title(os.path.basename(f))
            plt.legend()
            plt.xlabel('Reflectance')
            plt.ylabel('Depth from Surface [cm]')
            plt.xlim([0, 4100])
            plt.show()

        except Exception as e:
            print(e)


if __name__ == '__main__':
    main()
