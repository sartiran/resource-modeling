#! /usr/bin/env python

from __future__ import division, print_function

import json
import sys
from DataModel import DataModel
from ModelOut import plotStorage, plotStorageWithCapacity

modelNames = None
if len(sys.argv) > 1:
    modelNames=[]
    for a in sys.argv[1:]:
        modelNames = modelNames+ a.split(',')
dm = DataModel(modelNames)

keyName=''
if modelNames is not None:
    for m in modelNames:
        keyName = keyName + '_' + m.split('/')[-1].split('.')[0]
plotMaxs = dm.model['plotMaximums']

minYearVal = max(0, dm.model['minYearToPlot'] - dm.years[0]) - 0.5 #pandas...

plotStorage(dm.produced_by_tier, name='ProducedbyTier' + keyName + '.png',
    title='Data produced by tier', columns=dm.tiers, index=dm.years, maximum=plotMaxs['ProducedbyTier'], minYear=minYearVal)

plotStorageWithCapacity(dm.tape_by_tier, name='TapebyTier' + keyName + '.png',
    title='Data on tape by tier', columns=dm.tier_columns, bars=dm.tiers + dm.static_tiers,
    maximum=plotMaxs['TapebyTier'], minYear=minYearVal)

plotStorageWithCapacity(dm.disk_by_tier, name='DiskbyTier' + keyName + '.png', 
    title='Data on disk by tier', columns=dm.tier_columns, bars=dm.tiers + dm.static_tiers,
    maximum=plotMaxs['DiskbyTier'], minYear=minYearVal)

plotStorageWithCapacity(dm.tape_by_year, name='TapebyYear' + keyName + '.png', 
    title='Data on tape by year produced', columns=dm.year_columns, bars=dm.years + ['Run1 & 2015'],
    maximum=plotMaxs['TapebyTier'], minYear=minYearVal)
plotStorageWithCapacity(dm.disk_by_year, name='DiskbyYear' + keyName + '.png',
    title='Data on disk by year produced', columns=dm.year_columns, bars=dm.years + ['Run1 & 2015'],
    maximum=plotMaxs['DiskbyYear'], minYear=minYearVal) 


# Dump out tuples of all the data on tape and disk in a given year
with open('disk_samples.json', 'w') as disk_usage, open('tape_samples.json', 'w') as tape_usage:
    json.dump(dm.disk_samples, disk_usage, sort_keys=True, indent=1)
    json.dump(dm.tape_samples, tape_usage, sort_keys=True, indent=1)


# disk printout
print('\nDisk by tier printout in PB\n')
header = "year"
for column in dm.tiers + dm.static_tiers:
    header += ";"
    header += str(column)
header +=";total;40%"
print(header)

for year in dm.years:
    line = str(year)
    total = 0
    for column in dm.tiers + dm.static_tiers:
        line += " " 
        line += '{:8.2f}'.format(dm.disk_by_tier[dm.years.index(year)][dm.tier_columns.index(column)])
        total += dm.disk_by_tier[dm.years.index(year)][dm.tier_columns.index(column)]
    line += '{:8.2f}'.format(total)
    line += '{:8.2f}'.format(total*0.4)
    print(line)


# tape printout
print('\nTape by tier printout in PB\n')
header = "year"
for column in dm.tiers + dm.static_tiers:
    header += ";"
    header += str(column)
header +=";total;40%"
print(header)

for year in dm.years:
    line = str(year)
    total = 0
    for column in dm.tiers + dm.static_tiers:
        line += " " 
        line += '{:8.2f}'.format(dm.tape_by_tier[dm.years.index(year)][dm.tier_columns.index(column)])
        total += dm.tape_by_tier[dm.years.index(year)][dm.tier_columns.index(column)]
    line += '{:8.2f}'.format(total)
    line += '{:8.2f}'.format(total*0.4)
    print(line)


# two new lines needed for 2018
us_fraction = dm.model['us_fraction_T1T2']
tape_fraction_T0 = dm.model['tape_fraction_T0']
disk_fraction_T0 = dm.model['disk_fraction_T0']

print("Year","\t"," US Disk","\t"," US Tape\tCopies")
for year in dm.years:
    totalDisk = 0
    totalTape = 0
    nCopies = dm.copies_on_disk[year]/float(dm.tiers_on_disk[year])
    for column in dm.tiers + dm.static_tiers:
        totalDisk += dm.disk_by_tier[dm.years.index(year)][dm.tier_columns.index(column)]
        totalTape += dm.tape_by_tier[dm.years.index(year)][dm.tier_columns.index(column)]

    print(year,'\t','{:8.2f}'.format(totalDisk * us_fraction * (1.0 - disk_fraction_T0)),'\t',
               '{:8.2f}'.format(totalTape * us_fraction * (1.0 - tape_fraction_T0)),'\t',
          '{:4.2f}'.format(nCopies),'\t',
          '{:4.2f}'.format(us_fraction*nCopies)
          )

'''
AOD:
current year: 1 version, fraction on disk, complete on tape
next year: 1 version, nothing on disk, complete on tape
next-to-next year: 0 versions

MINIAOD:
current year: 2 versions, one on disk, one on tape
next year: 1 version, fraction on disk, one version on tape
next-to-next year: 0 version

NANOAOD:
current year: 10 different versions (combination of multiple different NANOAODs and different versions), several replicas on disk, one on tape
next year: only the distinct set of different NANOAOD, no different version, several replicas on disk (less than current year), on distinct set on tape
next-to-next year: same as next year, but only one disk replica
next year:
'''

