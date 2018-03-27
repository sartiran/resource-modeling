#! /usr/bin/env python
"""
Load the model parameters from two JSON files

 BaseModel.json - static things that are not going to change based on the assumptions of the model
 [modelName] - more dynamic parameters that will change based on conservative/optimistic assumptions
 Also load in the number of events expected per year from the detector

 Return all of this as a nested dictionary
"""

from __future__ import absolute_import, division, print_function
import json
from collections import namedtuple

SECONDS_PER_YEAR = 365.25 * 24 * 3600
GIGA = 1e9

DEFAULT_MODEL = ['BaseModel.json', 'RealisticModel.json']

class ResourceModel(object):
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
                year_factor = self.interpolate_value(ramp, improve_year)
                improvement_factor *= year_factor

            cpuPerEvent = cpuPerEvent / improvement_factor
        except KeyError:  # CPU model does not know this tier
            cpuPerEvent = None

        return cpuPerEvent, sizePerEvent

    @staticmethod
    def time_dependent_value(year=2016, values=None):
        """
        :param year: Year for which we are looking for parameter
        :param values: dictionary in the form {"2016": 1.0, "2017": 2.0}
        :return: determined value, first year for which its valid (for calculating improvements from a known point)
        """

        values = values or {}
        value = None
        last_year = None
        for delta_year in sorted(values.keys()):
            if int(year) >= int(delta_year):
                last_year = int(delta_year)
                value = values[delta_year]

        return value, last_year

    @staticmethod
    def interpolate_value(ramp, year):
        """
        Takes a dictionary of the form: {"2016": x, "2020": y, ...}

        and returns x for year=2016, y for year=2020, and an interpolated value for 2017, 2018, 2019
        """

        past_year = 0
        future_year = 3000
        value = None
        for other_type in sorted(ramp):
            other_year = int(other_type)
            if year == other_year:  # We found the exact value
                value = ramp[other_type]
                break
            if year - other_year < year - past_year and year > other_year:
                past_year = other_year
            if other_year > year:
                future_year = other_year
                break

        if value is None:  # We didn't get an exact value, interpolate between two values
            value = (ramp[str(past_year)] + (year - past_year) *
                     (ramp[str(future_year)] - ramp[str(past_year)]) / (future_year - past_year))

        return value


