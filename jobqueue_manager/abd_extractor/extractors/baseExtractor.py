import numpy as np
import pandas as pd
from django.db import connection, transaction
from abc import ABC
import jobqueue_manager.abd_extractor.models as extractorModels
from abd_database.models import CellTest, TestType, CyclingTest, BaseAggData, AggData, UploadFile, CyclingRawData,\
    HPPCTest, HPPCAggData, ResistanceData
import jobqueue_manager.abd_extractor.helpers.extractor_helper as helper
from jobqueue_manager.abd_extractor.helpers.to_csv_helper import get_cyclingRawData_csv
from customexceptions import VersionError
import logging

logger = logging.getLogger(__name__)

warnings = []


class BaseExtractor(ABC):
    def __init__(self, files):
        logger.info("Initializing BaseExtractor")
        self.files: list = files
        self.data_hppc: pd.DataFrame = pd.DataFrame()

        self.cellTests: [CellTest] = []
        self.tests: [TestType] = []
        self.agg_datas: list[list[BaseAggData]] = []
        self.warnings: list = []

        self.extract_data()

    def extract_data(self):
        logger.info("Start extracting data")
        for index, reader in enumerate(self.readers):
            try:
                logger.info(f"Getting data and cleaning it for file {index}/{len(self.readers)}")
                self.files[index].set_status(UploadFile.StatusCodes.EXTRACTING)
                reader.get_data()
                self.files[index].set_status(UploadFile.StatusCodes.CLEANING)
                self.clean_data(index)
                self.files[index].set_status(UploadFile.StatusCodes.PREPARED)
            except VersionError as e:
                logger.error(f"{e} by file {index}/{len(self.readers)}")
                transaction.on_commit(lambda: self.files[index].set_status(UploadFile.StatusCodes.ERROR, e))
                # TODO: logg, message to errorcodes/warnings, return  raise version error for upper func?
            except Exception as e:
                logger.error(f"Error in file nr {index}/{len(self.readers)}: \n{e}")
                transaction.on_commit(lambda: self.files[index].set_status(UploadFile.StatusCodes.ERROR, e))

        self.save_data()

    def clean_data(self, index):
        logger.info(f"Cleaning data for file nr. {index}")
        self.readers[index].check_headers(set(CyclingRawData.get_required_fields(self)), set(CyclingRawData.get_additional_fields(self)))
        self.readers[index].remove_nan()
        self.readers[index].get_date()
        if not self.readers[index].date:
            self.readers[index].date = self.date
        self.readers[index].data = helper.close_cycle_gaps(self.readers[index].data, pd.DataFrame())
        self.add_cycle_id_offset(self.readers[index].data, self.readers[index].date)
        logger.info(f"Successfully cleaned data")
        # error-correction

    def save_data(self):
        logger.info(f"Start saving data to database")

        for file_index, reader in enumerate(self.readers):
            # TODO: HPPCTest was saved even though CyclingTest failed --> should not happen due to atomic()?
            with transaction.atomic():
                try:
                    logger.info(f"Saving data for file {file_index}/{len(self.readers)}")
                    self.cellTests.append([])
                    self.tests.append([])
                    self.agg_datas.append([])
                    self.files[file_index].set_status(UploadFile.StatusCodes.SAVING)
                    samples_hppc = self.readers[file_index].data[
                        self.readers[file_index].data['step_flag'].isin([5, 6])]
                    test_index = 0
                    if not samples_hppc.empty:
                        cycle_ids = samples_hppc['cycle_id'].unique()
                        self.data_hppc = self.readers[file_index].data[
                            self.readers[file_index].data['cycle_id'].isin(cycle_ids)]
                        self.readers[file_index].data = self.readers[file_index].data[
                            ~self.readers[file_index].data['cycle_id'].isin(cycle_ids)]
                        # TODO: At the moment exact same CellTest as for the CyclingData.
                        self.cellTests[file_index].append(
                            CellTest(battery=self.battery, dataset=self.dataset, date=self.readers[file_index].date,
                                     equipment=self.equipment, file=self.files[file_index]).save())
                        self.tests[file_index].append(self.save_HPPCTest(file_index, test_index))  # Needs test_index to get the correct CellTest
                        self.agg_datas[file_index].append(self.save_HPPCaggData(file_index, test_index))  # Needs test_index to get the correct TestType
                        self.data_hppc = self.post_clean_HPPCRawData(self.data_hppc, file_index, test_index)
                        self.save_HPPCRawData(self.data_hppc)
                        test_index += 1

                    if not self.readers[file_index].data.empty:
                        self.cellTests[file_index].append(CellTest(battery=self.battery,
                                                                   dataset=self.dataset,
                                                                   date=self.readers[file_index].date,
                                                                   equipment=self.equipment,
                                                                   file=self.files[file_index]).save())
                        self.tests[file_index].append(self.save_cyclingTest(file_index, test_index))    # Needs test_index to get the correct CellTest
                        self.agg_datas[file_index].append(self.save_aggData(file_index, test_index))    # Needs test_index to get the correct TestType
                        self.readers[file_index].data = self.post_clean_cyclingRawData(file_index, test_index)
                        self.save_cyclingRawData(file_index)
                    logger.info(f"Successfully saved all data for")
                    self.files[file_index].set_status()
                except Exception as e:
                    logger.error(f"Error in file nr {file_index}/{len(self.readers)}: \n{e}")
                    transaction.on_commit(lambda: self.files[file_index].set_status(UploadFile.StatusCodes.ERROR, e))

    def save_cyclingTest(self, file_index, test_index=0):
        return CyclingTest(cellTest=self.cellTests[file_index][test_index]).save()

    def save_HPPCTest(self, file_index, test_index=0):
        return HPPCTest(cellTest=self.cellTests[file_index][test_index]).save()

    def save_aggData(self, reader_index, test_index=0, df_error_codes=pd.DataFrame(), additive=None):
        if not additive:
            df_cyclingRawData = self.readers[reader_index].data
        else:
            df_cyclingRawData = self.readers[reader_index].data[additive]['CyclingRawData']['data']
        groups = df_cyclingRawData.groupby('cycle_id')
        entries = []
        for cycle_index, group in groups:
            cycle_id = cycle_index
            cc_charge_avg = None
            cc_discharge_avg = None
            charge_c_rate = None
            discharge_c_rate = None
            charge_capacity = None
            discharge_capacity = None
            efficiency = None
            ambient_temperature = None
            start_time = None
            end_time = None
            min_voltage = None
            max_voltage = None

            error_codes = None

            battery_type = None
            if hasattr(self, 'battery'):
                battery_type = self.battery.battery_type
            else:
                battery_type = self.battery_types[reader_index]

            if len(group[group['step_flag'].isin([2, 3])]['current']) > 0:
                cc_charge_avg = group[group['step_flag'].isin([2, 3])]['current'].mean()
                charge_c_rate = np.round(cc_charge_avg / battery_type.theoretical_capacity, 2)
            if len(group[group['step_flag'] == 4]['current']) > 0:
                cc_discharge_avg = abs(group[group['step_flag'] == 4]['current'].mean())
                discharge_c_rate = np.round(cc_discharge_avg / battery_type.theoretical_capacity, 2)
            if len(group[group['step_flag'].isin([2, 3])]) > 0:
                charge_capacity = group[group['step_flag'].isin([2, 3])]['capacity'].abs().max()
            if len(group[group['step_flag'] == 4]['capacity']) > 0:
                discharge_capacity = group[group['step_flag'] == 4]['capacity'].abs().max()
            if discharge_capacity is not None and charge_capacity is not None and charge_capacity != 0:
                efficiency = discharge_capacity / charge_capacity * 100
            if 'ambient_temperature' in group:
                if group['ambient_temperature'].notnull().values.all():
                    ambient_temperature = group['ambient_temperature'].mean()
            start_time = group['time'].min()
            end_time = group['time'].max()
            min_voltage = group['voltage'].min()
            max_voltage = group['voltage'].max()
            # null check
            if not df_error_codes.empty:
                if cycle_index in df_error_codes['cycle_id']:
                    error_codes = df_error_codes["error"].loc[cycle_index]
                    if type(error_codes) is not list:
                        error_codes = [int(error_codes)]
            if error_codes is None:
                error_codes = []
            entries.append(AggData(cycle_id=cycle_id,
                                   charge_capacity=charge_capacity,
                                   discharge_capacity=discharge_capacity,
                                   efficiency=efficiency,
                                   charge_c_rate=charge_c_rate,
                                   discharge_c_rate=discharge_c_rate,
                                   cycling_test=self.tests[reader_index][test_index],
                                   ambient_temperature=ambient_temperature,
                                   start_time=start_time,
                                   end_time=end_time,
                                   min_voltage=min_voltage,
                                   max_voltage=max_voltage,
                                   error_codes=error_codes).save())

        return entries

    def save_HPPCaggData(self, reader_index, test_index=0, df_error_codes=pd.DataFrame()):
        df_HPPCRawData = self.data_hppc
        groups = df_HPPCRawData.groupby('cycle_id')
        entries = []
        for cycle_index, group in groups:
            cycle_id = cycle_index
            ambient_temperature = None
            start_time = None
            end_time = None
            error_codes = None

            battery_type = None
            if hasattr(self, 'battery'):
                battery_type = self.battery.battery_type
            else:
                battery_type = self.battery_types[reader_index]

            if 'ambient_temperature' in group:
                if group['ambient_temperature'].notnull().values.all():
                    ambient_temperature = group['ambient_temperature'].mean()
            start_time = group['time'].min()
            end_time = group['time'].max()
            # null check
            if not df_error_codes.empty:
                if cycle_index in df_error_codes['cycle_id']:
                    error_codes = df_error_codes["error"].loc[cycle_index]
                    if type(error_codes) is not list:
                        error_codes = [int(error_codes)]
            if error_codes is None:
                error_codes = []
            aggdata = HPPCAggData(cycle_id=cycle_id,
                                  hppc_test=self.tests[reader_index][test_index],
                                  ambient_temperature=ambient_temperature,
                                  start_time=start_time,
                                  end_time=end_time,
                                  error_codes=error_codes).save()
            entries.append(aggdata)

            pulses = group.loc[group['step_flag'].isin([5, 6])]
            grouped_pulses = pulses.groupby((pulses.index.to_series().diff() > 1).cumsum())
            for pulse_id, pulse in grouped_pulses:
                self.save_ResistanceData(pulse, group, aggdata, cycle_index, ambient_temperature)

        return entries

    @staticmethod
    def calc_resistance(pulse, group):
        idx_last_pulse = pulse.index[-1]
        idx_last_before_pulse = pulse.index[0] - 1

        voltage_pulse = group.loc[idx_last_pulse, 'voltage']
        voltage_before_pulse = group.loc[idx_last_before_pulse, 'voltage']
        diff_voltage = voltage_pulse - voltage_before_pulse

        current_pulse = group.loc[idx_last_pulse, 'current']
        mean_current_pulse = pulse['current'].mean()
        current_before_pulse = group.loc[idx_last_before_pulse, 'current']
        diff_current = current_pulse - current_before_pulse

        resistance = diff_voltage / diff_current

        return resistance, mean_current_pulse

    def save_ResistanceData(self, pulse, group, aggdata, cycle_index, ambient_temperature):

        resistance = None
        test_current = None
        cell_temperature = None
        # ambient_temperature = None
        soc = None

        # TODO: Probably better to only check this once and not here and in save_aggdata
        if 5 in pulse.loc[:, 'step_flag'].unique():
            resistance, test_current = self.calc_resistance(pulse, group)

        if 6 in pulse.loc[:, 'step_flag'].unique():
            resistance, test_current = self.calc_resistance(pulse, group)

        return ResistanceData(hppc_agg_data=aggdata,
                              cycle_id=cycle_index,
                              cell_temperature=cell_temperature,
                              ambient_temperature=ambient_temperature,
                              soc=soc,
                              resistance=resistance,
                              test_current=test_current).save()

    #TODO: Fix cycle offset calculation
    def post_clean_cyclingRawData(self, file_index, test_index=0, cellTest_name=None):
        if cellTest_name:
            df_cyclingRawData = self.readers[file_index].data[cellTest_name]['CyclingRawData']['data']
        else:
            df_cyclingRawData = self.readers[file_index].data
        entry_cycle_id = df_cyclingRawData.iloc[0]['cycle_id']
        last_cycle_id = entry_cycle_id
        nbr_of_jumps = 0
        offset_cycle_id = entry_cycle_id - 1 if entry_cycle_id != 0 else 0
        df_cyclingRawData['agg_data'] = ''
        for index, group in df_cyclingRawData.groupby('cycle_id'):
            if index - last_cycle_id >= 1:
                nbr_of_jumps += index - last_cycle_id - 1
            df_cyclingRawData.loc[df_cyclingRawData["cycle_id"] == index, 'agg_data'] = self.agg_datas[file_index][test_index][index - nbr_of_jumps - offset_cycle_id - 1]
            last_cycle_id = index
        if not set(extractorModels.CyclingRawData.required_fields).issubset(df_cyclingRawData.columns):
            missing_attributes = set(extractorModels.CyclingRawData.required_fields) - set(df_cyclingRawData.columns)
            warnings.append(f'Missing required attribute(s): {missing_attributes} in cyclingrawdata-dataset')
            raise AttributeError(f'Missing required attribute(s): {missing_attributes} in cyclingrawdata-dataset')
        return df_cyclingRawData

    # TODO: Similar to post_clean_cyclingRawData. Cycle offset calculation will be reworked, thus wait till then for changes
    def post_clean_HPPCRawData(self, df_HPPCRawData, file_index, test_index=0):
        entry_cycle_id = df_HPPCRawData.iloc[0]['cycle_id']
        last_cycle_id = entry_cycle_id
        nbr_of_jumps = 0
        offset_cycle_id = entry_cycle_id - 1 if entry_cycle_id != 0 else 0
        df_HPPCRawData['agg_data'] = ''
        for index, group in df_HPPCRawData.groupby('cycle_id'):
            if index - last_cycle_id >= 1:
                nbr_of_jumps += index - last_cycle_id - 1
            df_HPPCRawData.loc[df_HPPCRawData["cycle_id"] == index, 'agg_data'] = self.agg_datas[file_index][test_index][index - nbr_of_jumps - offset_cycle_id - 1]
            last_cycle_id = index
        if not set(extractorModels.HPPCRawData.required_fields).issubset(df_HPPCRawData.columns):
            missing_attributes = set(extractorModels.HPPCRawData.required_fields) - set(df_HPPCRawData.columns)
            warnings.append(f'Missing required attribute(s): {missing_attributes} in cyclingrawdata-dataset')
            raise AttributeError(f'Missing required attribute(s): {missing_attributes} in cyclingrawdata-dataset')
        return df_HPPCRawData

    def save_cyclingRawData(self, index, cellTest_name=None):
        if cellTest_name:
            df_cyclingRawData = self.readers[index].data[cellTest_name]['CyclingRawData']['data']
        else:
            df_cyclingRawData = self.readers[index].data
        if 'step_id' in df_cyclingRawData.columns:
            df_cyclingRawData.drop(columns=['step_id'], inplace=True)
        cyclingRawData_csv, columns = get_cyclingRawData_csv(df_cyclingRawData)

        with connection.cursor() as cursor:
            cursor.copy_from(cyclingRawData_csv, 'abd_database_cyclingrawdata', sep=',', columns=columns, null='None')

    @staticmethod
    def save_HPPCRawData(data):
        if 'step_id' in data.columns:
            data.drop(columns=['step_id'], inplace=True)
        HPPCRawData_csv, columns = get_cyclingRawData_csv(data)

        with connection.cursor() as cursor:
            cursor.copy_from(HPPCRawData_csv, 'abd_database_hppcrawdata', sep=',', columns=columns, null='None')

    def add_cycle_id_offset(self, data, date):
        # get the first cycle before the first test-date from the adding test
        sql = f'''
            SELECT rawdata.cycle_id
            FROM public.abd_database_battery as battery
            INNER JOIN public.abd_database_celltest as celltest on battery.id=celltest.battery_id
            INNER JOIN public.abd_database_cyclingtest as cyclingtest on celltest.id=cyclingtest."cellTest_id"
            INNER JOIN public.abd_database_aggdata as aggdata on cyclingtest.id=aggdata."cycling_test_id"
            INNER JOIN public.abd_database_cyclingrawdata as rawdata on aggdata.id=rawdata.agg_data_id
            WHERE battery.id={self.battery.id} AND time<'{date}'
            ORDER BY rawdata.id DESC
            LIMIT 1
            '''
        cycle_id = None
        with connection.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchone()
            if result:
                cycle_id = result[0]

        if not cycle_id:
            # no cycles before date found
            # all other cycles need to be increased by max(cycle_id)
            cycle_id_offset = data['cycle_id'].max()
            for cell_test in self.battery.cell_test.all():
                if hasattr(cell_test, 'cyclingtest_test_type'):
                    cell_test.cyclingtest_test_type.cycle_offset = cell_test.cyclingtest_test_type.cycle_offset + cycle_id_offset
                    cell_test.cyclingtest_test_type.save(update_fields=['cycle_offset'])
        else:
            data['cycle_id'] = data['cycle_id'].apply(lambda x: x + cycle_id)
            # get all tests after the last test-date from the uploading test
            sql = f'''
            SELECT DISTINCT(cyclingtest.id)
            FROM public.abd_database_battery as battery
            INNER JOIN public.abd_database_celltest as celltest on battery.id=celltest.battery_id
            INNER JOIN public.abd_database_cyclingtest as cyclingtest on celltest.id=cyclingtest."cellTest_id"
            INNER JOIN public.abd_database_aggdata as aggdata on cyclingtest.id=aggdata."cycling_test_id"
            INNER JOIN public.abd_database_cyclingrawdata as rawdata on aggdata.id=rawdata.agg_data_id
            WHERE battery.id={self.battery.id} AND time>'{data['time'].max()}'
            ORDER BY cyclingtest.id ASC
            '''
            cycletest_ids = None
            with connection.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()
                if result:
                    cycletest_ids = [x[0] for x in result]

            if cycletest_ids:
                # add the length of the uploading test to the offset for all tests after the uploading one.
                for cycletest_id in cycletest_ids:
                    cycletest = CyclingTest.objects.get(pk=cycletest_id)
                    cycletest.cycle_offset = cycletest.cycle_offset + data['cycle_id'].unique().size
                    cycletest.save(update_fields=['cycle_offset'])
