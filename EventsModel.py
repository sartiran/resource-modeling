#! /usr/bin/env python

from __future__ import division, print_function

import sys

from ResourceModel import ResourceModel, SECONDS_PER_YEAR, GIGA
from collections import namedtuple

class EventsModel(ResourceModel):
    """
    Class for getting the foreseen number of events per year and per type
    Gets the model (dictionary) as input parameter and uses the functions

    """
    def __init__(self, models,  usedefault=True):

        super(EventsModel, self).__init__(models, usedefault)

        self.define_data_kinds()

        self.events_by_year = {year: {} for year in self.years}
        self.get_data_events()
        self.get_mc_events()

    def define_data_kinds(self):
        
        # Just an hack. But I'd rather get the distinct set of keys in mc_evolution
        self.data_kinds = [key + ' MC' for key in self.model['mc_evolution']['2017'].keys()]
        self.data_kinds.append('Data')

    def run_model(self, year, data_type='data'):
        """
        :param year: the year the model is being queried for
        :param data_type: the type of data (MC or data)
        :return: data events, in_shutdown

        inputs looked up from the model dictonary:
          - trigger rate
          - live fraction
          - is it a shutdown year
        if it is a shutdown year returns 0 otherwise the n. of events
        calculated by the trigger rate and the live fraction.

        """

        run_model = namedtuple('RunModel', 'events, in_shutdown')

        in_shutdown, last_running_year = self.in_shutdown(year)
        events = 0
        if not in_shutdown:
            trigger_rate, basis_year = self.time_dependent_value(year, self.model['trigger_rate'])
            live_fraction, basis_year = self.time_dependent_value(year, self.model['live_fraction'])
            events = SECONDS_PER_YEAR * live_fraction * trigger_rate
#        if data_type == 'mc':
#            events *= self.model['mc_event_factor']
        return run_model(events, in_shutdown)


    def mc_event_model(self, year):
        """
        Given the various types of MC and their fraction compared to data in mc_evolution,
        for a the queried year, return the number of events needed to be simulated of each
        "MC year" in that calendar year.

        :param year: The year the model is being queried for
        :return: dictionary of {year1: events, year2: events} of types of events needed to be simualted

        inputs from model: 
          - 'mc_evolution': a dictionary with for each year the fraction of events for each "MC year"

        warning: this requies that the data events are already there
        """

        curr_events = self.events_by_year[year]['Data']

        mc_evolution = self.model['mc_evolution']
        mc_events = {}
        for mc_type, ramp in mc_evolution.items():
            mc_year = int(mc_type)

        # First figure out what to base the number of MC events
            if self.in_shutdown(year)[0]:
                last_year = self.in_shutdown(year)[1]
                last_events = self.events_by_year[last_year]['Data']
            else:
                last_events = 0

            if mc_year > year:
                future_events = self.events_by_year[mc_year]['Data']
            else:
                future_events = 0
            data_events = max(curr_events, last_events, future_events)

            mc_fraction = self.interpolate_value(ramp, year)

            mc_events[mc_type] = mc_fraction * data_events

        return mc_events

    def get_data_events(self):
        for year in self.years:
            self.events_by_year[year] = {k:0 for k in self.data_kinds}
            self.events_by_year[year]['Data'] = self.run_model(year).events

    def get_mc_events(self):
        for year in self.years:
           for mc_kind, count in self.mc_event_model(year).items():
               self.events_by_year[year][mc_kind + ' MC'] = count
  
    def get_events_matrix(self):
        return [[ self.events_by_year[y][k]/GIGA for k in self.data_kinds] for y in self.years]

