#! /usr/bin/env python

"""
Usage: ./cpu.py config1.json,config2.json,...,configN.json

Determine the disk and tape models by running under various configuration changes. BaseModel.json and RealisticModel.json
provide defaults and configN.json overrides values in those configs or earlier ones in the list
"""

from __future__ import division, print_function

import sys

from configure import ResourceModel
from plotting import plotEvents

GIGA = 1e9

class EventsModel(ResourceModel):

    def __init__(self, models,  usedefault=True):

        super(EventsModel, self).__init__(models, usedefault)

        self.define_data_kinds()
        self.get_events_by_year()

    def define_data_kinds(self):

        # Call the data model with a random year to get the fields
        self.data_kinds = [key + ' MC' for key in self.mc_event_model(2020).keys()]
        self.data_kinds.append('Data')

    def get_events_by_year(self):
        
        eby = [[0 for _i in range(len(self.data_kinds))] for _j in self.years]

        for year in self.years:
            eby[self.years.index(year)][self.data_kinds.index('Data')] = self.run_model(year).events / GIGA
            mc_evts = self.mc_event_model(year)
            for mc_kind, count in mc_evts.items():
                eby[self.years.index(year)][self.data_kinds.index(mc_kind + ' MC')] = count / GIGA
        
        self.events_by_year = eby

modelNames = None
if len(sys.argv) > 1:
    modelNames = sys.argv[1].split(',')
em = EventsModel(modelNames)

plotEvents(em.events_by_year, name='Produced by Kind.png', title='Events produced by type', columns=em.data_kinds, index=em.years)

