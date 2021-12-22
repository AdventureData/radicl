#!/usr/bin/env python

import argparse
import os
import sys
import platform
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib

matplotlib.rcParams['agg.path.chunksize'] = 100000

def find_header(fname):
    """
    Find the header of any length
    Args:
        fname:

    Returns:
    """
    with open(fname) as fp:
        lines = fp.readlines()
        result = None

        for i, line in enumerate(lines):
            if ',' in line:
                result = i
                break

        return result


def plot_hi_res(fname=None, df=None):
    """
    Plots the timeseries, the depth corrected, and the depth data
    """
    if 'Linux' in platform.platform():
        matplotlib.use('TkAgg')
        
    names = {'Sensor1': 'Hardness', 'Sensor2': 'Ambient NIR', 'Sensor3': 'Active NIR'}

    if fname is not None:
        header = find_header(fname)
        print(header)
        df = pd.read_csv(fname, header=header)

    f, axes = plt.subplots(1, 3)
    # fig = matplotlib.pyplot.gcf()
    f.set_size_inches(8, 10)
    pseudo_depth = np.arange(0, len(df.index))

    print("Number of samples: {}".format(len(df.index)))
    print("Max depth achieved: {} cm".format(df['depth'].min()))

    ambient_shift = 6
    active_shift = 4.5

    for k, v in names.items():
        # Build the timeseries plot
        if 'Ambient' in v:
            d = df.index + ambient_shift
        elif "Active" in v:
            d = df.index + active_shift
        else:
            d = df.index

        # build time series plot oriented vertically
        axes[0].plot(df[k], pseudo_depth, label=v)

        # Build depth corrected
        axes[1].plot(df[k], df['depth'], label=v)

    # plot data as timeseries
    axes[0].set_title("Timeseries")
    axes[0].set_ylim(len(df.index), 0)
    axes[0].legend()
    axes[0].set_xlim((0, 4096))
    axes[0].set_ylabel('Time index')

    # plot data with depth
    axes[1].set_title("Depth Corrected")
    axes[1].legend()
    axes[1].set_xlim((0, 4096))
    axes[1].set_ylabel('Depth from max height [cm]')

    # plot the depth and accel
    axes[2].plot(pseudo_depth, df['acceleration'], 'g')
    axes[2].set_ylabel('Accelerometer [g]')
    axes[2].set_xlabel('time index')
    axes[2].set_title('Depth + Accelerometer')
    twin = axes[2].twinx()
    twin.plot(df['depth'], 'm')
    twin.set_ylabel('Depth from Max Height [cm]')

    plt.tight_layout()
    plt.show()


def open_adjust_profile(fname):
    """
    Open a profile and make a dataframe for plotting
    """

    # Collect the header
    header_info = {}

    with open(fname) as fp:
        for i, line in enumerate(fp):
            if '=' in line:
                k, v = line.split('=')
                k, v = (c.lower().strip() for c in [k, v])
                header_info[k] = v
            else:
                header = i
                break

        fp.close()

    if 'radicl version' in header_info.keys():
        data_type = 'radicl'
        columns = ['depth', 'sensor_1', 'sensor_2', 'sensor_3']

    else:
        data_type = 'rad_app'
        columns = [
            'sample',
            'depth',
            'sensor_1',
            'sensor_2',
            'sensor_3',
            'sensor_4']

    df = pd.read_csv(fname, header=header, names=columns)

    return df, data_type


def shift_ambient_sensor(df):
    """
    Shift the ambient data
    """
    new_df = df.copy()

    S4 = new_df['SENSOR 4'].copy()
    S4 = S4.to_frame()

    S4 = S4.sub(np.min(S4['SENSOR 4']), axis=1)

    # Account for physical location of the sensor, offset by 1.2cm
    S4.index = S4.index + 3

    # Rejoin it back in
    new_df = pd.concat(
        [new_df[['SENSOR {0}'.format(i) for i in range(1, 4)]], S4], axis=1)

    # Interpolate
    # Due to mismatch index interpolate
    new_df = new_df.interpolate(method='cubic')
    return new_df


def enough_ambient(df):
    """
    Check to see if there is enough ambient to remove
    """

    S4 = df['SENSOR 4']
    value = (S4.max() - S4.min()) / S4.mean()
    print("Ambient Sensor Change: %s" % value)
    if value > 1.0:
        return True
    else:
        print("Ambient threshhold is not met by this measurement!")
        return False


def ambient_removed(df):
    columns = ['SENSOR 1', 'SENSOR 2', 'SENSOR 3', 'SENSOR 4']
    profiles = columns[0:-1]
    new_df = df.copy()
    max_values = new_df[columns].max()
    min_values = new_df[columns].min()
    norm_values = max_values - min_values

    # normalize
    new_df[columns] = new_df[columns].subtract(min_values, axis=1)
    new_df[columns] = new_df[columns].div(norm_values, axis=1)
    new_df.plot()
    plt.show()

    # Remove the ambient from the normalized signal
    new_df[profiles] = new_df[profiles].subtract(new_df['SENSOR 4'], axis=0)

    # bring back from the norm
    new_df = new_df.mul(norm_values, axis=1)
    new_df = new_df.add(min_values, axis=1)

    series = new_df.idxmin(axis=0)
    in_snow = np.max(series.values)  # Find where were in the snow
    # Trim off negative values
    new_df = (new_df[new_df.loc[:in_snow] > 0]).dropna()
    new_df.index = new_df.index - new_df.index.max()
    return new_df


def plot_hi_res_cli():
    files = sys.argv[1:]

    for f in files:
        plot_hi_res(fname=f)


def main():
    parser = argparse.ArgumentParser(
        description='Plot various versions of probe data.')
    parser.add_argument('file', help='path to measurement', nargs='+')
    parser.add_argument('--ambient', '-ab', dest='ambient', action='store_true',
                        help='Use ambient to adjust signals')

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
            df_o, data_type = open_adjust_profile(f)
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

            fig = plt.figure(figsize=(6, 10))

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
