#!/usr/bin/env python

import sys
import os
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
import argparse

def open_adjust_profile(fname):
	"""
	Open a profile and make a dataframe for plotting
	"""

	# Collect the header
	header_info = {}

	with open(fname) as fp:
	    for i, line in enumerate(fp):
	        if '=' in line:
	            k,v = line.split('=')
	            k,v = (c.lower().strip() for c in [k,v])
	            header_info[k] = v
	        else:
	            header = i
	            break

	    fp.close()

	if 'radicl version' in  header_info.keys():
	    data_type = 'radicl'
	    columns = ['depth','sensor_1','sensor_2','sensor_3','sensor_4']

	else:
	    data_type = 'rad_app'
	    columns = ['sample','depth','sensor_1','sensor_2','sensor_3','sensor_4']

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

	#Account for physical location of the sensor, offset by 1.2cm
	S4.index = S4.index+3

	#Rejoin it back in
	new_df = pd.concat([new_df[['SENSOR {0}'.format(i) for i in range(1,4)]],S4],axis=1)

	#Interpolate
	new_df = new_df.interpolate(method='cubic') #Due to mismatch index interpolate
	return new_df

def enough_ambient(df):
	"""
	Check to see if there is enough ambient to remove
	"""

	S4 = df['SENSOR 4']
	value = (S4.max() - S4.min())/S4.mean()
	print("Ambient Sensor Change: %s"%value)
	if value > 1.0:
		return True
	else:
		print("Ambient threshhold is not met by this measurement!")
		return False


def ambient_removed(df):
	columns = ['SENSOR 1','SENSOR 2','SENSOR 3','SENSOR 4']
	profiles = columns[0:-1]
	new_df = df.copy()
	max_values = new_df[columns].max()
	min_values = new_df[columns].min()
	norm_values = max_values-min_values

	#normalize
	new_df[columns] = new_df[columns].subtract(min_values, axis=1)
	new_df[columns] = new_df[columns].div(norm_values, axis=1)
	new_df.plot()
	plt.show()

	#Remove the ambient from the normalized signal
	new_df[profiles] = new_df[profiles].subtract(new_df['SENSOR 4'],axis = 0)

	#bring back from the norm
	new_df = new_df.mul(norm_values,axis = 1)
	new_df = new_df.add(min_values,axis = 1)

	series = new_df.idxmin(axis=0)
	in_snow = np.max(series.values) #Find where were in the snow
	new_df = (new_df[new_df.loc[:in_snow] > 0]).dropna() #Trim off negative values
	new_df.index = new_df.index - new_df.index.max()
	return new_df

def main():
	parser = argparse.ArgumentParser(description='Plot various versions of probe data.')
	parser.add_argument('file', help='path to measurement', nargs='+')
	parser.add_argument('--ambient','-ab', dest='ambient', action='store_true',
	                    help='Use ambient to adjust signals')

	parser.add_argument('--smooth''-sm', dest='smooth',
	                    help='Provide a integer to describing number of windows to smooth over')

	parser.add_argument('--avg','-a', dest='average', action='store_true',
	                    help='Average all three sensors together')
	parser.add_argument('--compare','-c', dest='compare', action='store_true',
	                    help='Plots before and after sensors')
	parser.add_argument('--sensor','-sn', dest='sensor',type=int,
	                    help='plots only a specific sensor, must be between 1-4')

	args = parser.parse_args()

	#Provide a opportunity to look at lots
	if args.file != None and type(args.file)!=list:
		if os.path.isdir(args.file):
			filenames = os.listdir(args.file)
		elif os.path.isfile(args.file):
			filenames = [args.file]

	elif type(args.file)==list:
		filenames = args.file
	else:
		print("Please provide a directory or filename")
		sys.exit()

	for f in filenames:
		try:
			post_processed = False
			print('\n'+os.path.basename(f))
			print('='*len(f))
			#Open the file and set the index to depth
			df_o, data_type = open_adjust_profile(f)
			df = df_o.copy()


			if args.smooth != None:
				df = df.rolling(window = int(args.smooth)).mean()
				post_processed = True

			#Remove the ambient signal
			if args.ambient:
				if enough_ambient(df):
					df = shift_ambient_sensor(df)
					df = ambient_removed(df)
				post_processed = True

			print("Pre-processed profile:")
			print("\tNum of samples: {0}".format(len(df_o.index)))
			print("\tDepth achieved: {0:.1f}".format(min(df_o.index)))
			print("\tResolution: {0:.1f} pts/cm".format(abs(len(df_o.index)/min(df_o.index)-max(df_o.index))))

			if post_processed:
				print("\nPost-processed profile:")
				print("\tNum of samples: {0}".format(len(df.index)))
				print("\tDepth achieved: {0:.1f}".format(min(df.index)))
				print("\tResolution: {0:.1f} pts/cm".format(abs(len(df.index)/min(df.index)-max(df.index))))

			#Plot
			data = {}
			if args.average:
				data['Average'] = df[['SENSOR 1','SENSOR 2', 'SENSOR 3']].mean(axis = 1)

			elif args.sensor != None:
				if args.sensor in  [1,2,3,4]:
					col = "SENSOR {0}".format(args.sensor)
					data[col] = df[[col]]
			else:
				for i in range(1,5):
					col = 'SENSOR %s'%i
					data[col] = df[col]



			if args.compare:
				if args.average:
					data['Orig. Average'] = df_o.mean(axis = 1)
				else:
					for i in range(1,5):
						col = 'SENSOR %s'%i
						new_col = 'Orig. %s'%col
						data[new_col] = df_o[col]


			fig = plt.figure(figsize=(6,10))

			# Parse the datetime
			for k,d in data.items():
				plt.plot(d, d.index, label = k)

			plt.title(os.path.basename(f))
			plt.legend()
			plt.xlabel('Reflectance')
			plt.ylabel('Depth from Surface [cm]')
			plt.xlim([0,4100])
			plt.show()

		except Exception as e:
			print(e)


if __name__ == '__main__':
	main()