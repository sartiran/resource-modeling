#! /usr/bin/env python

from __future__ import division, print_function

from collections import defaultdict
from EventsModel import EventsModel

PETA = 1e15

class DataModel(EventsModel):

    def __init__(self, models,  usedefault=True):

        super(DataModel, self).__init__(models, usedefault)

        self.tiers = list(self.model['tier_sizes'].keys())
        self.static_tiers = list(sorted(set(self.model['static_disk'].keys() + self.model['static_tape'].keys())))

        self.capacity = {}
        self.capacity_model('disk')
        self.capacity_model('tape')
        self.disk_space_used()

    def capacity_model(self, type):
        
        # Set the initial points
        self.capacity[type] = {str(self.model['capacity_model'][type + '_year']): self.model['capacity_model'][type + '_start']}

        cm_year = self.model['capacity_model'][type + '_year']
        lifetime = self.model['capacity_model'][type + '_lifetime']
        cm_years = range(cm_year - lifetime + 1, cm_year + 1)

        cm_start = self.model['capacity_model'][type + '_start']


        # A bit of a kludge. Assume what we have now was bought and will be retired in equal chunks over its lifetime
	added = {str(_year): cm_start/lifetime for _year in cm_years}

        factor = self.model['improvement_factors'][type]

        deltas = self.model['capacity_model'][type + '_delta']

        #builf the model for future years
        for year in self.years:
            if str(year) not in self.capacity[type]:
                delta = 0  # Find the delta which can be time dependant
                for _y in sorted(deltas.keys()):
                    if int(year) >= int(_y):
                        lasty = int(_y)
                        delta = deltas[_y]

                added[str(year)] = delta * factor**(int(year) - int(lasty))
                # Retire disk/tape added N years ago or retire 0

                retired = added.get(str(int(year) - lifetime), 0)
                self.capacity[type][str(year)] = self.capacity[type][str(int(year) - 1)] + added[str(year)] - retired

    def disk_space_used(self):
        # Disk space used
        data_produced = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        data_on_disk = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        data_on_tape = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
        self.disk_samples = defaultdict(list)
        self.tape_samples = defaultdict(list)

        disk_copies = {}
        tape_copies = {}

        disk_scale_factor_by_year = {"Run1 & 2015" : {"2000": 1.0, "2050" : 1.0} }
        tape_scale_factor_by_year = {"Run1 & 2015" : {"2000": 1.0, "2050" : 1.0} }
       
        for tier in self.tiers:
            v = self.model['storage_model']['versions'][tier]
            dr = self.model['storage_model']['disk_replicas'][tier]
            tr = self.model['storage_model']['tape_replicas'][tier]
            vr = zip(v, dr)
            disk_copies[tier] = [versions * replicas for versions, replicas in vr]
            tape_copies[tier] = [versions * replicas for versions, replicas in zip(v, tr)]

            if not tape_copies[tier]: tape_copies[tier] = [0, 0, 0]
            
            #try:
            disk_scale_factor_by_year[tier] = self.model['storage_model']['disk_scaling'].get(tier,None)
            tape_scale_factor_by_year[tier] = self.model['storage_model']['tape_scaling'].get(tier,None)
            if disk_scale_factor_by_year[tier] is None: disk_scale_factor_by_year[tier]={"2000": 1.0, "2050" : 1.0}
            if tape_scale_factor_by_year[tier] is None: tape_scale_factor_by_year[tier]={"2000": 1.0, "2050" : 1.0}
            #except:
            #    disk_scale_factor_by_year[tier]={"2000": 1.0, "2050" : 1.0}
            #    tape_scale_factor_by_year[tier]={"2000": 1.0, "2050" : 1.0}

        # Loop over years to determine how much is produced without versions or replicas
        for year in self.years:
            for kind, events in self.events_by_year[year].items():

                # this is ugly should probably reorganize things in a better way
                if kind == 'Data': 
                    data_type = 'data'
                    not_data_type = 'mc' 
                else: 
                    data_type = 'mc'
                    not_data_type = 'data'

                if data_type == 'mc': 
                    mc_kind = kind.split(' ')[0] 
                else: 
                    mc_kind = None

                for tier in self.tiers:
                    if tier not in self.model[not_data_type + '_only_tiers']:
                       dummycpu, size = self.performance_by_year(year, tier, data_type=data_type, kind=mc_kind)
                       data_produced[year][data_type][tier] += size * events
        
        self.produced_by_tier = [[0 for _i in range(len(self.tiers))] for _j in self.years]
        for year, data_dict in data_produced.items():
            for data_type, tier_dict in data_dict.items():
                for tier, size in tier_dict.items():
                     self.produced_by_tier[self.years.index(year)][self.tiers.index(tier)] += size / PETA

        # Initialize a matrix with tiers and years
        self.year_columns = self.years + ['Capacity', 'Year', 'Run1 & 2015']

        # Initialize a matrix with years and years
        self.disk_by_year = [[0 for _i in self.year_columns] for _j in self.years]
        self.tape_by_year = [[0 for _i in self.year_columns] for _j in self.years]

        #Simple factors inspired by spreadsheet for how "efficiently" we use disk and tape
        #two components - 1 a simple "filling" factor - eg, DDM fills X% of the disk
        #                 2 buffer space at the Tier1s (tier-2s are handled below) 
        dff = self.model['disk_fill_factor']
        t1df = self.model['tier1_disk_fraction']
        t1dbf = self.model['tier1_disk_buffer_fraction']
        self.disk_fill_factor = (1.0 / dff) * ( t1df * (1.0 + t1dbf) +  (1.0 - t1df))
        self.tape_fill_factor = 1.0 / self.model['tape_fill_factor']

        # Loop over years to determine how much is saved
        self.copies_on_disk={}
        self.tiers_on_disk={}
        for year in self.years:
           # Add static (or nearly) data
            for tier, spaces in self.model['static_disk'].items():
                size, produced_year = self.time_dependent_value(year=year, values=spaces)
                if produced_year < self.years[0]: produced_year = self.years[0]
                data_on_disk[year]['Other'][tier] += size
                self.disk_samples[year].append([produced_year, 'Other', tier, size])
                self.disk_by_year[self.years.index(year)][self.years.index(produced_year)] += size / PETA
            for tier, spaces in self.model['static_tape'].items():
                size, produced_year = self.time_dependent_value(year=year, values=spaces)
                if produced_year < self.years[0]: produced_year = self.years[0]
                data_on_tape[year]['Other'][tier] += size
                self.tape_samples[year].append([produced_year, 'Other', tier, size])
                self.tape_by_year[self.years.index(year)][self.years.index(produced_year)] += size / PETA


            # Figure out data from this year and previous
            for produced_year, data_dict in data_produced.items():
                for data_type, tier_dict in data_dict.items():
                    for tier, size in tier_dict.items():
                        scale_disk,ty = self.time_dependent_value(year=produced_year, values=disk_scale_factor_by_year[tier])
                        scale_tape,ty = self.time_dependent_value(year=produced_year, values=tape_scale_factor_by_year[tier])
                        disk_copies_by_delta = disk_copies[tier]
                        tape_copies_by_delta = tape_copies[tier]
                        print("DBP1", year, tier, tape_copies_by_delta)
                        if int(produced_year) <= int(year):  # Can't save data for future year
                            if int(produced_year) == int(year):
                                if tier != "USER" and tier != "GENSIM" and tier!="RAW":
                                    self.tiers_on_disk[year] = self.tiers_on_disk.get(year,0) + 1
                                    self.copies_on_disk[year] = self.copies_on_disk.get(year,0) + disk_copies_by_delta[0] * scale_disk 
                            if year - produced_year >= len(disk_copies_by_delta):
                                rev_on_disk = disk_copies_by_delta[-1]  # Revisions = versions * copies
                                rev_on_tape = tape_copies_by_delta[-1]  # Assume what we have for the last year is good for out years
                            elif self.in_shutdown(year):
                                in_shutdown, last_running_year = self.in_shutdown(year)
                                rev_on_disk = disk_copies_by_delta[last_running_year - produced_year]
                                rev_on_tape = tape_copies_by_delta[last_running_year - produced_year]
                            else:
                                rev_on_disk = disk_copies_by_delta[year - produced_year]
                                rev_on_tape = tape_copies_by_delta[year - produced_year]
                            if size and rev_on_disk:
                                contr = size * rev_on_disk * self.disk_fill_factor * scale_disk
                                data_on_disk[year][data_type][tier] += contr
                                self.disk_samples[year].append([produced_year, data_type, tier, contr, rev_on_disk])
                                self.disk_by_year[self.years.index(year)][self.years.index(produced_year)] += contr / PETA
                            if size and rev_on_tape:
                                #contr = size * rev_on_tape * self.tape_fill_factor * scale_tape
                                contr = size * rev_on_tape * scale_tape
                                data_on_tape[year][data_type][tier] += contr
				#Bug ?: add the tape fill factor only in the tape_samples table
                                self.tape_samples[year].append([produced_year, data_type, tier, contr * self.tape_fill_factor, rev_on_tape])
                                self.tape_by_year[self.years.index(year)][self.years.index(produced_year)] += contr * self.tape_fill_factor / PETA


            # Add capacity numbers
            self.disk_by_year[self.years.index(year)][self.year_columns.index('Capacity')] = self.capacity['disk'][str(year)] / PETA
            self.disk_by_year[self.years.index(year)][self.year_columns.index('Year')] = str(year)
            self.tape_by_year[self.years.index(year)][self.year_columns.index('Capacity')] = self.capacity['tape'][str(year)] / PETA
            self.tape_by_year[self.years.index(year)][self.year_columns.index('Year')] = str(year)
            #print("DBP1", year, self.tape_samples[year])
        # Initialize a matrix with tiers and years
        # Add capacity, years, and fake tiers as columns for the data frame
        self.tier_columns = self.tiers + ['Capacity', 'Year'] + self.static_tiers

        self.disk_by_tier = [[0 for _i in range(len(self.tier_columns))] for _j in self.years]
        self.tape_by_tier = [[0 for _i in range(len(self.tier_columns))] for _j in self.years]
        for year, data_dict in data_on_disk.items():
            for data_type, tier_dict in data_dict.items():
                for tier, size in tier_dict.items():
                    self.disk_by_tier[self.years.index(year)][self.tier_columns.index(tier)] += size / PETA
            self.disk_by_tier[self.years.index(year)][self.tier_columns.index('Capacity')] = self.capacity['disk'][str(year)] / PETA
            self.disk_by_tier[self.years.index(year)][self.tier_columns.index('Year')] = str(year)
        for year, data_dict in data_on_tape.items():
            for data_type, tier_dict in data_dict.items():
                for tier, size in tier_dict.items():
                    self.tape_by_tier[self.years.index(year)][self.tier_columns.index(tier)] += size / PETA
            self.tape_by_tier[self.years.index(year)][self.tier_columns.index('Capacity')] = self.capacity['tape'][str(year)] / PETA
            self.tape_by_tier[self.years.index(year)][self.tier_columns.index('Year')] = str(year)

        if 'legacyInfoDict' in self.model:
            for year,val in self.model['legacyInfoDict'].items():
                self.disk_by_tier[self.years.index(int(year))][self.tier_columns.index('Run1 & 2015')] = val
                self.disk_by_year[self.years.index(int(year))][self.year_columns.index('Run1 & 2015')] = val
        else:
            if 2016 in self.years:
                self.disk_by_tier[self.years.index(2016)][self.tier_columns.index('Run1 & 2015')] = 25
            self.disk_by_tier[self.years.index(2017)][self.tier_columns.index('Run1 & 2015')] = 25
            self.disk_by_tier[self.years.index(2018)][self.tier_columns.index('Run1 & 2015')] = 10
            self.disk_by_tier[self.years.index(2019)][self.tier_columns.index('Run1 & 2015')] = 5
            self.disk_by_tier[self.years.index(2020)][self.tier_columns.index('Run1 & 2015')] = 0
            if 2016 in self.years:
                self.disk_by_year[self.years.index(2016)][self.year_columns.index('Run1 & 2015')] = 25
            self.disk_by_year[self.years.index(2017)][self.year_columns.index('Run1 & 2015')] = 25
            self.disk_by_year[self.years.index(2018)][self.year_columns.index('Run1 & 2015')] = 10
            self.disk_by_year[self.years.index(2019)][self.year_columns.index('Run1 & 2015')] = 5
            self.disk_by_year[self.years.index(2020)][self.year_columns.index('Run1 & 2015')] = 0

