#! /usr/bin/env python

from __future__ import division, print_function

import json
import sys
from DataModel import DataModel
from ModelOut import plotStorage, plotStorageWithCapacity

modelNames = None
if len(sys.argv) > 1:
    modelNames = sys.argv[1].split(',')
dm = DataModel(modelNames)

plotStorage(dm.produced_by_tier, name='Produced by Tier.png', title='Data produced by tier', columns=dm.tiers, index=dm.years)

plotStorageWithCapacity(dm.tape_by_tier, name='Tape by Tier.png', title='Data on tape by tier', columns=dm.tier_columns,
                        bars=dm.tiers + dm.static_tiers)
plotStorageWithCapacity(dm.disk_by_tier, name='Disk by Tier.png', title='Data on disk by tier', columns=dm.tier_columns,
                        bars=dm.tiers + dm.static_tiers)
plotStorageWithCapacity(dm.tape_by_year, name='Tape by Year.png', title='Data on tape by year produced', columns=dm.year_columns,
                        bars=dm.years + ['Run1 & 2'])
plotStorageWithCapacity(dm.disk_by_year, name='Disk by Year.png', title='Data on disk by year produced', columns=dm.year_columns,
                        bars=dm.years + ['Run1 & 2'])

# Dump out tuples of all the data on tape and disk in a given year
with open('dm.disk_samples.json', 'w') as disk_usage, open('dm.tape_samples.json', 'w') as tape_usage:
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

'''
AOD:
current year: 1 version, fraction on disk, complete on tape
next year: 1 version, nothing on disk, complete on tape
next-to-next year: 0 versions

MINIAOD:
current year: 2 versions, one on disk, one on tape
next year: 1 version, fraction on disk, one version on tape
next-to-next year: 0 version

MICROAOD:
current year: 10 different versions (combination of multiple different MICROAODs and different versions), several replicas on disk, one on tape
next year: only the distinct set of different MICROAOD, no different version, several replicas on disk (less than current year), on distinct set on tape
next-to-next year: same as next year, but only one disk replica
next year:
'''

