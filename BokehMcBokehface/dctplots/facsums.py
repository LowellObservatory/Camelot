# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 7 May 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import datetime as dt

import numpy as np

from bokeh.models import DataTable, TableColumn
from bokeh.plotting import ColumnDataSource

from . import modulePlots as bplot


def assembleFacSumTCS(indat):
    """
    """
    # Common "now" time to compare everything against
    now = np.datetime64(dt.datetime.utcnow())

    # Now the tedious bit - reassemble the shredded parameters like RA/Dec/etc.
    #   Whomever designed the TCS XML...know that I'm not a fan of your work.
    #
    # 'deshred' will automatically take the last entry and return a
    #   non-annoying version with its timestamp for later display.
    #
    # First, get the last valid index in the q_tcssv dataframe and use that
    #   for all the TCS queries to make sure it's at least consistent
    tcsLastIdx = indat['q_tcssv'].cRA_h.last_valid_index()

    # CURRENT coords
    cRA = bplot.deshred([indat['q_tcssv'].cRA_h,
                         indat['q_tcssv'].cRA_m,
                         indat['q_tcssv'].cRA_s],
                        delim=":", lastIdx=tcsLastIdx,
                        name="cRA", comptime=now)
    cDec = bplot.deshred([indat['q_tcssv'].cDec_d,
                          indat['q_tcssv'].cDec_m,
                          indat['q_tcssv'].cDec_s],
                         delim=":", lastIdx=tcsLastIdx,
                         name="cDec", comptime=now)
    cEpoch = bplot.deshred([indat['q_tcssv'].cEqP,
                            indat['q_tcssv'].cEqY,
                            indat['q_tcssv'].cFrame],
                           delim="", lastIdx=tcsLastIdx,
                           name="cEpoch", comptime=now)
    # DEMAND coords
    dRA = bplot.deshred([indat['q_tcssv'].dRA_h,
                         indat['q_tcssv'].dRA_m,
                         indat['q_tcssv'].dRA_s],
                        delim=":", lastIdx=tcsLastIdx,
                        name="dRA", comptime=now)
    dDec = bplot.deshred([indat['q_tcssv'].dDec_d,
                          indat['q_tcssv'].dDec_m,
                          indat['q_tcssv'].dDec_s],
                         delim=":", lastIdx=tcsLastIdx,
                         name="dDec", comptime=now)
    dEpoch = bplot.deshred([indat['q_tcssv'].dEqP,
                            indat['q_tcssv'].dEqY,
                            indat['q_tcssv'].dFrame],
                           delim="", lastIdx=tcsLastIdx,
                           name="dEpoch", comptime=now)

    airmass = bplot.getLast(indat['q_tcssv'].Airmass,
                            lastIdx=tcsLastIdx, comptime=now)
    targname = bplot.getLast(indat['q_tcssv'].TargetName,
                             lastIdx=tcsLastIdx, comptime=now)
    guidemode = bplot.getLast(indat['q_tcssv'].GuideMode,
                              lastIdx=tcsLastIdx, comptime=now)
    sundist = bplot.getLast(indat['q_tcssv'].SunDistance,
                            lastIdx=tcsLastIdx, comptime=now)
    moondist = bplot.getLast(indat['q_tcssv'].MoonDistance,
                             lastIdx=tcsLastIdx, comptime=now)

    # Finally done! Now put it all into a list so it can be passed
    #   back a little easier and taken from there
    tableDat = [now, targname,
                cRA, cDec, cEpoch,
                dRA, dDec, dEpoch,
                airmass, guidemode,
                sundist, moondist]

    values = []
    labels = []
    for i, each in enumerate(tableDat):
        if i == 0:
            values.append(str(each))
            labels.append("LastUpdated")
        else:
            values.append(each.value)
            labels.append(each.label)

    mds = dict(labels=labels, values=values)
    cds = ColumnDataSource(mds)

    return cds


def assembleFacSumLPI(indat):
    """
    """
    # Common "now" time to compare everything against
    now = np.datetime64(dt.datetime.utcnow())

    # Now the tedious bit - reassemble the shredded parameters like RA/Dec/etc.
    #   Whomever designed the TCS XML...know that I'm not a fan of your work.
    #
    # 'deshred' will automatically take the last entry and return a
    #   non-annoying version with its timestamp for later display.
    #
    # First, get the last valid index in the q_tcssv dataframe and use that
    #   for all the TCS queries to make sure it's at least consistent
    tcsLastIdx = indat['q_tcssv'].cRA_h.last_valid_index()

    mirrorcov = bplot.getLast(indat['q_tcssv'].MirrorCover, lastIdx=tcsLastIdx,
                              comptime=now)

    # These are from other data sources, so get their values too
    domeshut = bplot.getLast(indat['q_tcslois'].DomeShutter, comptime=now)
    instcover = bplot.getLast(indat['q_cubeinstcover'].InstCover, comptime=now)

    cubeLastIdx = indat['q_cubefolds'].PortThru.last_valid_index()
    portT = bplot.getLast(indat['q_cubefolds'].PortThru, lastIdx=cubeLastIdx,
                          comptime=now)
    portA = bplot.getLast(indat['q_cubefolds'].PortA, lastIdx=cubeLastIdx,
                          comptime=now)
    portB = bplot.getLast(indat['q_cubefolds'].PortB, lastIdx=cubeLastIdx,
                          comptime=now)
    portC = bplot.getLast(indat['q_cubefolds'].PortC, lastIdx=cubeLastIdx,
                          comptime=now)
    portD = bplot.getLast(indat['q_cubefolds'].PortD, lastIdx=cubeLastIdx,
                          comptime=now)

    # Finally done! Now put it all into a list so it can be passed
    #   back a little easier and taken from there
    tableDat = [now,
                domeshut, mirrorcov, instcover,
                portT, portA, portB, portC, portD]

    values = []
    labels = []
    for i, each in enumerate(tableDat):
        if i == 0:
            values.append(str(each))
            labels.append("LastUpdated")
        elif each.label == "InstCover":
            # Special conversion to text for this one
            if each.value == 0:
                values.append("Closed")
            else:
                values.append("Open")
            labels.append(each.label)
        elif each.label.startswith("Port"):
            if each.value == 0:
                values.append("Inactive")
            else:
                values.append("Active")
            labels.append(each.label)
        else:
            values.append(each.value)
            labels.append(each.label)

    mds = dict(labels=labels, values=values)
    cds = ColumnDataSource(mds)

    return cds


def makeFacSumLPI(indat):
    """
    """
    #
    # TODO:
    #   I should *really* think about incorporating this into the other modules
    #
    abort = bplot.checkForEmptyData(indat)
    if abort is True:
        print("No data found! Aborting.")
        return None

    cds = assembleFacSumLPI(indat)
    print()

    cols = []
    for c in cds.column_names:
        print(c)
        col = TableColumn(field=c, title=c)
        cols.append(col)

    # Now actually construct the table
    dtab = DataTable(columns=cols, source=cds)

    return dtab


def makeFacSumTCS(indat):
    """
    """
    #
    # TODO:
    #   I should *really* think about incorporating this into the other modules
    #
    abort = bplot.checkForEmptyData(indat)
    if abort is True:
        print("No data found! Aborting.")
        return None

    cds = assembleFacSumTCS(indat)
    print()

    cols = []
    for c in cds.column_names:
        print(c)
        col = TableColumn(field=c, title=c)
        cols.append(col)

    # Now actually construct the table
    dtab = DataTable(columns=cols, source=cds)

    return dtab
