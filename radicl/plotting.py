#!/usr/bin/env python

import argparse
import os
import sys
import platform
import time
import traceback

import numpy as np
from matplotlib import pyplot as plt
import matplotlib
import traceback
from radicl.ui_tools import get_logger, get_index_from_ratio
from study_lyte.profile import LyteProfileV6, Sensor
from study_lyte.styles import SensorStyle, EventStyle
from study_lyte.plotting import plot_events


matplotlib.rcParams['agg.path.chunksize'] = 100000


def plot_nir_depth_correct(ax, profile):
    ax.grid(True, axis='y', alpha=0.5)

    for sensor in ['Sensor2', 'Sensor3']:
        style = SensorStyle.from_column(sensor)
        ax.plot(profile.nir[sensor],
                profile.nir.depth,
                alpha=0.3, color=style.color, label=style.label)

    style = SensorStyle.ACTIVE_NIR
    ax.plot(profile.nir['nir'], profile.nir['depth'], color=style.color, label=style.label)
    ax.set_title("NIR Depth Corrected")
    ax.legend(loc='lower left', fontsize='small')
    return ax


def plot_force_depth_corrected(ax, profile, ):
    # plot the depth corrected Force
    force_style = SensorStyle.RAW_FORCE
    ax.grid(True, axis='y', which='both', alpha=0.5)
    ax.plot(profile.force['force'], profile.force['depth'], color=force_style.color, label=force_style.label)
    ax.set_title("Force Depth Corrected")
    ax.legend(loc='lower left', fontsize='small')
    ax.set_ylabel('Depth [cm]')
    ax.set_xlim((0, 4096))
    return ax

def report_profile_error(ax):
    ylims = ax.get_ylim()
    xlims = ax.get_xlim()
    ax.annotate('Failed to compute \ncorrected profile.', (np.mean(xlims)*0.25, np.mean(ylims)))
    return ax


def plot_hi_res(fname=None, timed_plot=None, calibration_dict={}):
    """
    Plots the timeseries, the depth corrected, accelerometer and depth data.
    Plot from a dataframe or from a file. Use auto close to auto close the figure
    after a some amount of time.

    Args:
        fname: Path to csv containing hi resolution data
        timed_plot: Amount of time to show the plot, if none user has to close it
        calibration_dict: Dictionary to offer calibration coefficients for any of the sensors

    """
    log = get_logger('Hi Res Plot')
    if 'Linux' in platform.platform():
        matplotlib.use('TkAgg')

    # Setup a panel of plots
    fig = plt.figure(figsize=(10, 6), constrained_layout=True)
    gs = fig.add_gridspec(2, 5)

    print('')
    if fname is not None:
        profile = LyteProfileV6(fname)
        log.info(f"Filename: {profile.filename}")
        plt.suptitle(os.path.basename(profile.filename))

    # print out some handy numbers
    log.info(profile.report_card())

    # Plot time series data force data
    ax = fig.add_subplot(gs[:, 0])
    plot_events(ax, profile.events, plot_type='vertical')
    force_style = SensorStyle.from_column('Sensor1')
    ax.plot(profile.raw['Sensor1'], profile.time, color=force_style.color)
    ax.set_title("Raw Force Timeseries")
    ax.legend(loc='lower left')
    ax.set_ylabel('Time [s]')
    ax.set_xlim(0, 4096)
    ax.invert_yaxis()

    # plot time series NIR data
    ax = fig.add_subplot(gs[:, 1])
    plot_events(ax, profile.events, plot_type='vertical')
    for sensor in ['Sensor2', 'Sensor3']:
        style = SensorStyle.from_column(sensor)
        ax.plot(profile.raw[sensor], profile.time, color=style.color, label=style.label)
    ax.set_title("NIR Timeseries")
    ax.legend(loc='lower left')
    ax.invert_yaxis()

    # plot the depth corrected Force
    ax = fig.add_subplot(gs[:, 2])
    try:
        ax = plot_force_depth_corrected(ax, profile)
    except:
        log.error(traceback.format_exc())
        report_profile_error(ax)

    # plot depth corrected NIR data
    ax = fig.add_subplot(gs[:, 3])
    try:
        ax = plot_nir_depth_correct(ax, profile)
    except:
        log.error(traceback.format_exc())
        report_profile_error(ax)

    #### plot the acceleration as a sub-panel with events ####
    ax = fig.add_subplot(gs[0, 4])

    # Plot acceleration if it exists
    if profile.acceleration is not Sensor.UNAVAILABLE:
        plot_events(ax, profile.events, plot_type='normal')
        for c in profile.acceleration_names:
            alpha = 1.0
            if c != profile.motion_detect_name:
                alpha = 0.3
            style = SensorStyle.from_column(c)
            ax.plot(profile.time, profile.raw[c], color=style.color,
                    label=style.label, alpha=alpha)

        ax.set_ylabel("Acceleration [g's]")
        ax.set_xlabel('Time [s]')
        ax.set_title('Accelerometer')
        ax.legend(fontsize='xx-small')
    else:
        ax.annotate('No Accelerometer \nData Available', (0.2, 0.5), alpha=0.5)
    #### plot the depth as a sub-panel with events ####
    ax = fig.add_subplot(gs[1, 4])
    ax.set_title('Depth')
    plot_events(ax, profile.events, plot_type='normal')

    # for label, color, col in label_color_column:
    if profile.motion_detect_name is Sensor.UNAVAILABLE:
        style = SensorStyle.from_column('barometer')
    else:
        acc_style = SensorStyle.ACCELERATION
        baro_style = SensorStyle.CONSTRAINED_BAROMETER
        raw = SensorStyle.RAW_BARO
        style = SensorStyle.FUSED
        ax.plot(profile.barometer.raw.index, profile.barometer.raw.values, color=raw.color, label=raw.label, alpha=0.5)
        ax.plot(profile.barometer.depth.index, profile.barometer.depth.values, color=baro_style.color, label=baro_style.label, alpha=0.5)
        ax.plot(profile.accelerometer.depth, color=acc_style.color, label=acc_style.label, alpha=0.5)

    ax.plot(profile.time, profile.depth, color=style.color, label=style.label)

    ax.legend(loc='upper right', fontsize='xx-small')
    # limits for depth
    buffer = 0.3
    n_samples = len(profile.raw)
    lim_idx1 = get_index_from_ratio(profile.start.index, 1- buffer, n_samples)
    lim_idx2 = get_index_from_ratio(profile.stop.index, 1 + buffer, n_samples)
    ts1, ts2 = profile.time[lim_idx1], profile.time[lim_idx2]
    depth1 = profile.depth.iloc[lim_idx1] * (1 - buffer)
    depth2 =  profile.depth.iloc[lim_idx2].min() * (1 + buffer)
    if abs(depth1) < 5:
        depth1 = 5

    # ax.set_xlim(ts1, ts2)
    # ax.set_ylim(*sorted([depth1, depth2]))
    ax.grid(True, axis='y', which='both', alpha=0.5)

    # Make the figure full screen
    manager = plt.get_current_fig_manager()
    if 'Linux' in platform.platform():
        manager.full_screen_toggle()

    # Manage plot time
    if timed_plot == 0:
        pass
    elif timed_plot is not None:
        timer = fig.canvas.new_timer(interval=timed_plot*1000)
        timer.add_callback(plt.close)
        timer.start()
        plt.show(block=True)

    else:
        plt.show()


def plot_hi_res_cli():
    files = sys.argv[1:]

    for f in files:
        try:
            plot_hi_res(fname=f)
        except Exception as e:
            print(f'Encountered error while processing {f}')
            traceback.print_exc(file=sys.stdout)
            time.sleep(1)
            plt.close()


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

            print("Pre-processed profile:")
            print("\tNum of samples: {0:,}".format(len(df_o.index)))
            print("\tDepth achieved: {0:.1f}".format(min(df_o.index)[-1]))
            print("\tResolution: {0:.1f} pts/cm".format(
                abs(len(df_o.index) / min(df_o.index)[1] - max(df_o.index)[1])))

            if post_processed:
                print("\nPost-processed profile:")
                print("\tNum of samples: {0:,}".format(len(df.index)))
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
    plot_hi_res_cli()
