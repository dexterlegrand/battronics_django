import numpy as np

from jobqueue_manager.abd_extractor.readers.base_reader import BaseReader
from ndaparser import NdaParser


class NdaReader(BaseReader):
    def __init__(self, file):
        file = file.get_path()  # necessary because file is a UploadFile object after that file is path as string
        super(NdaReader, self).__init__(file)
        self.parser = NdaParser(self.file)

    def split_charge_cycle(self):
        self.data['step_name'] = self.data['step_name'].replace(
            ['CCCV_Chg', '20', 'Rest'], ['charge', 'discharge', 'OCV'])  # replace step names to work with base func

        self.convert_step_name_to_step_flag()

    def problem_solving(self):
        # todo this line solve the problem that timestamp is not always a vaild daytime object, if this is solved in nda parser itself it will be obsolete here
        self.data = self.data.astype({'timestamp': 'datetime64[ns]'})
        self.data = self.data.rename(columns={'timestamp': 'time_no_tz'})

        # todo solve column naming problem
        # column_names = set(self.data.columns)
        # if 'current_mA' in column_names:  # todo if we have mA etc. we neet to calculate to A units etc
        if 'current_mA' in self.data.columns:
            self.data.rename({'current_mA': 'current',
                              'voltage_V': 'voltage',
                              'energy_mWh': 'energy',
                              'capacity_mAh': 'capacity'}, axis=1, inplace=True)  # rename columns

            self.data['current'] = self.data['current'] / 1000  # convert mA to A
            self.data['energy'] = self.data['energy'] / 1000  # convert mWh to Wh
            self.data['capacity'] = self.data['capacity'] / 1000  # convert mAh to Ah
            self.unit_conversion = True

        # todo solve current direction + -
        if self.data.loc[self.data['step_name'] == 'CCCV_Chg', 'current'].iloc[0] < 0:
            self.data['current'] = self.data['current'] * -1
            self.data['energy'] = self.data['energy'] * -1
            self.data['capacity'] = self.data['capacity'] * -1

        # todo when no cycle_id
        if 'cycle_id' not in self.data.columns:
            if 'step_ID' in self.data.columns:  # if there is step_ID we use this to generate cycle_id
                # because agg data need charge and discharge in one cycle we neet to combine two of the original IDs
                # with dividing by 2 and flooring result we combine two IDs
                self.data['step_ID'] = (self.data['step_ID'] / 2).apply(np.floor)
                self.data['step_ID'] = self.data['step_ID'].replace(0, 1)  # start with Rest cycle we add this to follow up
                self.data = self.data.astype({'step_ID': 'int'})  # because of dividing typ is float we want it as int
                self.data = self.data.rename(columns={'step_ID': 'cycle_id'})  # change label

    def get_data(self):
        self.data = self.parser.to_df()

        self.problem_solving()
        self.transform_to_timezone_bound()

        self.split_charge_cycle()
