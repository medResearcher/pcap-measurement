#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2015 Quentin De Coninck
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  To install on this machine: matplotlib, numpy

from __future__ import print_function
from math import ceil

import argparse
import common as co
import common_graph as cog
import matplotlib
# Do not use any X11 backend
matplotlib.use('Agg')
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import matplotlib.pyplot as plt
import mptcp
import numpy as np
import os
import sys
import tcp

##################################################
##                  ARGUMENTS                   ##
##################################################

parser = argparse.ArgumentParser(
    description="Summarize stat files generated by analyze")
parser.add_argument("-s",
                    "--stat", help="directory where the stat files are stored", default=co.DEF_STAT_DIR + '_' + co.DEF_IFACE)
parser.add_argument('-S',
                    "--sums", help="directory where the summary graphs will be stored", default=co.DEF_SUMS_DIR + '_' + co.DEF_IFACE)
parser.add_argument("-d",
                    "--dirs", help="list of directories to aggregate", nargs="+")

args = parser.parse_args()
stat_dir_exp = os.path.abspath(os.path.expanduser(args.stat))
sums_dir_exp = os.path.abspath(os.path.expanduser(args.sums))
co.check_directory_exists(sums_dir_exp)

##################################################
##                 GET THE DATA                 ##
##################################################

connections = cog.fetch_valid_data(stat_dir_exp, args)
# multiflow_connections, singleflow_connections = cog.get_multiflow_connections(connections)

##################################################
##               PLOTTING RESULTS               ##
##################################################

RETRANS = 'Retransmission'
REINJ = 'Reinjection'
min_duration = 0.001
log_file = sys.stdout

location_time = {co.S2D: {REINJ: [], RETRANS: []}, co.D2S: {REINJ: [], RETRANS: []}}
reinj_first_sec = []
graph_fname = "merge_time_reinjection_retranmission"
base_graph_path = os.path.join(sums_dir_exp, graph_fname)
count_duration = {co.S2D: 0, co.D2S: 0}
count_low_duration = {co.S2D: 0, co.D2S: 0}
for fname, conns in connections.iteritems():
    for conn_id, conn in conns.iteritems():
        # We never know, still check
        if isinstance(conn, mptcp.MPTCPConnection):
            duration = conn.attr.get(co.DURATION, 0.0)
            if duration <= min_duration:
                continue

            start_time = conn.attr.get(co.START, float('inf'))
            if start_time == float('inf'):
                continue

            min_start_time = start_time
            max_end_time = 0.0
            for flow_id, flow in conn.flows.iteritems():
                flow_start_time = flow.attr.get(co.START, float('inf'))
                min_start_time = min(min_start_time, flow_start_time)
                if flow_start_time == float('inf'):
                    continue
                flow_start_time_int = long(flow_start_time)
                flow_start_time_dec = float('0.' + str(flow_start_time - flow_start_time_int).split('.')[1])
                flow_start_time_dec = ceil(flow_start_time_dec * 1000000) / 1000000.0
                flow_duration_int = long(flow.attr.get(co.DURATION, 0.0))
                flow_duration_dec = float('0.' + '{0:.6f}'.format(flow.attr.get(co.DURATION, 0.0) - flow_duration_int).split('.')[1])
                flow_duration_dec = ceil(flow_duration_dec * 1000000) / 1000000.0
                flow_end_time_int =  flow_start_time_int + flow_duration_int
                flow_end_time_dec = flow_start_time_dec + flow_duration_dec
                flow_end_time = flow_end_time_int + flow_end_time_dec
                max_end_time = max(max_end_time, flow_end_time)

            start_time = min_start_time
            start_time_int = long(start_time)
            start_time_dec = float('0.' + str(start_time - start_time_int).split('.')[1])
            start_time_dec = ceil(start_time_dec * 1000000) / 1000000.0
            end_time_int = long(max_end_time)
            end_time_dec = float('0.' + str(max_end_time - end_time_int).split('.')[1])
            end_time_dec = ceil(end_time_dec * 1000000) / 1000000.0
            duration_dec = (end_time_dec - start_time_dec)
            duration_int = (end_time_int - start_time_int)
            duration = duration_dec + duration_int
            warning_reinj = open(os.path.join(sums_dir_exp, 'warning_reinj.txt'), 'w')
            look_95 = open(os.path.join(sums_dir_exp, 'look95.txt'), 'w')
            look_100 = open(os.path.join(sums_dir_exp, 'look100.txt'), 'w')
            warning_retrans = open(os.path.join(sums_dir_exp, 'warning_retrans.txt'), 'w')
            for direction in [co.D2S]:
                for flow_id, flow in conn.flows.iteritems():
                    if co.REINJ_ORIG_TIMESTAMP in flow.attr[direction] and co.START in flow.attr:
                        for ts in flow.attr[direction][co.REINJ_ORIG_TIMESTAMP]:
                            # Some tricks to avoid floating errors
                            ts_int = long(ts)
                            ts_dec = float('0.' + str(ts - ts_int).split('.')[1])
                            ts_dec = ceil(ts_dec * 1000000) / 1000000.0
                            ts_dec_delta = ts_dec - start_time_dec
                            ts_fix_int = ts_int - start_time_int
                            ts_fix = ts_fix_int + ts_dec_delta
                            # location_time[direction]['all']["Reinjections"].append(max(min(ts_fix / duration, 1.0), 0.0))
                            location_time[direction][REINJ].append(ts_fix / duration)
                            if direction == co.D2S and ts_fix / duration < 0.0 or ts_fix / duration > 1.0:
                                print(fname, conn_id, flow_id, ts_fix / duration, ts, start_time, ts_fix, duration, file=warning_reinj)
                            if direction == co.D2S and ts_fix <= 1.0:
                                reinj_first_sec.append((conn_id, flow_id))
                            if direction == co.D2S and ts_fix / duration >= 0.92 and ts_fix / duration <= 0.97:
                                print(fname, conn_id, flow_id, ts_fix / duration, ts, start_time, ts_fix, duration, file=look_95)
                            if direction == co.D2S and ts_fix / duration >= 0.99:
                                print("LOOK 100", fname, conn_id, flow_id, ts_fix / duration, ts, start_time, ts_fix, duration, file=log_file)

            for direction in co.DIRECTIONS:
                for flow_id, flow in conn.flows.iteritems():
                    if co.TIMESTAMP_RETRANS in flow.attr[direction] and co.START in flow.attr:
                        # start_flow_time = flow.attr[co.START]
                        # time_diff = start_flow_time - start_time
                        for ts in flow.attr[direction][co.TIMESTAMP_RETRANS]:
                            # Some tricks to avoid floating errors
                            ts_int = long(ts)
                            ts_dec = float('0.' + str(ts - ts_int).split('.')[1])
                            ts_dec = ceil(ts_dec * 1000000) / 1000000.0
                            ts_dec_delta = ts_dec - start_time_dec
                            ts_fix_int = ts_int - start_time_int
                            ts_fix = ts_fix_int + ts_dec_delta
                            # location_time[direction][RETRANS].append(max(min((ts + time_diff) / duration, 1.0), 0.0))
                            location_time[direction][RETRANS].append(ts_fix / duration)
                            if ts_fix / duration < 0 or ts_fix / duration > 1:
                                print("NOOOOO", fname, conn_id, flow_id, duration, start_time, ts, ts_fix, ts_fix / duration, file=log_file)
                            if direction == co.D2S and ts_fix / duration >= 0.99:
                                print("LOOK RETRANS", fname, conn_id, flow_id, duration, ts_fix / duration, file=log_file)
                                count_duration[direction] += 1
                                if duration < 3.0:
                                    count_low_duration[direction] += 1
                            # if direction == co.D2S and (ts + time_diff) / duration < 0.0 or (ts + time_diff) / duration > 1.0:
                            #     print(fname, conn_id, flow_id, ts / duration, file=warning_retrans)


ls = {RETRANS: '--', REINJ: '-'}
color = {RETRANS: 'blue', REINJ: 'red'}
for direction in co.DIRECTIONS:
    plt.figure()
    plt.clf()
    fig, ax = plt.subplots()

    for dataset in [RETRANS, REINJ]:
        sample = np.array(sorted(location_time[direction][dataset]))
        sorted_array = np.sort(sample)
        yvals = np.arange(len(sorted_array)) / float(len(sorted_array))
        if len(sorted_array) > 0:
            # Add a last point
            sorted_array = np.append(sorted_array, sorted_array[-1])
            yvals = np.append(yvals, 1.0)
            # Log plot
            ax.plot(sorted_array, yvals, color=color[dataset], linewidth=2, linestyle=ls[dataset], label=dataset)

    ax.set_xscale('log')
    ax.legend(loc='lower right')

    plt.xlabel('Fraction of connection duration', fontsize=18)
    plt.ylabel("CDF", fontsize=18)
    plt.savefig(os.path.splitext(base_graph_path)[0] + '_log_' + direction + '.pdf')
    plt.close('all')

    # No log
    plt.figure()
    plt.clf()
    fig, ax = plt.subplots()

    for dataset in [RETRANS, REINJ]:
        sample = np.array(sorted(location_time[direction][dataset]))
        sorted_array = np.sort(sample)
        yvals = np.arange(len(sorted_array)) / float(len(sorted_array))
        if len(sorted_array) > 0:
            # Add a last point
            sorted_array = np.append(sorted_array, sorted_array[-1])
            yvals = np.append(yvals, 1.0)
            # Log plot
            ax.plot(sorted_array, yvals, color=color[dataset], linewidth=2, linestyle=ls[dataset], label=dataset)

    ax.legend(loc='lower right')

    plt.xlabel('Fraction of connection duration', fontsize=18)
    plt.ylabel("CDF", fontsize=18)
    plt.savefig(os.path.splitext(base_graph_path)[0] + '_' + direction + '.pdf')
    plt.close('all')

# co.plot_cdfs_with_direction(location_time, color, 'Fraction of connection duration', base_graph_path, natural=True)
#co.plot_cdfs_with_direction(location_time_nocorrect, color, 'Fraction of connection duration', base_graph_path + '_nocorrect', natural=True)
print(reinj_first_sec, file=log_file)
print(len(reinj_first_sec), "reinjections in 1 second", file=log_file)
warning_reinj.close()
look_95.close()
look_100.close()
warning_retrans.close()
for direction in co.DIRECTIONS:
    print("DURATION", count_duration[direction], count_low_duration[direction], file=log_file)
