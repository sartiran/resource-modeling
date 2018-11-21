#! /usr/bin/env python

"""
Usage: ./cpu.py config1.json,config2.json,...,configN.json

Determine the CPU model by running under various configuration changes. BaseModel.json and RealisticModel.json
provide defaults and configN.json overrides values in those configs or earlier ones in the list
"""


from __future__ import division

from EventsModel import EventsModel

# Basic parameters
kilo = 1000
mega = 1000 * kilo
giga = 1000 * mega
tera = 1000 * giga
peta = 1000 * tera
seconds_per_year = 86400 * 365
seconds_per_month = 86400 * 30
running_time = 7.8E06

class CPUModel(EventsModel):

    def __init__(self, models,  usedefault=True):

        super(CPUModel, self).__init__(models, usedefault)

        self.get_performances()
        self.prompt_reco()
        self.re_reco()
        self.mc()
        self.analysis()
        self.shutdowns()
        self.get_cpu_capacity_simple()
        self.get_cpu_capacity()
        self.get_totals()
        self.get_fractions()

    def get_performances(self):
        """
        Get the performance year by year 
        which includes the software improvement factor
        """

        self.cpu_efficiency = self.model['cpu_efficiency']

        self.reco_time = {year: self.performance_by_year( year, 'RECO', 
                                                          data_type='data')[0] for year in self.years}

        self.lhc_sim_time = {year: self.performance_by_year( year, 'GENSIM',
                                                           data_type='mc', kind='2017')[0] +
                                   self.performance_by_year( year, 'DIGI',
                                                           data_type='mc', kind='2017')[0] +
                                   self.performance_by_year( year, 'RECO',
                                                           data_type='mc', kind='2017')[0] for year in self.years}

        self.hllhc_sim_time = {year: self.performance_by_year( year, 'GENSIM',
                                                             data_type='mc', kind='2026')[0] +
                                     self.performance_by_year( year, 'DIGI',
                                                             data_type='mc', kind='2026')[0] +
                                   self.performance_by_year( year, 'RECO',
                                                             data_type='mc', kind='2026')[0] for year in self.years}
    def prompt_reco(self):
        """
        CPU time requirement calculations, in HS06 * s
        Take the running time and event rate from the model


        """

        #data_events = {i: rm.run_model(i, data_type='data').events for i in YEARS}

        self.data_cpu_time = {i : self.events_by_year[i]['Data'] * self.reco_time[i] / self.cpu_efficiency for i in self.years}

        # The data need to be reconstructed about as quickly as we record them.  In
        # addition, we need to factor in express, repacking, AlCa, CAF
        # functionality and skimming.  Presumably these all scale like the data.
        # Per the latest CRSG document, these total to 123 kHS06 compared to 240
        # kHS016 for the prompt reconstruction, which we can round to 50%, so
        # multiply by 50%.  (Ignoring the 10 kHS06 needed for VO boxes, which
        # won't scale up and is also pretty small.)

        self.data_cpu_required = {i : (self.model['t0_factor'] * self.data_cpu_time[i] / running_time)
                         for i in self.years}

        # Also keep using the _time variables to sum up the total HS06 * s needed,
        # which frees us from assumptions on time needed to complete the work.

        self.data_cpu_time = {i : self.model['t0_factor'] * self.data_cpu_time[i] for i in self.years}

    def re_reco(self):
        """
        In-year reprocessing model: assume we will re-reco 25% of the data each
        year, but we want to complete it in one month.  We also re-reco 25% of
        the previous year's data (assumed to be the same number of events as this
        year) but we want to do that in three months.
        But the total time needed is the sum of both activities.
        """

        self.rereco_cpu_required = {i : (1.0/ self.cpu_efficiency) * max(0.25 * self.events_by_year[i]['Data'] * 
                                self.reco_time[i]/seconds_per_month,
                                self.events_by_year[i]['Data'] * self.reco_time[i] / (3 * seconds_per_month))
                         for i in self.years}
    
        self.rereco_cpu_time = {i : (1.25 * self.events_by_year[i]['Data'] * self.reco_time[i]) for i in self.years}
 
    def mc(self):
        """
        The corresponding MC, on the other hand, can be reconstructed over an
        entire year.  We can use this to calculate the HS06 needed to do those
        tasks.

        Unless it is a year with new detectors in, in which case we will have
        less time to make MC (say half as much).  Only applies to the current
        era, i.e. no need to compress HL-LHC MC when we are still in LHC era.
        """
        lhc_mc_events = {i: self.events_by_year[i]['2017 MC'] for i in self.years}
        hllhc_mc_events = {i: self.events_by_year[i]['2026 MC'] for i in self.years}

        #print('DBP2', 'Year', self.data_kinds)
        #for year in self.years:
        #    print('DBP2', year, self.events_by_year[self.years.index(year)]['2017 MC'], self.events_by_year[self.years.index(year)]['2026 MC'])

        self.lhc_mc_cpu_time = {i : lhc_mc_events[i] * self.lhc_sim_time[i] / self.cpu_efficiency for i in self.years}
        self.hllhc_mc_cpu_time = {i : hllhc_mc_events[i] * self.hllhc_sim_time[i] / self.cpu_efficiency for i in self.years}

        #for year in self.years:
        #    print("DBP: ", year, hllhc_mc_events[year], self.hllhc_sim_time[year], self.cpu_efficiency, self.hllhc_mc_cpu_time[year])

        self.lhc_mc_cpu_required = {i : self.lhc_mc_cpu_time[i] / seconds_per_year for i in self.years}
        self.hllhc_mc_cpu_required = {i : self.hllhc_mc_cpu_time[i] / seconds_per_year for i in self.years}

        for i in self.years:
            if (i in self.model['new_detector_years']):
                if i < 2026:
                    self.lhc_mc_cpu_required[i] *= 2
                else:
                    self.hllhc_mc_cpu_required[i] *= 2

    def analysis(self):
        if 'AnalysisSet' in self.model:
            self.analysis_new()
        else:
            self.analysis_old()

    def analysis_new(self):
        self.analysis_method = 'new'
        lhc_mc_events = {i: self.events_by_year[i]['2017 MC'] for i in self.years}
        hllhc_mc_events = {i: self.events_by_year[i]['2026 MC'] for i in self.years}
        data_events = {i: self.events_by_year[i]['Data'] for i in self.years}
            
        self.analysis_cpu_time={}
        for i in self.years:
            data_reads,ty = self.time_dependent_value(year=i, values=self.model['AnalysisReadsPerYearData'])
            mc_reads,ty = self.time_dependent_value(year=i, values=self.model['AnalysisReadsPerYearMC'])
            self.analysis_cpu_time[i]=0.
            for j in self.model['AnalysisSet'][str(i)]:
                # 2.25 is 1 for prompt + 1.25 of rereco
                self.analysis_cpu_time[i] += self.model['AnalysisCPUPerEvent'] * data_reads * 2.25 * data_events[j]
                self.analysis_cpu_time[i] += self.model['AnalysisCPUPerEvent'] * mc_reads * lhc_mc_events[j]
            if i > 2025:
                for j in self.model['AnalysisSet'][str(i)]:
                    self.analysis_cpu_time[i] += self.model['AnalysisCPUPerEvent'] * mc_reads * hllhc_mc_events[j]
            else:
                self.analysis_cpu_time[i] += self.model['AnalysisCPUPerEvent'] * mc_reads * hllhc_mc_events[i]
            self.analysis_cpu_time[i] = self.analysis_cpu_time[i]  / self.cpu_efficiency

        self.analysis_cpu_required={}

        # allow a component that scales with reconstruction
        analysis_scaled_by_reco = self.model['AnalysisCPUScaledByReco']
        if analysis_scaled_by_reco > 0:
            for i in self.years:
                self.analysis_cpu_time[i] += analysis_scaled_by_reco * (self.lhc_mc_cpu_time[i] + self.hllhc_mc_cpu_time[i] +
                                                            self.data_cpu_time[i] +  self.rereco_cpu_time[i])
        #now sum up everything
        for i in self.years:
            self.analysis_cpu_required[i] = self.analysis_cpu_time[i] / seconds_per_year
        

    def analysis_old(self):
        """
        Analysis!  Following something like the 2018 resource request, we make this
        75% of everything else (for a moment).

        But do something a little funkier for the time up to HL-LHC.  We are
        accumulating data, so analysis should keep taking longer.  Assume 2018 is
        "right".  In 2019 we will analyze 2018 data in addition to 2016 and 2017,
        so make 2019 1/3 bigger.  Keep the same amount through the shutdown when
        we don't accumulate data.  Then after the shutdown we keep adding in data
        years that are the same size as the previous ones, and then keep that
        flat until we ramp up HL-LHC studies in 2025 and we revert back to the
        75% model.  Implemented here as a complete kludge.  Note that by kludging
        this way we don't absorb the software improvement factors...but that's
        OK, the analysis is I/O bound anyway and doesn't benefit from such
        improvements.

        More kludging: assume analysis takes place all year to calculate the HS06
        required for the above analysis CPU time.  Eric will hate this, I do too,
        we should fix it up later.
        """
        self.analysis_method = 'old'
        self.analysis_cpu_required = {i : 0.75 *
                        (self.lhc_mc_cpu_required[i] + self.hllhc_mc_cpu_required[i] +
                        self.data_cpu_required[i] + self.rereco_cpu_required[i])
                             for i in self.years}

        self.analysis_cpu_time = {i : 0.75 * (self.data_cpu_time[i] + self.rereco_cpu_time[i] +
                         self.lhc_mc_cpu_time[i] + self.hllhc_mc_cpu_time[i])
                         for i in self.years}

        self.analysis_cpu_time[2019] = (4/3) * self.analysis_cpu_time[2018]
        self.analysis_cpu_time[2020] = self.analysis_cpu_time[2019]
        self.analysis_cpu_time[2021] = self.analysis_cpu_time[2019]
        self.analysis_cpu_time[2022] = (5/4)* self.analysis_cpu_time[2021]
        self.analysis_cpu_time[2023] = (6/5)* self.analysis_cpu_time[2022]
        self.analysis_cpu_time[2024] = (7/6)* self.analysis_cpu_time[2023]

        for i in self.years:
            if (i >= 2019 and i < 2025):
                self.analysis_cpu_required[i] = self.analysis_cpu_time[i]/seconds_per_year

    def shutdowns(self):  
        """
        If in the first year of a shutdown, need to reconstruct the previous
        three years of data, but you have all year to do it.  No need for all the
        ancillary stuff.  We need to do the MC also...assume similarly that we
        have three times as many events as we had the previous year.
        """
        mc_events = {i:0 for i in self.years}
        date_rereco_two_years = self.model['first_year_to_spread_rereco_over_two_years']

        for i in self.years:
           shutdown_this_year, dummy = self.in_shutdown(i)
           shutdown_last_year, dummy = self.in_shutdown(i - 1)
           shutdown_next_year, dummy = self.in_shutdown(i + 1)
           if (shutdown_this_year and not(shutdown_last_year)):
               data_events = 3 * self.events_by_year[i - 1]['Data']
               if i >= date_rereco_two_years:
                   data_events = 0.5 * data_events
               self.rereco_cpu_time[i] = data_events * self.reco_time[i] / self.cpu_efficiency
               self.rereco_cpu_required[i] = self.rereco_cpu_time[i] / seconds_per_year

               if i >=date_rereco_two_years:
                   if (i + 1 in self.events_by_year):
                       if shutdown_next_year:
                           self.events_by_year[i + 1]['Data'] = 0
                           self.rereco_cpu_time[i + 1] = 0                   
                           self.rereco_cpu_required[i + 1] = 0
                       self.events_by_year[i + 1]['Data'] += data_events
                       self.rereco_cpu_time[i + 1] += self.rereco_cpu_time[i]
                       self.rereco_cpu_required[i + 1] += self.rereco_cpu_required[i]
               
               if i < 2025:
                   mc_events[i] = 3 * self.events_by_year[i - 1]['2017 MC']
                   if i >= date_rereco_two_years:
                       mc_events[i] = 0.5 * mc_events[i]
                   self.lhc_mc_cpu_time[i] = mc_events[i] * self.lhc_sim_time[i] / self.cpu_efficiency
                   self.lhc_mc_cpu_required[i] = self.lhc_mc_cpu_time[i] / seconds_per_year
                   
                   if i >= date_rereco_two_years:
                       if i + 1 in self.events_by_year:
                           if shutdown_next_year:
                               self.events_by_year[i + 1]['2017 MC'] = 0
                               self.lhc_mc_cpu_time[i + 1] = 0
                               self.lhc_mc_cpu_required[i + 1] = 0
                           self.events_by_year[i + 1]['2017 MC'] += mc_events[i]
                           self.lhc_mc_cpu_time[i + 1] += self.lhc_mc_cpu_time[i]
                           #BUG!: self.lhc_mc_cpu_required[i + 1] += self.lhc_mc_cpu_required[i]
                           self.lhc_mc_cpu_required[i] += self.lhc_mc_cpu_required[i]
               else:
                   mc_events[i] = 3 * self.events_by_year[i - 1]['2026 MC']
                   if i >= date_rereco_two_years:
                       mc_events[i]=0.5 * mc_events[i]

                   self.hllhc_mc_cpu_time[i] = mc_events[i] * self.hllhc_sim_time[i] / self.cpu_efficiency
                   self.hllhc_mc_cpu_required[i] = self.hllhc_mc_cpu_time[i] / seconds_per_year
                   if i >= date_rereco_two_years:
                       if i + 1 in self.events_by_year:
                           if shutdown_next_year:
                               self.events_by_year[i + 1]['2026 MC'] = 0
                               self.hllhc_mc_cpu_time[i + 1] = 0
                               self.hllhc_mc_cpu_required[i + 1] = 0
                           self.events_by_year[i + 1]['2026 MC'] += mc_events[i]
                           self.hllhc_mc_cpu_time[i + 1] += self.hllhc_mc_cpu_time[i]
                           self.hllhc_mc_cpu_required[i + 1] += self.hllhc_mc_cpu_required[i]

    def get_totals(self):

        self.total_cpu_required = {i : 
                          self.data_cpu_required[i] + 
                          self.rereco_cpu_required[i] +
                          self.lhc_mc_cpu_required[i] +
                          self.hllhc_mc_cpu_required[i] +
                          self.analysis_cpu_required[i] for i in self.years}

        self.total_cpu_time = {i: 
                      self.data_cpu_time[i] +
                      self.rereco_cpu_time[i] +
                      self.lhc_mc_cpu_time[i] +
                      self.hllhc_mc_cpu_time[i] +
                      self.analysis_cpu_time[i]
                      for i in self.years}

        self.hpc_cpu_required = {i :
                          self.rereco_cpu_required[i] +
                          self.lhc_mc_cpu_required[i] +
                          self.hllhc_mc_cpu_required[i] for i in self.years}

        self.hpc_cpu_time = {i: self.rereco_cpu_time[i] +
                      self.lhc_mc_cpu_time[i] +
                      self.hllhc_mc_cpu_time[i] for i in self.years}

    def get_cpu_capacity_simple(self):
        """
        Then, CPU availability calculations.  This follows the "Available CPU
        power" spreadsheet.  Take a baseline value of 1.4 MHS06 in 2016, in
        future years subtract 5% of the previous for retirements, and add 300
        kHS06 which gets improved by the cpu_improvement in each year, until
        2020, during LS2, when we shift the computing model to start buying an
        improved 600 kHS06 per year.

        This is kludgey -- need to establish the baseline to make the
        caluculation work, but once the calculation is there, delete the baseline
        for the histogram to work.  Not to mention that I couldn't get the
        dictionary comprehension to work here.
        """
        cpu_improvement_factor = self.model['improvement_factors']['hardware']
        cpu_improvement = {i : cpu_improvement_factor ** (i-2017) for i in self.years}

        self.cpu_capacity_simple = {self.years[0] - 1 : 1.4 * mega}

        # This variable assumes that you can have the cpu_capacity for an entire
        # year and thus calculates the HS06 * s available (in principle).

        self.cpu_time_capacity_simple = {self.years[0] - 1 : 1.4 * mega}

        retirement_rate = 0.05

        for i in self.years:
            self.cpu_capacity_simple[i] = self.cpu_capacity_simple[i-1] * (1 - retirement_rate) + (300 if i < 2020 else 600) * kilo * cpu_improvement[i]
            self.cpu_time_capacity_simple[i] = self.cpu_capacity_simple[i] * seconds_per_year

        del self.cpu_capacity_simple[self.years[0] - 1]
        del self.cpu_time_capacity_simple[self.years[0] - 1]


    def get_cpu_capacity(self):
        """
        CPU capacity model ala data.py

        Set the initial points
        """

        self.cpu_capacity = {str(self.model['capacity_model']['cpu_year']): self.model['capacity_model']['cpu_start']}
        self.cpu_time_capacity = {str(self.model['capacity_model']['cpu_year']): self.model['capacity_model']['cpu_start'] * seconds_per_year}


        # A bit of a kludge. Assume what we have now was bought and will be retired in equal chunks over its lifetime
        cpu_added = {}
        for year in range(self.model['capacity_model']['cpu_year'] - self.model['capacity_model']['cpu_lifetime'] + 1,
                          self.model['capacity_model']['cpu_year'] + 1):
            retired = self.model['capacity_model']['cpu_start'] / self.model['capacity_model']['cpu_lifetime']
            cpu_added[str(year)] = retired

        cpu_factor = self.model['improvement_factors']['hardware']

        for year in self.years:
            if str(year) not in self.cpu_capacity:
                cpu_delta = 0  # Find the delta which can be time dependant
                cpu_deltas = self.model['capacity_model']['cpu_delta']
                for delta_year in sorted(cpu_deltas.keys()):
                    if int(year) >= int(delta_year):
                        last_cpu_year = int(delta_year)
                        cpu_delta = self.model['capacity_model']['cpu_delta'][delta_year]

                cpu_added[str(year)] = cpu_delta * cpu_factor ** (int(year) - int(last_cpu_year))

                # Retire cpu added N years ago or retire 0

                cpu_retired = cpu_added.get(str(int(year) - self.model['capacity_model']['cpu_lifetime']), 0)
                self.cpu_capacity[str(year)] = self.cpu_capacity[str(int(year) - 1)] + cpu_added[str(year)] - cpu_retired
                self.cpu_time_capacity[str(year)] = self.cpu_capacity[str(year)] * seconds_per_year

    def get_fractions(self):
        self.fractions = {}
        self.fractions['SIM'] = {}
        self.fractions['DIGI'] = {}
        self.fractions['RECO'] = {}
        self.fractions['RERECO'] = {}
        self.fractions['ANALYSIS'] = {}
        self.uscpu = {}

        self.fractions['PROMPT'] = 0.
        self.fractions['GEN'] = 0.03
        self.fractions['us'] = self.model['us_fraction_T1T2']

        
        for i in self.years:
            #Bug! year = i
            year = 2030 

            #first some calculations we didn't do before
            lhcSim = self.performance_by_year(year, 'GENSIM', data_type='mc', kind='2017')[0]
            lhcDigi = self.performance_by_year(year, 'DIGI', data_type='mc', kind='2017')[0]
            lhcReco = self.performance_by_year(year, 'RECO', data_type='mc', kind='2017')[0]

            hllhcSim = self.performance_by_year(year, 'GENSIM', data_type='mc', kind='2026')[0]
            hllhcDigi = self.performance_by_year(year, 'DIGI', data_type='mc', kind='2026')[0]
            hllhcReco =  self.performance_by_year(year, 'RECO', data_type='mc', kind='2026')[0]

            lhcDigiFraction = lhcDigi / (lhcSim + lhcDigi + lhcReco)
            lhcRecoFraction = lhcReco / (lhcSim + lhcDigi + lhcReco)
            lhcSimFraction = lhcSim / (lhcSim + lhcDigi + lhcReco)

            hllhcDigiFraction = hllhcDigi / (hllhcSim + hllhcDigi + hllhcReco)
            hllhcRecoFraction = hllhcReco / (hllhcSim + hllhcDigi + hllhcReco)
            hllhcSimFraction = hllhcSim / (hllhcSim + hllhcDigi + hllhcReco)

            lhcFraction= self.lhc_mc_cpu_time[i] / (self.lhc_mc_cpu_time[i] + self.hllhc_mc_cpu_time[i])

            totalT1T2 = (self.total_cpu_time[i] - self.data_cpu_time[i]) * (1.0 + self.fractions['GEN'])

            self.fractions['SIM'][i] = (lhcSimFraction * lhcFraction + hllhcSimFraction * (1.0 - lhcFraction)) *\
                                       (self.lhc_mc_cpu_time[i] + self.hllhc_mc_cpu_time[i]) / totalT1T2

            self.fractions['DIGI'][i] = (lhcDigiFraction * lhcFraction +
                                         hllhcDigiFraction * (1.0 - lhcFraction)) *\
                                         (self.lhc_mc_cpu_time[i] + self.hllhc_mc_cpu_time[i]) / totalT1T2

            self.fractions['RECO'][i] = (lhcRecoFraction * lhcFraction +
                                        hllhcRecoFraction * (1.0 - lhcFraction)) *\
                                        (self.lhc_mc_cpu_time[i] + self.hllhc_mc_cpu_time[i]) / totalT1T2

            self.fractions['RERECO'][i] = self.rereco_cpu_time[i] / totalT1T2
            self.fractions['ANALYSIS'][i] = self.analysis_cpu_time[i] / totalT1T2
            promptFraction = 0.
            self.uscpu[i] = totalT1T2 * self.fractions['us']/tera


