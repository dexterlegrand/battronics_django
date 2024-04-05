import pandas as pd
import jobqueue_manager.abd_extractor.helpers.reader_helper as helper
from jobqueue_manager.abd_extractor.readers.base_reader import BaseReader


class Hdf5Reader(BaseReader):
    def __init__(self, file_path):
        super(Hdf5Reader, self).__init__(file_path)
        self.file = pd.HDFStore(file_path, 'r')
        self.battery = None #self.file.get('BatteryTable')
        self.dataset = None #self.file.get('BatteryTable/Dataset')

    def get_data(self):
        self.battery = self.file.get('BatteryTable')
        self.dataset = self.file.get('BatteryTable/Dataset')
        groups = list(self.file.root.BatteryTable.Dataset._v_groups)
        groups.sort(key=helper.get_number)
        for group in groups:
            self.extract(self.file.root.BatteryTable.Dataset[group])
        self.file.close()

    def extract(self, root):
        parent_name = root._v_pathname.split('/')[-2]
        if parent_name != 'Dataset':
            self.data[parent_name][root._v_name] = {'data': self.file.get(root._v_pathname)}
        else:
            self.data[root._v_name] = {'data': self.file.get(root._v_pathname)}
            if len(root._v_groups) > 0:
                for group in root._v_groups:
                    self.extract(root[group])

    def check_headers(self):
        super(Hdf5Reader, self).check_headers()

    def remove_nan(self):
        super(Hdf5Reader, self).remove_nan()

    def get_date(self):
        super(Hdf5Reader, self).get_date()

    def add_cycle_id_offset(self, battery, date):
        super(Hdf5Reader, self).add_cycle_id_offset()
