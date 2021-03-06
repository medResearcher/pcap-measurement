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

nb_conns = 0
nb_packets = 0
nb_bytes = 0
nb_bytes_tcp = 0
nb_bytes_tcp_dir = {co.C2S: 0, co.S2C: 0}
nb_conns_port = {}
nb_bytes_port = {}

for fname, conns in connections.iteritems():
    for conn_id, conn in conns.iteritems():
        nb_conns += 1
        port = conn.flows[0].attr.get(co.SOCKS_PORT, conn.attr.get(co.SOCKS_PORT, None))
        if port and port not in nb_conns_port:
            nb_conns_port[port] = 1
            nb_bytes_port[port] = 0
        elif port:
            nb_conns_port[port] += 1
        for direction in co.DIRECTIONS:
            if conn.attr[direction][co.BYTES_MPTCPTRACE] > 1000000000:
                print("MPTCP", fname, conn_id, direction, conn.attr[direction][co.BYTES_MPTCPTRACE])
            nb_bytes += conn.attr[direction][co.BYTES_MPTCPTRACE]
            for flow_id, flow in conn.flows.iteritems():
                nb_packets += flow.attr[direction].get(co.PACKS, 0)
                if flow.attr[direction].get(co.BYTES_DATA, 0) > 1000000000:
                    print("TCP", fname, conn_id, flow_id, direction, flow.attr[direction].get(co.BYTES_DATA, 0))
                nb_bytes_tcp += flow.attr[direction].get(co.BYTES_DATA, 0)
                nb_bytes_tcp_dir[direction] += flow.attr[direction].get(co.BYTES_DATA, 0)
                if port is not None:
                    nb_bytes_port[port] += flow.attr[direction].get(co.BYTES_DATA, 0)

print("TRACE 1")
print("NB CONNS", nb_conns)
print("NB PACKETS", nb_packets)
print("NB BYTES MPTCP", nb_bytes)
print("NB BYTES", nb_bytes_tcp)
print("NB BYTES DIR", nb_bytes_tcp_dir)
print("PORT CONN", nb_conns_port)
print("PORT BYTES", nb_bytes_port)


nb_conns = 0
nb_packets = 0
nb_bytes = 0
nb_bytes_tcp = 0
nb_bytes_tcp_dir = {co.C2S: 0, co.S2C: 0}
nb_conns_port = {}
nb_bytes_port = {}

for fname, conns in multiflow_connections.iteritems():
    for conn_id, conn in conns.iteritems():
        if len(conn.flows) < 2:
            continue
        nb_conns += 1
        port = conn.flows[0].attr.get(co.SOCKS_PORT, conn.attr.get(co.SOCKS_PORT, None))
        if port and port not in nb_conns_port:
            nb_conns_port[port] = 1
            nb_bytes_port[port] = 0
        elif port:
            nb_conns_port[port] += 1
        for direction in co.DIRECTIONS:
            if conn.attr[direction][co.BYTES_MPTCPTRACE] > 1000000000:
                print("MPTCP", fname, conn_id, direction, conn.attr[direction][co.BYTES_MPTCPTRACE])
            nb_bytes += conn.attr[direction][co.BYTES_MPTCPTRACE]
            for flow_id, flow in conn.flows.iteritems():
                nb_packets += flow.attr[direction].get(co.PACKS, 0)
                if flow.attr[direction].get(co.BYTES_DATA, 0) > 1000000000:
                    print("TCP", fname, conn_id, flow_id, direction, flow.attr[direction].get(co.BYTES_DATA, 0))
                nb_bytes_tcp += flow.attr[direction].get(co.BYTES_DATA, 0)
                nb_bytes_tcp_dir[direction] += flow.attr[direction].get(co.BYTES_DATA, 0)
                if port is not None:
                    nb_bytes_port[port] += flow.attr[direction].get(co.BYTES_DATA, 0)

print("TRACE 2")
print("NB CONNS", nb_conns)
print("NB PACKETS", nb_packets)
print("NB BYTES MPTCP", nb_bytes)
print("NB BYTES", nb_bytes_tcp)
print("NB BYTES DIR", nb_bytes_tcp_dir)
print("PORT CONN", nb_conns_port)
print("PORT BYTES", nb_bytes_port)


nb_conns = 0
nb_packets = 0
nb_bytes = 0
nb_bytes_tcp = 0
nb_bytes_tcp_dir = {co.C2S: 0, co.S2C: 0}
nb_conns_port = {}
nb_bytes_port = {}

for fname, conns in multiflow_connections.iteritems():
    for conn_id, conn in conns.iteritems():
        nb_flows = 0
        for flow_id, flow in conn.flows.iteritems():
            # Avoid taking into account connections that do not use at least two subflows
                if flow.attr[co.C2S].get(co.BYTES, 0) > 0 or flow.attr[co.S2C].get(co.BYTES, 0) > 0:
                    nb_flows += 1

        if nb_flows < 2:
            continue

        nb_conns += 1

        for direction in co.DIRECTIONS:
            if conn.attr[direction][co.BYTES_MPTCPTRACE] > 1000000000:
                print("MPTCP", fname, conn_id, direction, conn.attr[direction][co.BYTES_MPTCPTRACE])
            nb_bytes += conn.attr[direction][co.BYTES_MPTCPTRACE]
            for flow_id, flow in conn.flows.iteritems():
                nb_packets += flow.attr[direction].get(co.PACKS, 0)
                if flow.attr[direction].get(co.BYTES_DATA, 0) > 1000000000:
                    print("TCP", fname, conn_id, flow_id, direction, flow.attr[direction].get(co.BYTES_DATA, 0))
                nb_bytes_tcp += flow.attr[direction].get(co.BYTES_DATA, 0)
                nb_bytes_tcp_dir[direction] += flow.attr[direction].get(co.BYTES_DATA, 0)

print("TRACE 3")
print("NB CONNS", nb_conns)
print("NB PACKETS", nb_packets)
print("NB BYTES MPTCP", nb_bytes)
print("NB BYTES", nb_bytes_tcp)
print("NB BYTES DIR", nb_bytes_tcp_dir)
