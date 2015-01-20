#! /usr/bin/python
# -*- coding: utf-8 -*-
#
#  Copyright 2015 Matthieu Baerts & Quentin De Coninck
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

##################################################
##                   IMPORTS                    ##
##################################################

from common import *
from mptcp import *
from tcp import *

import argparse
import Gnuplot
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import os
import os.path
import pickle

##################################################
##                  CONSTANTS                   ##
##################################################

# The default stat directory
DEF_STAT_DIR = 'stats'

##################################################
##                  ARGUMENTS                   ##
##################################################

parser = argparse.ArgumentParser(
    description="Summarize stat files generated by analyze")
parser.add_argument("-s",
                    "--stat", help="directory where the stat files are stored", default=DEF_STAT_DIR)
parser.add_argument("-a",
                    "--app", help="application results to summarize", default="")
parser.add_argument(
    "time", help="aggregate data in specified time, in format START,STOP")

args = parser.parse_args()

split_agg = args.time.split(',')

if not len(split_agg) == 2 or not is_number(split_agg[0]) or not is_number(split_agg[1]):
    print("The aggregation argument is not well formatted", file=sys.stderr)
    parser.print_help()
    exit(1)

start_time = split_agg[0]
stop_time = split_agg[1]

if int(start_time) > int(stop_time):
    print("The start time is posterior to the stop time", file=sys.stderr)
    parser.print_help()
    exit(2)

stat_dir_exp = os.path.abspath(os.path.expanduser(args.stat))

##################################################
##                 GET THE DATA                 ##
##################################################

check_directory_exists(stat_dir_exp)
connections = {}
for dirpath, dirnames, filenames in os.walk(stat_dir_exp):
    for fname in filenames:
        if args.app in fname:
            try:
                stat_file = open(os.path.join(dirpath, fname), 'r')
                connections[fname] = pickle.load(stat_file)
                stat_file.close()
            except IOError as e:
                print(str(e) + ': skip stat file ' + fname, file=sys.stderr)

##################################################
##               PLOTTING RESULTS               ##
##################################################

def plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname):

    matplotlib.rcParams.update({'font.size': 8})

    # Convert Python arrays to numpy arrays (easier for mean and std)
    for cond, elements in aggl_res.iteritems():
        for label, array in elements.iteritems():
            elements[label] = np.array(array)

    N = len(aggl_res)
    nb_subbars = len(label_names)
    ind = np.arange(N)
    labels = []
    values = {}
    for label_name in label_names:
        values[label_name] = ([], [])

    width = (1.00 / nb_subbars) - (0.1 / nb_subbars)        # the width of the bars
    fig, ax = plt.subplots()

    # So far, simply count the number of connections
    for cond, elements in aggl_res.iteritems():
        labels.append(cond)
        for label_name in label_names:
            values[label_name][0].append(elements[label_name].mean())
            values[label_name][1].append(elements[label_name].std())

    bars = []
    labels_names = []
    zero_bars = []
    count = 0
    for label_name, (mean, std) in values.iteritems():
        bar = ax.bar(ind + (count * width), mean, width, color=color[count], yerr=std, ecolor=ecolor[count])
        bars.append(bar)
        zero_bars.append(bar[0])
        labels_names.append(label_name)
        count += 1

    # add some text for labels, title and axes ticks
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(ind + width)
    ax.set_xticklabels(labels)

    ax.legend(zero_bars, labels_names)


    def autolabel(rects):
        # attach some text labels
        for rect in rects:
            height = rect.get_height()
            ax.text(rect.get_x() + rect.get_width() / 2., 1.05 * height, '%d' % int(height),
                    ha='center', va='bottom')

    for bar in bars:
        autolabel(bar)

    plt.savefig(graph_fname)


def get_experiment_condition(fname):
    """ Return a string of the format protocol_condition (e.g. tcp_both4TCD100m) """
    app_index = fname.index(args.app)
    dash_index = fname.index("-")
    end_index = fname[:dash_index].rindex("_")
    return fname[:app_index] + fname[app_index + len(args.app) + 1:end_index]


def count_interesting_connections(data):
    """ Return the number of interesting connections in data """
    count = 0
    tot = 0
    for k, v in data.iteritems():
        if isinstance(v, MPTCPConnection):
            for subflow_id, flow in v.flows.iteritems():
                if flow.attr[IF]:
                    count += 1
                if flow.attr[DADDR]:
                    tot += 1

        elif isinstance(v, TCPConnection):
            # Check the key k
            # An interesting flow has an IF field
            if v.flow.attr[IF]:
                count += 1
            # All flows have a DADDR field
            if v.flow.attr[DADDR]:
                tot += 1
    return tot, count

def bar_chart_count_connections():
    aggl_res = {}
    tot_lbl = 'Total Connections'
    tot_flw_lbl = 'Total Flows'
    tot_int_lbl = 'Interesting Flows'
    label_names = ['Total Connections', 'Total Flows', 'Interesting Flows']
    color = ['b', 'g', 'r']
    ecolor = ['g', 'r', 'b']
    ylabel = 'Number of connections'
    title = 'Counts of total and interesting connections of ' + args.app
    graph_fname = "count_" + args.app + "_" + start_time + "_" + stop_time + '.pdf'

    # Need to agglomerate same tests
    for fname, data in connections.iteritems():
        condition = get_experiment_condition(fname)
        tot_flow, tot_int = count_interesting_connections(data)
        if condition in aggl_res:
            aggl_res[condition][tot_lbl] += [len(data)]
            aggl_res[condition][tot_flw_lbl] += [tot_flow]
            aggl_res[condition][tot_int_lbl] += [tot_int]
        else:
            aggl_res[condition] = {
                tot_lbl: [len(data)], tot_flw_lbl: [tot_flow], tot_int_lbl: [tot_int]}

    plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname)


def bar_chart_bandwidth():
    aggl_res = {}
    tot_lbl = 'Bytes s2d'
    tot_flw_lbl = 'Bytes d2s'
    label_names = ['Bytes s2d', 'Bytes d2s']
    color = ['b', 'g']
    ecolor = ['g', 'r']
    ylabel = 'Bytes'
    title = 'Number of bytes transfered of ' + args.app
    graph_fname = "bytes_" + args.app + "_" + start_time + "_" + stop_time + '.pdf'

    # Need to agglomerate same tests
    for fname, data in connections.iteritems():
        condition = get_experiment_condition(fname)
        s2d = 0
        d2s = 0
        for conn_id, conn in data.iteritems():
            if isinstance(conn, MPTCPConnection):
                data = conn.attr
            elif isinstance(conn, TCPConnection):
                data = conn.flow.attr
            here = [i for i in data.keys() if i in [BYTES_S2D, BYTES_D2S]]
            if not len(here) == 2:
                continue
            s2d += data[BYTES_S2D]
            d2s += data[BYTES_D2S]


        if condition in aggl_res:
            aggl_res[condition][tot_lbl] += [s2d]
            aggl_res[condition][tot_flw_lbl] += [d2s]
        else:
            aggl_res[condition] = {
                tot_lbl: [s2d], tot_flw_lbl: [d2s]}

    plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname)


def bar_chart_bandwidth_smart():
    aggl_res = {}
    tot_lbl = 'Bytes s2d'
    tot_flw_lbl = 'Bytes d2s'
    label_names = ['Bytes s2d', 'Bytes d2s']
    color = ['b', 'g']
    ecolor = ['g', 'r']
    ylabel = 'Bytes'
    title = 'Number of bytes transfered of ' + args.app
    graph_fname = "bytes_" + args.app + "_" + start_time + "_" + stop_time + '.pdf'

    # Need to agglomerate same tests
    for fname, data in connections.iteritems():
        condition = get_experiment_condition(fname)
        for conn_id, conn in data.iteritems():
            if isinstance(conn, MPTCPConnection):
                data = conn.attr
            elif isinstance(conn, TCPConnection):
                data = conn.flow.attr
            here = [i for i in data.keys() if i in [BYTES_S2D, BYTES_D2S]]
            if not len(here) == 2:
                continue
            if condition in aggl_res:
                aggl_res[condition][tot_lbl] += [data[BYTES_S2D]]
                aggl_res[condition][tot_flw_lbl] += [data[BYTES_D2S]]
            else:
                aggl_res[condition] = {
                    tot_lbl: [data[BYTES_S2D]], tot_flw_lbl: [data[BYTES_D2S]]}

    plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname)


def bar_chart_duration():
    aggl_res = {}
    tot_int_lbl = 'Duration'
    label_names = ['Duration']
    color = ['r']
    ecolor = ['b']
    ylabel = 'Number of seconds'
    title = 'Time of connections of ' + args.app
    graph_fname = "duration_" + args.app + "_" + start_time + "_" + stop_time + '.pdf'

    # Need to agglomerate same tests
    for fname, data in connections.iteritems():
        condition = get_experiment_condition(fname)
        for conn_id, conn in data.iteritems():
            if isinstance(conn, MPTCPConnection):
                data = conn.attr
            elif isinstance(conn, TCPConnection):
                data = conn.flow.attr
            here = [i for i in data.keys() if i in [DURATION]]
            if not len(here) == 1:
                continue
            if condition in aggl_res:
                aggl_res[condition][tot_int_lbl] += [data[DURATION]]
            else:
                aggl_res[condition] = {tot_int_lbl: [data[DURATION]]}

    plot_bar_chart(aggl_res, label_names, color, ecolor, ylabel, title, graph_fname)

bar_chart_count_connections()
bar_chart_bandwidth()
bar_chart_duration()
print("End of summary")
