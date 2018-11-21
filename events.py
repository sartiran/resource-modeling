#! /usr/bin/env python

"""
Usage: ./events.py config1.json,config2.json,...,configN.json

Determine the disk and tape models by running under various configuration changes. BaseModel.json and RealisticModel.json
provide defaults and configN.json overrides values in those configs or earlier ones in the list
"""

from __future__ import division, print_function

import sys

from EventsModel import EventsModel
from ModelOut import plotEvents

modelNames = None
if len(sys.argv) > 1:
    modelNames=[]
    for a in sys.argv[1:]:
        modelNames = modelNames + a.split(',')
em = EventsModel(modelNames)
#print('DBP3', modelNames)

matrix = em.get_events_matrix()

print('Year', em.data_kinds)
for year in em.years:
    print(year, matrix[em.years.index(year)])

#print('DBP2', em.events_by_year)


plotEvents(matrix, name='Produced by Kind.png', title='Events produced by type', columns=em.data_kinds, index=em.years)

