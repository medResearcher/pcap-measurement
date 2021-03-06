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
multiflow_connections, singleflow_connections = cog.get_multiflow_connections(connections)

##################################################
##               PLOTTING RESULTS               ##
##################################################


def plot(connections, multiflow_connections, sums_dir_exp):
    threshold_handover = 1.0
    syn_first_additional_sf = []
    syn_additional_sfs = []
    time_handover = []
    time_handover_conn = []
    time_handover_conn_info = []
    react_handover = []
    handover_conns = {}
    second_sf_handover = []
    log_file = sys.stdout
    less_200ms = 0
    less_1s = 0
    more_60s = 0
    more_3600s = 0
    less_200ms_second = 0
    less_1s_second = 0
    more_60s_second = 0
    more_3600s_second = 0
    # Look only at multiple subflows connections
    for fname, conns in multiflow_connections.iteritems():
        handover_conns[fname] = {}
        for conn_id, conn in conns.iteritems():
            # First find initial subflow timestamp
            initial_sf_ts = float('inf')
            initial_sf_id = None
            last_acks = []
            min_time_last_ack = float('inf')
            for flow_id, flow in conn.flows.iteritems():
                if co.START not in flow.attr or flow.attr[co.SADDR] == co.IP_PROXY:
                    continue
                if flow.attr[co.START] < initial_sf_ts:
                    initial_sf_ts = flow.attr[co.START]
                    initial_sf_id = flow_id
                flow_bytes = 0
                for direction in co.DIRECTIONS:
                    flow_bytes += flow.attr[direction].get(co.BYTES_DATA, 0)
                if flow_bytes > 0 and flow.attr[co.S2C].get(co.TIME_LAST_ACK_TCP, 0.0) > 0.0:
                    last_acks.append(flow.attr[co.S2C][co.TIME_LAST_ACK_TCP])
                    min_time_last_ack = min(min_time_last_ack, flow.attr[co.S2C][co.TIME_LAST_ACK_TCP])

            if initial_sf_ts == float('inf'):
                continue

            # Now store the delta and record connections with handover
            handover_detected = False
            count_flows = 0
            min_delta = float('inf')
            flow_id_min_delta = None
            for flow_id, flow in conn.flows.iteritems():
                if co.START not in flow.attr or flow.attr[co.SADDR] == co.IP_PROXY:
                    continue
                delta = flow.attr[co.START] - initial_sf_ts
                min_last_acks = float('inf')
                if len(last_acks) >= 1:
                    min_last_acks = min(last_acks)

                max_last_payload = 0 - float('inf')
                if flow.attr[co.C2S].get(co.BYTES, 0) > 0 or flow.attr[co.S2C].get(co.BYTES, 0) > 0:
                    max_last_payload = max([flow.attr[direction][co.TIME_LAST_PAYLD] for direction in co.DIRECTIONS])
                handover_delta = flow.attr[co.START] + max_last_payload - min_last_acks
                if delta > 0.0:
                    min_delta = min(min_delta, delta)
                    if min_delta == delta:
                        flow_id_min_delta = flow_id
                    if delta < 0.01:
                        print(fname, conn_id, flow_id, delta)
                    syn_additional_sfs.append(delta)

                    if handover_delta > 0.0:
                        # A subflow is established after the last ack of the client seen --> Handover
                        time_handover.append(min_last_acks - initial_sf_ts)
                        react_handover.append(handover_delta)
                        last_acks.remove(min_last_acks)
                        if not handover_detected:
                            handover_detected = True
                            time_handover_conn.append(delta)
                            time_handover_conn_info.append((min_last_acks - initial_sf_ts, delta, fname, conn_id))
                            handover_conns[fname][conn_id] = conn
                    if delta >= 50000:
                        print("HUGE DELTA", fname, conn_id, flow_id, delta, file=log_file)

                    if delta <= 0.2:
                        less_200ms += 1
                    if delta <= 1:
                        less_1s += 1
                    if delta >= 60:
                        more_60s += 1
                    if delta >= 3600:
                        more_3600s += 1

            if flow_id_min_delta:
                syn_first_additional_sf.append(min_delta)
                if conn.flows[initial_sf_id].attr[co.S2C][co.TIME_LAST_ACK_TCP] < conn.flows[flow_id_min_delta].attr[co.START]:
                    # Handover between initial and second subflow
                    second_sf_handover.append(min_delta)
                if delta <= 0.2:
                    less_200ms_second += 1
                if delta <= 1:
                    less_1s_second += 1
                if delta >= 60:
                    more_60s_second += 1
                if delta >= 3600:
                    more_3600s_second += 1

    # Do a first CDF plot of the delta between initial SYN and additional ones
    base_graph_path = os.path.join(sums_dir_exp, 'cdf_delta_addtitional_syns')
    color = 'red'
    graph_fname = os.path.splitext(base_graph_path)[0] + "_cdf.pdf"
    graph_fname_log = os.path.splitext(base_graph_path)[0] + "_cdf_log.pdf"
    sample = np.array(sorted(syn_additional_sfs))
    sorted_array = np.sort(sample)
    yvals = np.arange(len(sorted_array)) / float(len(sorted_array))
    sample_2 = np.array(sorted(syn_first_additional_sf))
    sorted_array_2 = np.sort(sample_2)
    yvals_2 = np.arange(len(sorted_array_2)) / float(len(sorted_array_2))
    if len(sorted_array) > 0:
        # Add a last point
        sorted_array = np.append(sorted_array, sorted_array[-1])
        yvals = np.append(yvals, 1.0)

        sorted_array_2 = np.append(sorted_array_2, sorted_array_2[-1])
        yvals_2 = np.append(yvals_2, 1.0)

        # Log plot
        plt.figure()
        plt.clf()
        fig, ax = plt.subplots()
        ax.plot(sorted_array, yvals, color=color, linewidth=2, label="Additional subflows")
        ax.plot(sorted_array_2, yvals_2, color='blue', linestyle='--', linewidth=2, label="Second subflows")

        # Shrink current axis's height by 10% on the top
        # box = ax.get_position()
        # ax.set_position([box.x0, box.y0,
        #                  box.width, box.height * 0.9])
        ax.set_xscale('log')

        # Put a legend above current axis
        # ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.05), fancybox=True, shadow=True, ncol=ncol)
        ax.legend(loc='lower right')

        plt.xlim(xmin=0.01)
        plt.xlabel('Time between MP_JOIN and MP_CAP [s]', fontsize=24, labelpad=-2)
        plt.ylabel("CDF", fontsize=24)
        plt.savefig(graph_fname_log)
        plt.close('all')

    #     # Normal plot
    #     plt.figure()
    #     plt.clf()
    #     fig, ax = plt.subplots()
    #     ax.plot(sorted_array, yvals, color=color, linewidth=2, label="MP_JOIN - MP_CAP")
    #
    #     # Shrink current axis's height by 10% on the top
    #     # box = ax.get_position()
    #     # ax.set_position([box.x0, box.y0,
    #     #                  box.width, box.height * 0.9])
    #     # ax.set_xscale('log')
    #
    #     # Put a legend above current axis
    #     # ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.05), fancybox=True, shadow=True, ncol=ncol)
    #     ax.legend(loc='lower right')
    #
    #     plt.xlabel('Time [s]', fontsize=18)
    #     plt.ylabel("CDF", fontsize=18)
    #     plt.savefig(graph_fname)
    #     plt.close('all')

    # Now quantify in handover connections the amount of data not on the initial subflows
    bytes_init_sf = 0.0
    bytes_init_sfs = 0.0
    bytes_total = 0.0
    for fname, conns in handover_conns.iteritems():
        for conn_id, conn in conns.iteritems():
            # First find initial subflow timestamp
            initial_sf_ts = float('inf')
            for flow_id, flow in conn.flows.iteritems():
                if co.START not in flow.attr:
                    continue
                if flow.attr[co.START] < initial_sf_ts:
                    initial_sf_ts = flow.attr[co.START]

            min_delta = float('inf')
            for flow_id, flow in conn.flows.iteritems():
                if co.START not in flow.attr:
                    continue
                delta = flow.attr[co.START] - initial_sf_ts
                if delta > 0.0:
                    min_delta = min(min_delta, delta)

            # Now collect the amount of data on all subflows
            for flow_id, flow in conn.flows.iteritems():
                if co.START not in flow.attr:
                    continue
                delta = flow.attr[co.START] - initial_sf_ts
                for direction in co.DIRECTIONS:
                    bytes_total += flow.attr[direction].get(co.BYTES, 0)
                    if flow.attr[direction].get(co.BYTES, 0) >= 1000000000:
                        print("WARNING!!!", fname, conn_id, flow_id, bytes_total, file=log_file)
                    if delta <= min_delta:
                        # Initial subflows
                        bytes_init_sfs += flow.attr[direction].get(co.BYTES, 0)
                        if delta == 0.0:
                            # Initial subflow
                            bytes_init_sf += flow.attr[direction].get(co.BYTES, 0)

    # Log those values in the log file
    print("DELTA HANDOVER IN FILE delta_handover")
    co.save_data("delta_handover", sums_dir_exp, time_handover)
    print("REACT HANDOVER IN FILE react_handover")
    co.save_data("react_handover", sums_dir_exp, react_handover)
    print("REACT HANDOVER IN FILE time_handover_conn")
    co.save_data("time_handover_conn", sums_dir_exp, time_handover_conn)
    print("REACT HANDOVER IN FILE time_handover_conn_info")
    co.save_data("time_handover_conn_info", sums_dir_exp, time_handover_conn_info)
    print("SECOND SF HANDOVER IN FILE second_sf_handover")
    co.save_data("second_sf_handover", sums_dir_exp, second_sf_handover)
    print("QUANTIFY HANDOVER", file=log_file)
    print(bytes_init_sf, "BYTES ON INIT SF", bytes_init_sf * 100 / bytes_total, "%", file=log_file)
    print(bytes_init_sfs, "BYTES ON INIT SFS", bytes_init_sfs * 100 / bytes_total, "%", file=log_file)
    print("TOTAL BYTES", bytes_total, file=log_file)

    print("<= 200ms", less_200ms, less_200ms * 100.0 / len(syn_additional_sfs), "%")
    print("<= 1s", less_1s, less_1s * 100.0 / len(syn_additional_sfs), "%")
    print(">= 60s", more_60s, more_60s * 100.0 / len(syn_additional_sfs), "%")
    print(">= 3600s", more_3600s, more_3600s * 100.0 / len(syn_additional_sfs), "%")

    print("<= 200ms second", less_200ms_second, less_200ms_second * 100.0 / len(syn_first_additional_sf), "%")
    print("<= 1s second", less_1s_second, less_1s_second * 100.0 / len(syn_first_additional_sf), "%")
    print(">= 60s second", more_60s_second, more_60s_second * 100.0 / len(syn_first_additional_sf), "%")
    print(">= 3600s second", more_3600s_second, more_3600s_second * 100.0 / len(syn_first_additional_sf), "%")


plot(connections, multiflow_connections, sums_dir_exp)
