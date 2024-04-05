import pandas as pd

from jobqueue_manager.abd_extractor.readers.base_reader import BaseReader


class CsvReader(BaseReader):
    def __init__(self, file):
        file = file.get_path()
        super(CsvReader, self).__init__(file)

    def data_cleaner_on_failure(self):
        success = False
        column_types = self.column_types | {'time': 'datetime64[ns]'}
        while not success:  # todo infinity loop when a cast not work may a possibility to implement that in base?
            try:
                # try to cast to correct types
                self.data = self.data.astype(column_types)

                self.data = self.data.rename(columns={'time': 'time_no_tz'})
                self.transform_to_timezone_bound()
                self.data = self.data.reset_index(drop=True)  # reset index in case something was deleted

                success = True
            except ValueError:
                # if value error then next row is probably header
                self.data.drop(labels=0, axis=0, inplace=True)
            except Exception as e:
                # TODO: error handling
                pass

    def get_data(self):  # todo check on header, units
        self.data = pd.read_csv(self.file, nrows=10)
        if 'voltage' not in self.data.columns:
            self.find_header('voltage')  # (string search lower case)
        else:
            self.header_line = 'infer'  # the first row is the header

        try:
            # (string search lower case) return array of all indexes with 'a' for units like A Ah etc.
            unit_row = [self.str_finder('a')[0, 0] + 1]
        except IndexError as e:
            print('IndexError:', e)
            unit_row = []

        try:  # try to read csv with type cast and date parse remove unit column
            self.data = pd.read_csv(self.file, header=self.header_line, skiprows=unit_row,
                                    dtype=self.column_types, parse_dates=['time'])

        except ValueError as e:
            print('ValueError:', e)
            self.data = pd.read_csv(self.file)  # remove first row (second header)
            self.data_cleaner_on_failure()
