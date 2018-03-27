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
    modelNames = sys.argv[1].split(',')
em = EventsModel(modelNames)

plotEvents(em.get_events_matrix(), name='Produced by Kind.png', title='Events produced by type', columns=em.data_kinds, index=em.years)

