#! /usr/bin/env python
"""
Load the model parameters from two JSON files

 BaseModel.json - static things that are not going to change based on the assumptions of the model
 [modelName] - more dynamic parameters that will change based on conservative/optimistic assumptions
 Also load in the number of events expected per year from the detector

 Return all of this as a nested dictionary
"""

import json
from collections import namedtuple

from utils import time_dependent_value, interpolate_value

SECONDS_PER_YEAR = 365.25 * 24 * 3600

DEFAULT_MODEL = ['BaseModel.json', 'RealisticModel.json']

class ResourceModel(object):
    """
    """

    def __init__(self, inputs, usedefault=True):

        if(usedefault):
            self.inputs = DEFAULT_MODEL

        if isinstance(inputs, basestring):
            self.inputs.append(inputs)
        elif isinstance(inputs, list):
            self.inputs.extend(inputs)

        self.configure()

        self.years = list(range(self.model['start_year'], self.model['end_year'] + 1))


    def configure(self):
        self.model = {}
        for conf in self.inputs:
            with open(conf, 'r') as conf_file:
                conf_data = json.load(conf_file)
                self.model.update(conf_data)

    def in_shutdown(self, year):
        """
        :param year: check if this year is in a shutdown period
        :return: boolean for in shutdown, integer for last year not in shutdown
        TODO: can we do things with a better and/or generic granularity
              for example we can have shutdowns = [[start, stop], ....]
              and the function could get an interval as input and return 
              the fraction of it which is in shutdown.
        """

        inShutdown = year in self.model['shutdown_years']

        while year in self.model['shutdown_years']:
           year -= 1

        return inShutdown, year


    def run_model(self, year, data_type='data'):
        """
        :param year: The year the model is being queried for
        :param data_type: The type of data (MC or data)
        :return: data events, in_shutdown
        """

        RunModel = namedtuple('RunModel', 'events, in_shutdown')

        inShutdown, lastRunningYear = self.in_shutdown(year)
        events = 0
        if not inShutdown:
            triggerRate, basisYear = time_dependent_value(year, self.model['trigger_rate'])
            liveFraction, basisYear = time_dependent_value(year, self.model['live_fraction'])
            events = SECONDS_PER_YEAR * liveFraction * triggerRate
        if data_type == 'mc':
            events *= self.model['mc_event_factor']
        return RunModel(events, inShutdown)


    def mc_event_model(self, year):
        """
        Given the various types of MC and their fraction compared to data in mc_evolution,
        for a the queried year, return the number of events needed to be simulated of each
        "MC year" in that calendar year.

        :param year: The year the model is being queried for
        :return: dictionary of {year1: events, year2: events} of types of events needed to be simualted
        """

        mcEvolution = self.model['mc_evolution']
        mcEvents = {}
        for mcType, ramp in mcEvolution.items():
            mcYear = int(mcType)

        # First figure out what to base the number of MC events
            currEvents = self.run_model(year).events
            if self.in_shutdown(year)[0]:
                lastYear = self.in_shutdown(year)[1]
                lastEvents = self.run_model(lastYear).events
            else:
                lastEvents = 0

            if mcYear > year:
                futureEvents = self.run_model(mcYear).events
            else:
                futureEvents = 0
            dataEvents = max(currEvents, lastEvents, futureEvents)

        # TODO: Replace this bit of code with interpolate_value from utils.py
            pastYear = 0
            futureYear = 3000
            mc_fraction = None
            for otherType in sorted(ramp):
                otherYear = int(otherType)
                if year == otherYear:  # We found the exact value
                    mc_fraction = ramp[otherType]
                    break
                if year - otherYear < year - pastYear and year > otherYear:
                    pastYear = otherYear
                if otherYear > year:
                   futureYear = otherYear
                   break

            if mc_fraction is None:  # We didn't get an exact value, interpolate between two values
                mc_fraction = (ramp[str(pastYear)] + (year - pastYear) *
                               (ramp[str(futureYear)] - ramp[str(pastYear)]) / (futureYear - pastYear))

            mcEvents[mcType] = mc_fraction * dataEvents

        return mcEvents

    def performance_by_year(self, year, tier, data_type=None, kind=None):
        """
        Return various performance metrics based on the year under consideration
        (allows for step and continuous variations)

        :param year: The year in which processing is done
        :param tier: Data tier produced
        :param data_type: data or mc
        :param kind: The year flavor of MC or data. May differ from actual running year
        
        :return:  tuple of cpu time (HS06 * s) and data size
        """

        # If we don't specify flavors, assume we are talking about the current year
        
        # TODO:  Big old hack for now because we don't have "kind" for data
        if not kind:
        # print year
           kind = str(year)
        if kind not in ['2016', '2026']:
            if int(kind) >= 2025:
                kind = '2026'
            else:
                kind = '2017'
        kind = str(kind)

        try:
            for modelYear in sorted(self.model['tier_sizes'][tier].keys()):
                if int(kind) >= int(modelYear):
                    sizePerEvent = self.model['tier_sizes'][tier][modelYear]
        except KeyError:  # Storage model does not know this tier
            sizePerEvent = None

        try:
            # Look up the normalized processing time
            for modelYear in sorted(self.model['cpu_time'][data_type][tier].keys()):
                if int(kind) >= int(modelYear):
                    cpuPerEvent = self.model['cpu_time'][data_type][tier][modelYear]

            # Apply the year by year correction
            improvement_factor = 1.0
            ramp = self.model['improvement_factors']['software_by_kind'][kind]
            for improve_year in range(int(self.model['start_year']), int(year) + 1):
                year_factor = interpolate_value(ramp, improve_year)
                improvement_factor *= year_factor

            cpuPerEvent = cpuPerEvent / improvement_factor
        except KeyError:  # CPU model does not know this tier
            cpuPerEvent = None

        return cpuPerEvent, sizePerEvent

