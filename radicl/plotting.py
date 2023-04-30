#!/usr/bin/env python

import argparse
import os
import sys
import platform
import time
import traceback
from matplotlib import pyplot as plt
import matplotlib
from radicl.ui_tools import get_logger, get_index_from_ratio

from study_lyte.detect import get_acceleration_start, get_acceleration_stop, get_nir_surface
from study_lyte.depth import get_depth_from_acceleration, get_constrained_baro_depth
from study_lyte.io import read_csv
from study_lyte.adjustments import remove_ambient, assume_no_upward_motion


matplotlib.rcParams['agg.path.chunksize'] = 100000


def plot_events(ax, start=None, surface=None, stop=None, nir_stop=None, plot_type='normal'):
    """
    Plots the hline or vline for each event on a plot
    Args:
        ax: matplotlib.Axes to add horizontal or vertical lines to
        start: Array index to represent start of motion
        surface: Array index to represent snow surface
        stop: Array index to represent stop of motion
        nir_stop: Array index to represent stop estimated by nir
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
        line_fn(stop, linestyle='dashed', color='red', label='Stop', alpha=event_alpha)
    if nir_stop is not None:
        line_fn(nir_stop, linestyle='dashed', color='magenta', label='NIR Stop', alpha=event_alpha)


def plot_hi_res(fname=None, df=None, timed_plot=None, calibration_dict={}):
    """
    Plots the timeseries, the depth corrected, accelerometer and depth data.
    Plot from a dataframe or from a file. Use auto close to auto close the figure
    after a some amount of time.

    Args:
        fname: Path to csv containing hi resolution data
        df: Optional pandas dataframe instead of a file
        timed_plot: Amount of time to show the plot, if none user has to close it
        calibration_dict: Dictionary to offer calibration coefficients for any of the sensors

    """
    log = get_logger('Hi Res Plot')
    if 'Linux' in platform.platform():
        matplotlib.use('TkAgg')

    print('')
    if fname is not None:
        df, meta = read_csv(fname)
        log.info(f"Filename: {fname}")

    # Setup a panel of plots
    fig = plt.figure(figsize=(10, 6), constrained_layout=True)
    gs = fig.add_gridspec(2, 5)

    # # Use time when possible
    if 'time' in df.columns:
        time_series = df['time']
    else:
        time_series = df.index

    # Grab all the estimates on the typical events of interest
    if 'Y-Axis' in df.columns:
        detect_col = 'Y-Axis'
        acc_cols = [c for c in df.columns if 'Axis' in c]

    elif 'acceleration' in df.columns:
        detect_col = 'acceleration'
        acc_cols = ['acceleration']
    else:
        acc_cols = None

    # Estimate events
    if acc_cols is not None:
        start = get_acceleration_start(df[detect_col])
        stop = get_acceleration_stop(df[detect_col])

        # Calculate depth from acceleration
        acc_depth = get_depth_from_acceleration(df[acc_cols + ['time']]).mul(100)
        acc_depth = acc_depth.reset_index()
        df['acc_depth'] = acc_depth[detect_col].copy()
        df['avg_depth'] = df[['acc_depth', 'depth']].mean(axis=1)
        depth_cols = ['depth', 'acc_depth', 'avg_depth']
        # Crop data to motion
        cropped = df.iloc[start:stop].copy()
        cropped['clean'] = remove_ambient(cropped['Sensor3'], cropped['Sensor2'])
    else:
        start = 0
        stop = df.index[-1]
        cropped = df.copy()
        depth_cols = ['depth']

    cropped['clean'] = remove_ambient(cropped['Sensor3'], cropped['Sensor2'])
    surface = get_nir_surface(cropped['clean'])
    full_surface = surface + start

    # Re-zero the depth
    for c in depth_cols:
        cropped[c] = cropped[c] - cropped[c].iloc[surface]

    # Calculate some travel distances
    max_distance = df[depth_cols].max() - df[depth_cols].min()
    mv_distance = df[depth_cols].iloc[start] - df[depth_cols].iloc[stop]
    snow_distance = df[depth_cols].iloc[full_surface] - df[depth_cols].iloc[stop]

    # print out some handy numbers
    log.info(f"* Number of samples: {len(df.index):,}\n")
    msg = "{:<25}"
    msg_f = "{:<25}"
    for c in depth_cols:
        msg += '{:<10}'
        msg_f += '{:<10.1f}'
    header_names = ['Distance'] + depth_cols
    header = msg.format(*header_names)
    log.info(header)
    log.info('-' * len(header))

    # Dict and summary series
    distances = {"Maximum Measured": max_distance,
                 'During Motion': mv_distance,
                 'Snow Only': snow_distance}

    for desc, distance in distances.items():
        depths = [distance[c] for c in depth_cols]
        log.info(msg_f.format(desc, *depths))

    # Provide depth shifts
    ambient_shift = 6  # cm
    active_shift = 4.5  #
    mean_shift = (ambient_shift + active_shift) / 2
    time_series_events = dict(start=time_series[start],
                              surface=time_series[full_surface],
                              stop=time_series[stop],
                              nir_stop=None,
                              plot_type='vertical')

    # Plot time series data force data
    ax = fig.add_subplot(gs[:, 0])
    plot_events(ax, **time_series_events)
    ax.plot(df['Sensor1'], time_series, color='k')
    ax.set_title("Raw Force Timeseries")
    ax.legend(loc='lower left')
    ax.set_ylabel('Time [s]')
    ax.set_xlim(0, 4096)
    ax.invert_yaxis()

    # plot time series NIR data
    ax = fig.add_subplot(gs[:, 1])
    plot_events(ax, **time_series_events)
    ax.plot(df['Sensor2'], time_series, color='darkorange', label='Ambient')
    ax.plot(df['Sensor3'], time_series, color='crimson', label='Active')
    ax.set_title("NIR Timeseries")
    ax.legend(loc='lower left')
    ax.invert_yaxis()

    # plot the depth corrected Force
    ax = fig.add_subplot(gs[:, 2])
    ax.grid(True, axis='y', which='both', alpha=0.5)
    final_depth = 'acc_depth' if acc_cols is not None else 'depth'

    plot_events(ax, surface=cropped[final_depth].iloc[surface],
                plot_type='vertical')
    ax.plot(cropped['Sensor1'], cropped[final_depth], color='k', label='Raw Force')
    ax.set_title("Force Depth Corrected")
    ax.legend(loc='lower left', fontsize='small')
    ax.set_xlim((0, 4096))
    ax.set_ylabel('Depth [cm]')

    # plot depth corrected NIR data
    ax = fig.add_subplot(gs[:, 3])
    ax.grid(True, axis='y', alpha=0.5)
    plot_events(ax, surface=cropped['depth'].iloc[surface], plot_type='vertical')
    ax.plot(cropped['Sensor2'], cropped[final_depth] + 2.0, alpha=0.3, color='darkorange', label='Ambient')
    ax.plot(cropped['Sensor3'], cropped[final_depth], alpha=0.3, color='crimson', label='Active')
    ax.plot(cropped['clean'], cropped[final_depth], color='crimson', label='Clean Active')
    ax.set_title("NIR Depth Corrected")
    ax.legend(loc='lower left', fontsize='small')

    # plot the acceleration as a sub-panel with events, handle acceleration or all 3 axis
    ax = fig.add_subplot(gs[0, 4])
    # Switch event direction plotting for horiz. time series
    time_series_events["plot_type"] = 'normal'
    if acc_cols is not None:
        plot_events(ax, **time_series_events)
        acc_colors = ['darkslategrey', 'darkgreen', 'darkorange']

        for aidx, c in enumerate(acc_cols):
            ax.plot(time_series, df[c], color=acc_colors[aidx], label=c)
        ax.set_ylabel("Acceleration [g's]")
        ax.set_xlabel('Time [s]')
        ax.set_title('Accelerometer')
        ax.legend(fontsize='xx-small')

    # plot the depth as a sub-panel with events
    ax = fig.add_subplot(gs[1, 4])
    ax.set_title('Depth')
    plot_events(ax, **time_series_events)
    labels = ['Baro.', 'Acc.', 'Avg.']
    colors = ['navy', 'mediumseagreen', 'tomato']
    label_color_column = [(labels[i], colors[i], c) for i, c in enumerate(depth_cols)]

    for label, color, col in label_color_column:
        ax.plot(time_series, df[col], color=color, label=label)

    # extra = get_constrained_baro_depth(df, acc_axis=detect_col)
    #
    # ax.plot(extra.index, extra['depth'], label='constr.')
    # ax.legend(loc='upper right', fontsize='xx-small')
    # ax.set_ylabel('Depth from Max Height [cm]')
    # limits for depth
    buffer = 0.3
    n_samples = len(df.index)
    lim_idx1 = get_index_from_ratio(start, 1-buffer, n_samples)
    lim_idx2 = get_index_from_ratio(stop, 1 + buffer, n_samples)
    ts1, ts2 = time_series[lim_idx1], time_series[lim_idx2]
    depth1 = df[depth_cols].iloc[lim_idx1].max() * (1-buffer)
    depth2 = df[depth_cols].iloc[lim_idx2].min() * (1+buffer)
    if abs(depth1) < 5:
        depth1 = 5

    ax.set_xlim(ts1, ts2)
    ax.set_ylim(*sorted([depth1, depth2]))
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
