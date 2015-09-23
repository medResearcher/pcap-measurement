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
    # Compute here traffic from server to smartphone; the reverse may be done
    log_file = sys.stdout
    min_bytes = 1000000
    min_samples = 3
    # Computed only on MPTCP connections with at least 2 subflows and at least 3 samples on each considered SF
    diff_rtt = []
    color = 'red'
    graph_fname = "rtt_avg_diff_2sf.pdf"
    graph_full_path = os.path.join(sums_dir_exp, graph_fname)
    for fname, data in multiflow_connections.iteritems():
        for conn_id, conn in data.iteritems():
            if isinstance(conn, mptcp.MPTCPConnection):
                if conn.flows[0].attr[co.DADDR].startswith(co.PREFIX_IP_PROXY):
                    count_usable = 0
                    for flow_id, flow in conn.flows.iteritems():
                        if flow.attr[co.D2S].get(co.RTT_SAMPLES, 0) >= min_samples:
                            count_usable += 1

                    if count_usable < 2:
                        continue

                    rtt_best_sf = float('inf')
                    rtt_worst_sf = -1.0
                    for flow_id, flow in conn.flows.iteritems():
                        if flow.attr[co.D2S].get(co.RTT_SAMPLES, 0) >= min_samples:
                            rtt_best_sf = min(rtt_best_sf, flow.attr[co.D2S][co.RTT_AVG])
                            rtt_worst_sf = max(rtt_worst_sf, flow.attr[co.D2S][co.RTT_AVG])
                    if rtt_worst_sf - rtt_best_sf <= 1.0:
                        print(conn_id, rtt_worst_sf - rtt_best_sf)
                    diff_rtt.append(rtt_worst_sf - rtt_best_sf)

    sample = np.array(sorted(diff_rtt))
    sorted_array = np.sort(sample)
    yvals = np.arange(len(sorted_array)) / float(len(sorted_array))
    if len(sorted_array) > 0:
        # Add a last point
        sorted_array = np.append(sorted_array, sorted_array[-1])
        yvals = np.append(yvals, 1.0)

        # Log plot
        plt.figure()
        plt.clf()
        fig, ax = plt.subplots()
        ax.plot(sorted_array, yvals, color=color, linewidth=2, label="Worst - Best")

        # Shrink current axis's height by 10% on the top
        # box = ax.get_position()
        # ax.set_position([box.x0, box.y0,
        #                  box.width, box.height * 0.9])
        ax.set_xscale('log')

        # Put a legend above current axis
        # ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.05), fancybox=True, shadow=True, ncol=ncol)
        ax.legend(loc='lower right')

        plt.xlabel('RTT [ms]', fontsize=18)
        plt.ylabel("CDF", fontsize=18)
        plt.savefig(graph_full_path)
        plt.close('all')

# co.plot_cdfs_natural(results, ['red', 'blue', 'green', 'black'], 'Initial SF AVG RTT - Second SF AVG RTT', os.path.splitext(graph_full_path)[0] + '.pdf')
plot(connections, multiflow_connections, sums_dir_exp)
