import pandas as pd
import numpy as np
from datetime import datetime
from jobqueue_manager.abd_extractor.readers.base_reader import BaseReader
from biologic import MPTReader


class BiologicReader(BaseReader):

    def __init__(self, file):
        file = file.get_path()
        self.meta = {}
        super(BiologicReader, self).__init__(file)
        self.parser = MPTReader(self.file)

    def get_date(self):
        try:
            start_date = datetime.strptime(self.meta.get('start_time'), '%m/%d/%Y %H:%M:%S.%f')
            return start_date
        except ValueError as ve1:
            print('ValueError:', ve1)

    def set_step_flag(self):
        conditions = [
            (self.data['mode'] == 1) & (self.data['current'] > 0),
            (self.data['mode'] == 1) & (self.data['current'] < 0),
            (self.data['mode'] == 2) & (self.data['current'] > 0),
            (self.data['mode'] == 2) & (self.data['current'] < 0),
        ]
        choices = [2, 4, 3, 5]
        self.data['step_flag'] = np.select(conditions, choices, default=1)

        # df_step = pd.DataFrame(index=range(len(self.data.index)), columns=['step_flag'])
        #
        # for elements in range(len(self.data.index)):
        #
        #     match ({'mode': self.data['mode'].iloc[elements], 'current': self.data['current'].iloc[elements]}):
        #         case {'mode': mode, 'current': current} if mode == 1 and current > 0:
        #             df_step['step_flag'].iloc[elements] = 2  # cc_charge
        #         case {'mode': mode, 'current': current} if mode == 1 and current < 0:
        #             df_step['step_flag'].iloc[elements] = 4  # cc_discharge
        #         case {'mode': mode, 'current': current} if mode == 2 and current > 0:
        #             df_step['step_flag'].iloc[elements] = 3  # cv_charge
        #         case {'mode': mode, 'current': current} if mode == 2 and current < 0:
        #             df_step['step_flag'].iloc[elements] = 5  # cv_discharge
        #         case _:
        #             df_step['step_flag'].iloc[elements] = 1  # OCV
        #
        # self.data['step_flag1'] = df_step

    def get_data(self):  # todo maybe integrate an unit check we are strongly depending a mA or mAh value, if there comes a A or Ah we result in wrong values later in db
        self.meta = self.parser.get_meta()  # get meta information of data
        self.data = pd.DataFrame(self.parser.to_df())  # load raw data

        self.data['current'] = self.data['I/mA'] / 1000  # convert mA into A

        self.data.rename({'cycle number': 'cycle_id',
                          'Ecell/V': 'voltage',
                          }, axis=1, inplace=True)  # rename columns

        self.data = self.data.astype({'voltage': 'float64',
                                      'current': 'float64',
                                      'cycle_id': 'int',
                                      'mode': 'int'})

        start_date = self.get_date()  # get the start date from meta information
        self.data['time_no_tz'] = pd.to_timedelta(self.data['time/s'], 's') + start_date  # generate timestamp

        # self.data.drop(columns=list(['ox/red', 'error', 'control changes', 'Ns changes', 'counter inc.', 'Ns',
        #                              'I Range', 'control/V/mA', 'dq/mA.h', '(Q-Qo)/mA.h', 'Q charge/discharge/mA.h',
        #                              'half cycle', '|Energy|/W.h', 'Energy charge/W.h', 'Energy discharge/W.h',
        #                              'Capacitance charge/µF', 'Capacitance discharge/µF', 'x', 'Efficiency/%',
        #                              'control/V', 'control/mA', 'R/Ohm']),
        #                inplace=True)  # reduce df on used fields

        # energy calculation
        dtime = self.data['time_no_tz'].diff().dt.seconds / 3600
        de = self.data['P/W'] * dtime.bfill()
        self.data['energy'] = de.cumsum()

        # capacity calculation
        self.data['capacity'] = (self.data['Q charge/mA.h'] + self.data['Q discharge/mA.h'] * -1) / 1000  # convert mAh to Ah
        self.set_step_flag()
        self.transform_to_timezone_bound()
