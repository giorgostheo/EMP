import warnings
warnings.simplefilter(action='ignore', category=DeprecationWarning)
import os, sys
sys.path.append(os.path.dirname(__file__))

import argparse
import pandas as pd
import numpy as np
from haversine import haversine
import math
from functools import wraps
import time
from datetime import timedelta
from scipy.interpolate import interp1d
from sklearn.cluster import OPTICS, DBSCAN
from scipy.spatial.distance import euclidean, pdist
from dtw import dtw
import pyproj
import geopandas as gpd
from shapely.geometry import Point
from shapely.ops import transform
# import torch
from dateutil.parser import parse



def timeit(func):
	'''
	This is the decorator that is added before every func that is part of the pipeline to measure execution time 
	'''
	@wraps(func)
	def timeit_wrapper(*args, **kwargs):
		start_time = time.perf_counter()
		result = func(*args, **kwargs)
		end_time = time.perf_counter()
		total_time = end_time - start_time
		print(f'Function {func.__name__} Took {total_time:.4f} seconds')
		return result
	return timeit_wrapper

@timeit
def init_df(df, oid, ts, ts_unit):
	'''
	Set oid, ts and rid columns for consistency + sort based on oid and ts
	'''
	result = df.sort_values(by=[oid, ts])  
	# print('Creating discrete object ids...')
	result['oid'] = result[oid].map({v: key for key, v in enumerate(result[oid].unique().tolist())})
	if result[ts].dtype=='O':
		ts_series = result[ts].apply(lambda a: parse(a).timestamp())
	elif result[ts].dtype=='int64':
		ts_series = result[ts]
	else:
		raise TypeError(f"dtype '{result[ts].dtype}' is not allowed")
	# print('Creating ts column...')
	result['ts'] = pd.to_datetime(ts_series,unit=ts_unit)
	# print('Creating per object record identifiers...')
	result['rid'] = [x for l in result.groupby('oid', group_keys=False).apply(lambda a: range(len(a))).tolist() for x in l]
	return result

@timeit
def drop_outliers(df, features, alpha):
	'''
	Find outliers on "feature" based on iqr and drop them
	'''

	def calc_outliers(series, alpha = 3):
		'''
		Returns a series of indexes of row that are to be concidered outliers, using the quantilies of the data.
		'''
		q25, q75 = series.quantile((0.25, 0.75))
		iqr = q75 - q25
		q_high = q75 + alpha*iqr
		q_low = q25 - alpha*iqr
		# return the indexes of rows that are over/under the threshold above
		return (series >q_high) | (series<q_low) , q_low, q_high

	if type(features) != list:
		features = features.split(',')

	ixs = []

	for feature in features:
		ix, low, high = calc_outliers(df[feature], int(alpha))
		ixs.append(ix.tolist())


	return df.loc[~pd.Series(list(map(any, zip(*ixs)))).reset_index(drop=True)].reset_index(drop=True)

@timeit
def speed_bearing(df):
	'''
	Calculate speed and bearing valeus based on coordinates.
	'''

	def calc(traj):
		if len(traj)==1: return pd.DataFrame([[0.0, 0.0]], dtype='float')
		tsdif = traj.ts.diff()[1:]
		coords = zip(traj[['lat', 'lon']].values, traj[['lat', 'lon']].values[1:], tsdif)

		speeds = []
		brgs = []

		for a, b, tsd in coords:
			speeds.append(haversine(a, b, 'nmi')/(tsd.seconds/3600))
			dLon = (b[1] - a[1])
			x = math.cos(math.radians(b[0])) * math.sin(math.radians(dLon))
			y = math.cos(math.radians(a[0])) * math.sin(math.radians(b[0])) - math.sin(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.cos(math.radians(dLon))
			brgs.append(np.degrees(np.arctan2(x,y)))

		return pd.DataFrame([pd.Series([speeds[0]]+speeds), pd.Series([brgs[0]]+brgs)], dtype='float').transpose()
		
	df[['sp', 'br']] = df.groupby('oid', group_keys=False).apply(lambda traj: calc(traj)).reset_index(drop=True)

	return df

@timeit
def read_csv(input_path):
	return pd.read_csv(input_path)

@timeit
def drop_duplicates(df, columns):
	return df.drop_duplicates(columns).reset_index(drop=True)

@timeit
def resample_gaps(df):
	'''
	Find outlier wrt to sampling rate and used that a threshold to detect gaps in sampling.
	Then resample these gaps using the median sampling value of the oid trajectory.
	'''

	def calc_outliers(series, alpha = 3):
		'''
		Returns a series of indexes of row that are to be concidered outliers, using the quantilies of the data.
		'''
		q25, q75 = series.quantile((0.25, 0.75))
		iqr = q75 - q25
		q_high = q75 + alpha*iqr
		q_low = q25 - alpha*iqr
		# return the indexes of rows that are over/under the threshold above
		return (series >q_high) | (series<q_low) , q_low, q_high


	def temporal_resampling_v2(df, gap_id, temporal_unit='s', rate='60S', method='linear', min_pts=1, speed_col='sp', label=1):
		# The Interpolate module of SciPy requires at least 2 Records
		
		if len(df) < min_pts or df.ts.diff().max().seconds<int(rate.removesuffix('S')):
			return df.iloc[0:0]

		# Define temp. axis and feature space
		x = pd.to_datetime(df['ts'], unit=temporal_unit).values.astype(np.int64)
		y = df.loc[:,(df.dtypes == int) | (df.dtypes== float)].values
		# Fetch the starting and ending timestamps of the trajectory
		dt_start = pd.to_datetime(df['ts'].min(), unit=temporal_unit)
		dt_end = pd.to_datetime(df['ts'].max(), unit=temporal_unit)
		# Interpolate
		f = interp1d(x, y, kind=method, axis=0)
		xnew_V3 = pd.date_range(start=dt_start.round(rate), end=dt_end, freq=rate, inclusive='right')

		# Reconstruct the new (resampled) dataframe
		df_RESAMPLED = pd.DataFrame(f(xnew_V3), columns=df.columns[(df.dtypes == int) | (df.dtypes== float)])
		if df_RESAMPLED.empty:
			return
		df_RESAMPLED.loc[:, 'ts'] = xnew_V3
		df_RESAMPLED.loc[:, 'gap_id'] = gap_id

		df_RESAMPLED.loc[:, 'oid'] = getattr(df.iloc[0, :], 'oid')
		df_RESAMPLED.loc[:, 'sp'] = haversine(df.iloc[0][['lat', 'lon']].values, df.iloc[1][['lat', 'lon']].values, 'nmi')/(df.ts.diff().iloc[-1].seconds/3600)
		return df_RESAMPLED
	

	def _resample_gaps(traj, gap_threshold):
		if len(traj)<3: return traj
		traj.reset_index(drop=True, inplace=True)
		median_sr = traj.ts.diff().median().seconds
		gaps = traj[(traj.ts.diff()>timedelta(seconds=gap_threshold))].index
		if len(gaps)==0:
			return traj

		lst = [temporal_resampling_v2(traj.iloc[gap-1:gap+1], ind, rate=f'{median_sr}S') for ind, gap in enumerate(gaps)]

		# print('1', lst)
		res = pd.concat([traj]+lst).sort_values(by=['oid', 'ts']).reset_index(drop=True)
		# print(res.head())
		return res

	gap_threshold = df.groupby('oid').apply(lambda tmp: calc_outliers(tmp.ts.diff())[2].seconds).mean()
	# for i in range(50):
	#     tmp = df.loc[df.oid==i].reset_index(drop=True)

	return df.groupby('oid', group_keys=False).apply(lambda traj: _resample_gaps(traj, gap_threshold)).reset_index(drop=True)

@timeit
def trips(df):
	'''
	Based on the records where sp<1 (from TRIPS), cluster (DBSCAN) and detect stopages (places where many records with sp<1 are found)
	'''
	def apply_trips(traj):
		used = False
		t_id = 0
		tids = []
		for status in traj.status.tolist():
			if status == 0:
				if used:
					used=False
					t_id+=1
				tids.append(-1)
			else:
				tids.append(t_id)
				used=True
		
		return tids

	df['status'] = df.sp.apply(lambda sp: 0 if sp<1 else 1)

	df['tid'] = df.groupby('oid').apply(apply_trips).explode().reset_index(drop=True)

	return df

@timeit
def stopages(df):
	data = df.loc[df.status==0][['lon', 'lat']].sample(frac=0.1).values
	# clustering = OPTICS(min_samples=0.01).fit(data)
	clustering = DBSCAN(0.01).fit(data)
	return [np.mean(data[clustering.labels_==i], axis=0) for i in range(clustering.labels_.max()+1)]

@timeit
def compress(df, dthr):
	# TODO: this should be done for each trip not for each oid.
	def td_tr(gdf, dthr, lat='lat', lon='lon'):
		'''
		td-tr as described by Meratnia and De by
		Input:
			gdf  : GeoDataFrame with geom column containing Shapely Points
			dthr : Distance threshold in Kilometers
		Output:
			simplified GeoDataFrame 
		'''
		gdf.reset_index(drop=True, inplace=True)
		if len(gdf)<=2:
			return gdf
		else:
			start = gdf.iloc[0]
			end   = gdf.iloc[-1]

			de = (end.ts - start.ts)/3600
			dlat = end[lat] - start[lat]
			dlon = end[lon] - start[lon]

			# distances for each point and the calulated one based on it and start
			dists = gdf.apply(lambda rec: dist_from_calced(rec, start, de, dlat, dlon), axis=1) 

			if dists.max()>dthr:
				return pd.concat([td_tr(gdf.iloc[:dists.idxmax()], dthr), td_tr(gdf.iloc[dists.idxmax():], dthr)])
			else:
				return gdf.iloc[[0,-1]]


	def dist_from_calced(rec, start, de, dlat, dlon, lat='lat', lon='lon'):
		di = (rec.ts - start.ts)/3600
		calced = (start[lat] + dlat * di / de, start[lon] + dlon * di / de)
		# return rec.geom.distance(calced)*100 
		return haversine(rec[['lat', 'lon']], calced)*100
		
	return df.groupby(['oid', 'tid'], group_keys=False).apply(td_tr, dthr)

@timeit
def cluster_trajectories(df, eps=0.01):
	# TODO same with compress
	dm = np.zeros((df.oid.max()+1,df.oid.max()+1))
	for i in range(df.oid.max()+1):
		for j in range(df.oid.max()+1):
			dm[i][j] = dtw(df.iloc[i][['lat', 'lon']].to_numpy(np.float64), df.iloc[j][['lat', 'lon']].to_numpy(np.float64)).distance

	clustering = DBSCAN(eps=eps, metric='precomputed').fit(dm)
	clustering.labels_

	df['dbscan'] = df.oid.apply(lambda a: clustering.labels_[a])

	return df

@timeit
def predict(df):
	def apply_pred(traj):
		if len(traj)<13:
			return traj

		test_trajectory = traj[-13:]
		gdf = gpd.GeoDataFrame( geometry=gpd.points_from_xy(test_trajectory[-11:].lon, test_trajectory[-11:].lat),
								columns=['dt_curr', 'dt_next'],
								crs=4326)
		gdf = gdf.to_crs(3857)
		lastpnt = gdf.iloc[-1].copy()
		# print(test_trajectory.ts)
		# print(test_trajectory.ts.dt.timestamp())
		gdf['dt_curr'] = (test_trajectory.ts.astype('int64') // 10**9).diff(1)[1:12].tolist()
		gdf['dt_next'] = (test_trajectory.ts.astype('int64') // 10**9).diff(1)[2:13].tolist()
		gdf['dlon_curr'] = gdf.geometry.x.diff()[1:]
		gdf['dlat_curr'] = gdf.geometry.y.diff()[1:]
		gdf = gdf[-10:].drop(['geometry'], axis=1)

		gdf[['dlon_curr', 'dlat_curr']] = (gdf[['dlon_curr', 'dlat_curr']] - np.array([0.604, 1.619])) / np.array([245.366, 232.757])
		gdf[['dt_curr', 'dt_next']] = (gdf[['dt_curr', 'dt_next']] - 0) / (1800 - 0)

		model = torch.jit.load('vrf_brest_proto_jit_trace.pth')

		prediction = model(
			torch.Tensor(gdf.values).unsqueeze(0),  # Input Trajectory/ies
			torch.Tensor([len(gdf)])                # Trajectory Length(s)
		)

		# Leave the numbers as-is; They are for de-normalizing the prediction
		preddiff = prediction.detach().numpy() * np.array([245.366, 232.757]) + np.array([0.604, 1.619])
		pred_pnt = (lastpnt.geometry.x+preddiff[0][0], lastpnt.geometry.y+preddiff[0][1])

		project = pyproj.Transformer.from_crs(pyproj.CRS('EPSG:3857'), pyproj.CRS('EPSG:4326'), always_xy=True).transform
		utm_point = transform(project, Point((pred_pnt)))
		predlon = utm_point.xy[0][0]
		predlat = utm_point.xy[1][0]

		return (predlon, predlat)

		# list = [np.nan for _ in range(6)] + [predlon, predlat, test_trajectory.t.iloc[-1]+3000, test_trajectory.oid.iloc[-1], test_trajectory.ts.iloc[-1] + timedelta(minutes=5)] + [np.nan for _ in range(7)]
		
		# # using loc methods
		# traj.loc[len(traj)] = list
		# traj['pred_id'] = [0 for _ in range(len(traj)-1)] + [1]

		# return traj.reset_index(drop=True)

	return df.groupby('oid', group_keys=False).apply(apply_pred)


@timeit
def main(input_path, oid, ts, feature, ts_unit='s'):
	
	df = read_csv(input_path)
	
	df = init_df(df, oid, ts, ts_unit)

	df = drop_duplicates(df, ['oid', 'ts'])

	df = drop_outliers(df, feature, 3)

	df = speed_bearing(df)

	df = resample_gaps(df)

	df = trips(df)
	
	stops = stopages(df)

	# compressed = compress(df, 2	)

	# df = cluster_trajectories(df, 0.01)

	# df = predict(df)

	return df, stops	
	# return df, stops, compressed

if __name__=='__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('input', metavar='FILE', help='Input file path')
	parser.add_argument('--oid', dest='oid', required=True, metavar='COLUMN', nargs="?", help='Specify the column with the unique ID for each object')
	parser.add_argument('--ts', dest='ts', required=True,  metavar='COLUMN', nargs="?", help='Column containing time information')
	parser.add_argument('--feature', dest='feature', required=True,  metavar='COLUMN', nargs="?", help='Feature that will be used for outlier drop')
	parser.add_argument('--ts-unit', dest='ts_unit',  metavar='str', nargs="?", default = 's', help='The unit of the arg (D,s,ms,us,ns) denote the unit, which is an integer or float number. Default="s"')
	args = parser.parse_args()

	main(args.input, args.oid, args.ts, args.feature, args.ts_unit)