import pandas as pd
import numpy as np
# import datetime as dt

from jobqueue_manager.abd_extractor.readers.base_reader import BaseReader
from gamry_parser import GamryParser

EIS_TAG_MAPS = {
    'gamry': {
        'Freq': 'frequency',
        'Zreal': 'z_real',
        'Zimag': 'z_im',
        'Vdc': 'voltage',
        'Temp': 'temperature'
    }
}


class GamryReader(BaseReader):

    def __init__(self, file):
        file = file.get_path()
        super(GamryReader, self).__init__(file)
        self.prev_temp = None

    def file_type_detect(self):  # todo generate a step_flag to given data and cycle_id without that not complete functional
        dfx = pd.DataFrame(index=range(len(self.data.index)), columns=['cycle_id', 'step_flag'])
        # todo cycle id need to be put together by 2 or more files because gamry make new file for every part cycle
        match {'name': self.file}:
            case {'name': name} if 'CHARGE' in name:
                dfx['cycle_id'] = 0
            case {'name': name} if 'DISCHARGE' in name:
                dfx['cycle_id'] = 0
            case {'name': name} if 'OCV' in name:
                dfx['cycle_id'] = 0

    def generate_cycle_id(self):  # todo
        pass

    def get_data(self):

        self.data = GamryParser(filename=self.file)
        self.data.load(to_timestamp=True)  # load the data and convert the time into a real timestamp

        if 'CHARGE' not in self.data.header['TAG']:
            return pd.DataFrame(columns=['voltage', 'current'])

        assert len(self.data.curves) == 1, 'unexpected data format'

        df = pd.DataFrame(self.data.curves[0])
        df.rename(columns={'Vf': 'voltage',
                           'Im': 'current',
                           'T': 'time_no_tz',
                           'Temp': 'cell_temperature'}, inplace=True)

        # capacity and energy calculation
        dtime = df['time_no_tz'].diff().dt.seconds / 3600
        # capacity calc
        dq = df['current'] * dtime.bfill()
        df['capacity'] = dq.cumsum()
        # energy calc
        de = df['Pwr'] * dtime.bfill()
        df['energy'] = de.cumsum()

        df.fillna(0, inplace=True)
        # todo cycle_id need to exist for further processing
        # df[['step_flag',
        #     'cycle_id']] = None  # todo maybe add missing columns dynamically or in header check
        self.data = df
        self.data = self.data.rename(columns={'timestamp': 'time_no_tz'})

    def get_eis_data(self, file, voltage=None, temperature=None):
        # file.open()
        self.data = self.parser.Impedance(filename=file)
        self.data.load()

        nb_curves = self.data.curve_count
        assert nb_curves == 1, 'More than one curve per file not supported'

        df = self.data.curves[0]
        df.rename(EIS_TAG_MAPS['gamry'], axis=1, inplace=True)

        if 'frequency' in df.columns:
            if self.data.ocv_curve is not None:
                df['temperature'] = self.data.ocv_curve['Temp']
            elif self.prev_temp is not None:
                df['temperature'] = self.prev_temp
            else:
                df['temperature'] = np.NaN

            df.ffill(inplace=True)

            ts = self.get_file_timestamp()

            self.prev_temp = None
            self.set_eis_experiment(df=df, ts=ts)
        else:
            self.prev_temp = df['temperature'].mean()
            return None, None

        return df, self.experiment
