from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
import time
import pytz


class BaseReader(ABC):
    def __init__(self, file):
        self.data = {}
        self.file = file
        self.date = None
        self.unit_conversion = False  # if we had mA and need to convert to A set this on True
        self.header_line = 0
        self.column_types = {'voltage': 'float64',
                             'current': 'float64',
                             'capacity': 'float64',
                             'energy': 'float64',
                             'cycle_id': 'int',
                             'step_flag': 'int',
                             'time_in_step': 'float64',
                             'cell_temperature': 'float64',
                             'ambient_temperature': 'float64'}

    @abstractmethod
    def get_data(self, file):
        pass

    def str_finder(self, str_to_find):
        # return a matrix where value True when string exist in that df field (string search lower case)
        # TODO: FutureWarning: DataFrame.applymap has been deprecated. Use DataFrame.map instead.
        mask = self.data.applymap(lambda x: str_to_find in x.lower() if isinstance(x, str) else False).to_numpy()
        indices = np.argwhere(mask)  # return "coordinates" of the found True value
        return indices

    def find_header(self, string):
        indices = self.str_finder(string)  # (string search lower case)
        try:
            header_line = indices[0, 0]  # column where the first line of header lies
            self.header_line = header_line
        except IndexError:
            print('no header found')

    def transform_to_timezone_bound(self):
        localtz = time.tzname
        tz = pytz.timezone('Europe/Zurich')

        if (localtz[1] == 'CEST') or (localtz[0] == 'W. Europe Standard Time') or \
                (localtz[0] == 'Mitteleuropäische Zeit'):
            self.data['time'] = self.data['time_no_tz'].dt.tz_localize(tz)
        elif localtz[1] == 'UTC':
            self.data['time'] = self.data['time_no_tz'].dt.tz_localize(pytz.timezone('UTC'))
            self.data['time'] = self.data['time'].dt.tz_convert(tz)
        else:
            NotImplementedError(f'{localtz[1]} is not implemented')

    def convert_step_name_to_step_flag(self):
        self.data['step_flag'] = 99  # init step flag column with not used value to check at the end if it worked

        if self.unit_conversion:  # if wee need to change the unit from mA to A, comparison below need multiplier
            multiplier = 1000
        else:
            multiplier = 1

        while 1:
            charge = False
            discharge = False

            # if there are part cycles they are mixed we only take the part cycle to split it in its parts (dis-charge)
            if 'charge' in self.data['step_name'].unique():
                dfy = self.data[self.data['step_name'] == 'charge'].filter(
                    ['current', 'voltage']).reset_index()
                charge = True
                self.data = self.data.replace('charge', 'done')

            elif 'discharge' in self.data['step_name'].unique():
                dfy = self.data[self.data['step_name'] == 'discharge'].filter(
                    ['current', 'voltage']).reset_index()
                discharge = True
                self.data = self.data.replace('discharge', 'done')

            elif 'OCV' in self.data['step_name'].unique():  # directly convert the OCV flag
                self.data.loc[self.data.step_name == 'OCV', 'step_flag'] = 1  # OCV
                self.data = self.data.replace('OCV', 'done')

            elif 'CC_Chg' in self.data['step_name'].unique():  # directly convert the CC_Chg flag
                self.data.loc[self.data.step_name == 'CC_Chg', 'step_flag'] = 2  # CC_Chg
                self.data = self.data.replace('CC_Chg', 'done')

            elif 'CC_Dchg' in self.data['step_name'].unique():  # directly convert the CC_Dchg flag
                self.data.loc[self.data.step_name == 'CC_Dchg', 'step_flag'] = 4  # CC_Dchg
                self.data = self.data.replace('CC_Dchg', 'done')

            else:
                break

            if charge:  # if the combined cycle is a charge
                cv_max_value = dfy['voltage'].round(2).max()
                dfy.loc[dfy.voltage.round(2) == cv_max_value, 'step_name'] = 3  # set CV_Chg value
                dfy.loc[dfy.voltage.round(2) < cv_max_value, 'step_name'] = 2  # set CC_Chg value

            if discharge:  # if the combined cycle is a discharge
                cv_min_value = dfy['voltage'].round(2).min()
                dfy.loc[dfy.current * multiplier < 0, 'step_name'] = 4  # set CC_Dchg value
                dfy.loc[dfy.voltage.round(2) == cv_min_value, 'step_name'] = 5  # set CV_Dchg

            if charge or discharge:
                dfy.loc[dfy.current * multiplier == 0, 'step_name'] = 1  # set OCV value

                # set all the values from combined cycle in self.data['step_flag']
                for elements in range(0, len(dfy)):
                    # Vectorized
                    # TODO: check if this is faster than the original atleast SettingWithCopyWarning is gone
                    index = dfy['index'].iloc[elements]
                    self.data.loc[index, 'step_flag'] = dfy['step_name'].iloc[elements].copy()
                    # Original
                    # self.data['step_flag'].iloc[index] = dfy['step_name'].iloc[elements]


        # if there is a nan value in step_flag the behaviour of the device was not CC_ or CV_Chg, CC_ or CV_Dchg, OCV
        self.data = self.data.dropna(subset=['step_flag']).reset_index(drop=True)  # delete those rows
        self.data['step_flag'] = self.data['step_flag'].astype('int32')  # convert column to int

        if 99 in self.data['step_flag'].unique():
            print('one or more elements are not converted to the right step_flag')
            # todo handle the case of not treated cases

    def check_headers(self, required_names, additional_names):
        column_names = set(self.data.columns)

        # check for missing attributes
        if not required_names.issubset(
                self.data.columns):
            missing_attributes = required_names - column_names
            # self.data[list(missing_attributes)] = None  # add all missing columns to df
            raise AttributeError(
                f'Missing attribute(s) {missing_attributes} in data for extending test data to battery')
        # delete unnecessary columns
        required_names.update(additional_names)  # combine required and allowed fields to only delete not expected field
        self.data.drop(columns=list(column_names - required_names), inplace=True)

    def remove_nan(self):
        self.data = self.data.replace("", np.nan)
        self.data.fillna(value=np.nan, axis='columns', inplace=True)
        self.data = self.data.where(pd.notnull(self.data), None)

    def get_date(self):
        # TODO: check if only returning datetime instead of date for more accurate query (see add_cycle_id_offset)
        first_timestamp = self.data['time'].min().to_pydatetime().date()
        # TODO: check if timestamp is valid (not in unix, and not in the future or impossible past
        if first_timestamp:
            self.date = first_timestamp
