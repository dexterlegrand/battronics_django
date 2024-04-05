import pandas as pd
import numpy as np
import datetime
from difflib import SequenceMatcher

from jobqueue_manager.abd_extractor.helpers.reader_helper import cast_datetime_to_float
from jobqueue_manager.abd_extractor.readers.base_reader import BaseReader
from customexceptions import VersionError

# todo to open .xlsx files need to install openpyxl package (pip install openpyxl)


class DigatronReader(BaseReader):
    def __init__(self, file):
        file = file.get_path()
        self.start_date = ''
        self.unit_conversion_curr = False
        self.unit_conversion_cap = False
        self.meta = pd.DataFrame()
        self.version_list = ['V 1.600.386']  # versions witch are compatible with this script
        super(DigatronReader, self).__init__(file)

    def find_start_date(self):
        indices = self.str_finder('start of test')  # (string search lower case)

        try:
            # takes the two fields next to start of test str field and combine them to a datetime obj
            # date and time are stored in separate fields combine them
            date = datetime.datetime.combine(self.data.iloc[indices[0, 0], indices[0, 1] + 1],
                                             self.data.iloc[indices[0, 0], indices[0, 1] + 2])
        except ValueError:
            print('ValueError:', ValueError)

        # check if it's a date filed or something others
        if isinstance(date, datetime.datetime):
            self.start_date = date
        else:
            print('The field is not a datetime object, return value date of today')
            self.start_date = date.today()

    def find_version(self):
        indices = self.str_finder('version')  # (string search lower case)

        try:
            version_nr = self.data.iloc[indices[0, 0], indices[0, 1]]

            for versions in self.version_list:  # compare version of file with allowed versions in list
                match = SequenceMatcher(None, version_nr, versions).find_longest_match()
                result = versions[match.b:match.b + match.size]

            if result in self.version_list:  # if the found version is equal to one in list data can be extracted
                print('Version is compatible')
                return True
            else:
                print('Version not supported')
                raise VersionError()

        except IndexError:
            print('no Version found')
            raise VersionError()

    def unit_check(self):
        try:
            amp_unit = self.data.Current.iloc[1]
            cap_unit = self.data.AhAccu.iloc[1]

            if amp_unit == '[mA]':
                self.unit_conversion_curr = True

            if cap_unit == '[mAh]':
                self.unit_conversion_cap = True
        except AttributeError as e:
            print('AttributeError:', e)

    def split_meta_data(self):
        if not self.header_line == 0:
            self.meta = self.data.iloc[: self.header_line].dropna(axis=1, how='all')  # extract the metadata
            self.data = self.data.iloc[self.header_line:]  # extract all data from header to end
            self.data.columns = self.data.iloc[0]  # use real header as df header

        else:
            print('Header not found or no meta data in this file')

    def remove_unwanted_status_lines(self, status):
        indices = self.str_finder(status)
        self.data = self.data.drop(indices[:, 0])  # remove the rows where status is unwanted
        self.data = self.data.reset_index(drop=True)

    def remove_switching_rows(self):
        # this removes the empty rows when step switch occurs
        indices = list(self.data.loc[pd.isna(self.data['capacity']), :].index)
        self.data = self.data.drop(indices)  # remove the rows where step change and they are empty therefor
        self.data = self.data.reset_index(drop=True)

    def adjust_data(self):
        self.remove_unwanted_status_lines('prg')  # remove PRG status rows
        self.remove_unwanted_status_lines('sto')  # remove STO rows
        self.remove_switching_rows()
        self.data = self.data.astype(dtype={"cycle_id": np.int32,
                                            "capacity": np.float64,
                                            "voltage": np.float64,
                                            "current": np.float64
                                            })  # cast the value types

        if self.unit_conversion_curr:
            self.data['current'] = self.data['current'] / 1000  # conv mA to A
        if self.unit_conversion_cap:
            self.data['capacity'] = self.data['capacity'] / 1000  # conv mAh to Ah

    def set_step_flag(self):
        self.data = self.data.replace(['CHA', 'DCH', 'PAU'], ['charge', 'discharge', 'OCV'])  # replace Status names
        self.convert_step_name_to_step_flag()

    def time_conversion(self):  # construct a timestamp with start date and program time (starts by 0)
        self.data['time_no_tz'] = pd.to_timedelta(self.data['Program time'].astype(str)) + self.start_date

    def energy_calculation(self):
        # calculate the difference of energy
        self.data.loc[self.data['current'] != 0, 'energy_diff'] = self.data['capacity'].diff() * self.data['voltage']
        self.data.loc[self.data['current'] == 0, 'energy_diff'] = 0  # if current 0 energy 0
        self.data.loc[self.data['capacity'] == 0, 'energy_diff'] = 0  # if capacity 0 energy 0
        # use groupeby and cumsum to cumulate the energy in the column and reset to 0 every time energy is 0
        self.data['energy'] = self.data.groupby(self.data.energy_diff.eq(0).cumsum()).energy_diff.transform('cumsum')

    def get_temp_fields(self, nbr_of_fields):
        chan_hits = []
        t_hits = []
        for i in range(1, nbr_of_fields + 1):
            chan_string = f"chan00{i}"
            t_string = f"[t{i}]"
            chan_hit = self.str_finder(chan_string)
            if chan_hit.any() and len(chan_hit) == 1:
                chan_hits.append(chan_hit[0])
            t_hit = self.str_finder(t_string)
            if t_hit.any() and len(t_hit) == 1:
                t_hits.append(t_hit[0])

        temperature_pairs = []
        for chan_hit in chan_hits:
            for t_hit in t_hits:
                if chan_hit[0] == t_hit[0] - 1 and chan_hit[1] == t_hit[1]:
                    temperature_pairs.append((chan_hit, t_hit))
        return temperature_pairs

    def get_data(self):
        self.data = pd.read_excel(self.file, nrows=30)
        version_supported = self.find_version()

        if version_supported:  # if version nr is not supported upload not possible
            self.find_start_date()
            self.find_header('step time')  # todo unit check on second header line

            # temp_column = self.str_finder('[t1]')  # search for temperature column (string search lower case)
            temperature_pairs = self.get_temp_fields(3)
            if len(temperature_pairs) > 1:
                #     TODO: pick from selection
                pass
            elif len(temperature_pairs) <= 0:
                #     TODO: throw error --> no pairs found // or just ignore temp field
                pass
            else:
                pass
            col_name = self.data.iloc[temperature_pairs[0][0][0], temperature_pairs[0][0][1]]

            self.split_meta_data()
            self.unit_check()
            try:
                self.data = pd.read_excel(self.file, header=self.header_line+1, skiprows=[self.header_line+2])
                self.data.rename({'Current': 'current',
                                  'Voltage': 'voltage',
                                  'AhAccu': 'capacity',
                                  'Cycle': 'cycle_id',
                                  'Status': 'step_name',
                                  'Step time': 'time_in_step'}, axis=1, inplace=True)
                if col_name:
                    self.data.rename({col_name: 'ambient_temperature'}, axis=1, inplace=True)
                self.data['step_name'] = self.data['step_name'].astype("string")
                self.data['time_in_step'] = self.data['time_in_step'].apply(lambda x: cast_datetime_to_float(x))

            except ValueError as ve:
                print('ValueError:', ve)

            self.adjust_data()
            self.set_step_flag()
            self.time_conversion()
            self.energy_calculation()
            self.transform_to_timezone_bound()
