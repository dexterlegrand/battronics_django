from datetime import datetime

import numpy as np
import pandas as pd
from django.conf import settings
from django.db import transaction

from abd_database.models import Battery, CellTest, BatteryType, Dataset, UploadFile
from abd_management.models import Organisation
from jobqueue_manager.abd_extractor.extractors.baseExtractor import BaseExtractor
from jobqueue_manager.abd_extractor.readers.hdf5_reader import Hdf5Reader
import jobqueue_manager.abd_extractor.helpers.extractor_helper as helper
import jobqueue_manager.abd_extractor.models as extractorModels
import logging

logger = logging.getLogger(__name__)


class Hdf5Extractor(BaseExtractor):
    
    def __init__(self, files, owner):
        # TODO: make battery_type and battery to list for uploading multiple files at once
        self.owner = owner
        self.battery_types: [BatteryType] = []
        self.batteries: [Battery] = []
        self.datasets: [Dataset] = []
        self.readers = [Hdf5Reader(file.file.path) for file in files]
        super(Hdf5Extractor, self).__init__(files)

    def extract_data(self):
        super(Hdf5Extractor, self).extract_data()
        for reader_index, reader in enumerate(self.readers):
            try:
                for test_index, cellTest_name in enumerate(reader.data):
                    if 'CyclingRawData' in reader.data[cellTest_name]:
                        reader.data[cellTest_name]['CyclingRawData']['data'] = self.post_clean_cyclingRawData(reader_index, test_index, cellTest_name)
                        self.save_cyclingRawData(reader_index, cellTest_name)
                        logger.info("Saved cycling raw data")
                    elif 'EISRawData' in reader.data[cellTest_name]:
                        # Prepared for EIS data
                        pass
                return list(set(self.warnings))
            except Exception as e:
                # TODO: check if necessary for other extractors AND if handling can be more specifig than general Exception
                logger.error(f"Error in file nr {reader_index}/{len(self.readers)}: \n{e}")
                transaction.on_commit(lambda: self.files[reader_index].set_status(UploadFile.StatusCodes.ERROR, e))

    def clean_data(self, index):
        self.readers[index].battery = self.clean_battery(index)
        self.readers[index].dataset = self.clean_dataset(self.readers[index].dataset)

        for test_index, cellTest_name in enumerate(self.readers[index].data):
            self.readers[index].data[cellTest_name]['CyclingRawData']['data'] = self.clean_cyclingRawData(self.readers[index].data[cellTest_name]['CyclingRawData']['data'], self.readers[index].data[cellTest_name]['ErrorCodes']['data'])

    def save_data(self):
        logger.info(f"Start saving data to database")
        for file_index, reader in enumerate(self.readers):
            with transaction.atomic():
                try:
                    # why does here the set_status function not get hit but the last call in method does???
                    self.files[file_index].set_status(UploadFile.StatusCodes.SAVING)
                    logger.info(f"Saving data for file {file_index}/{len(self.readers)}")
                    self.battery_types.append(self.save_battery_type(reader.battery))
                    saved_battery = self.save_battery(reader.battery, self.battery_types[file_index], datetime.strptime(str(reader.data['CellTest0']['data']['date'].values[0]), "%Y-%m-%d").year)
                    self.batteries.append(saved_battery)
                    self.files[file_index].set_battery(saved_battery)
                    logger.info(f"Saved battery with id: {self.batteries[file_index].pk}")
                    self.datasets.append(self.save_dataset(reader.dataset, self.owner))
                    logger.info(f"Saved dataset with id: {self.datasets[file_index].pk}")

                    self.cellTests.append([])
                    self.cycling_tests.append([])
                    self.agg_datas.append([])
                    for test_index, cellTest_name in enumerate(reader.data):
                        reader.data[cellTest_name]['data'] = self.clean_cellTest(reader.data[cellTest_name]['data'], self.batteries[file_index], self.datasets[file_index], self.files[file_index])
                        self.cellTests[file_index].append(self.save_cellTest(reader.data[cellTest_name]['data']))
                        logger.info(f"Saved cell-test with id: {self.cellTests[file_index][test_index].pk}")

                        if 'CyclingRawData' in reader.data[cellTest_name]:
                            # index instead of testindex
                            self.cycling_tests[file_index].append(self.save_cyclingTest(file_index, test_index))
                            logger.info(f"Saved cycling-test with id: {self.cycling_tests[file_index][test_index].pk}")

                            self.agg_datas[file_index].append(self.save_aggData(file_index, test_index, reader.data[cellTest_name]['ErrorCodes']['data'], cellTest_name))
                            logger.info(f"Saved agg-data with id(s): {min(agg_data.pk for agg_data in self.agg_datas[file_index][test_index])}-{max(agg_data.pk for agg_data in self.agg_datas[file_index][test_index])}")

                            reader.data[cellTest_name]['CyclingRawData']['data'] = self.post_clean_cyclingRawData(file_index, test_index, cellTest_name)

                            self.save_cyclingRawData(file_index, cellTest_name)
                            logger.info("Saved cycling raw data")
                    self.files[file_index].set_status()
                except Exception as e:
                    logger.error(f"Error in file nr {file_index}/{len(self.readers)}: \n{e}")
                    transaction.on_commit(lambda: self.files[file_index].set_status(UploadFile.StatusCodes.ERROR, e))

    def clean_battery(self, index):
        renaming_attributes = ["format", "manufacturer", "nominal_voltage", "max_voltage", "min_voltage", "format_type"]
        df_battery = self.readers[index].battery
        if not set(renaming_attributes).issubset(df_battery.columns):
            missing_attributes = set(renaming_attributes) - set(df_battery.columns)
            self.warnings.append(f'Missing attribute(s) for renaming columns {missing_attributes} in battery-dataset')
            raise AttributeError(f'Missing attribute(s) for renaming columns {missing_attributes} in battery-dataset')
        df_battery = df_battery.rename(
            columns={"format": "content_object", "manufacturer": "supplier", "nominal_voltage": "vnom",
                     "max_voltage": "vmax", "min_voltage": "vmin"})
        df_battery['private'] = False
        default_owner, created = Organisation.objects.get_or_create(settings.PUBLIC_DATA_ADMIN_ORG_NAME)
        df_battery['owner'] = default_owner
        df_battery = df_battery.replace("", np.nan)
        df_battery.fillna(value=np.nan, axis='columns', inplace=True)
        df_battery = df_battery.where(pd.notnull(df_battery), None)
        if 'chemical_type_anode' in df_battery.columns:
            df_battery['chemical_type_anode'] = df_battery['chemical_type_anode'].apply(
                lambda x: helper.get_or_create_chemicaltype(shortname=x.replace(' ', '')))
            if 'anode_proportions' in df_battery.columns:
                df_battery['anode_proportions'] = df_battery['anode_proportions'].apply(
                    lambda x: helper.get_or_create_proportion(string=x))
        df_battery['chemical_type_cathode'] = df_battery['chemical_type_cathode'].apply(
            lambda x: helper.get_or_create_chemicaltype(shortname=x.replace(' ', '')))
        if 'cathode_proportions' in df_battery.columns:
            df_battery['cathode_proportions'] = df_battery['cathode_proportions'].apply(
                lambda x: helper.get_or_create_proportion(string=x))
        df_battery['supplier'] = df_battery['supplier'].apply(lambda x: helper.get_or_create_supplier(name=x))
        df_battery['content_object'] = df_battery[['content_object', 'format_type']].apply(
            lambda x: helper.get_battery_content_object(*x), axis=1)
        df_battery.drop(columns=list(set(df_battery.columns) - set(
            extractorModels.Battery().allowed_fields() + extractorModels.BatteryType().allowed_fields())), inplace=True)
        if not set(extractorModels.Battery.required_fields).issubset(df_battery.columns):
            missing_attributes = set(extractorModels.Battery().required_fields) - set(df_battery.columns)
            self.warnings.append(f'Missing required attribute(s): {missing_attributes} in battery-dataset')
            raise AttributeError(f'Missing required attribute(s): {missing_attributes} in battery-dataset')
        return df_battery

    @staticmethod
    def save_battery_type(clean_df_battery):
        clean_df_battery_type = clean_df_battery.drop(columns=list(set(clean_df_battery.columns) - set(extractorModels.BatteryType().allowed_fields())))
        return helper.get_or_create_battery_type(clean_df_battery_type)

    @staticmethod
    def save_battery(df_battery, saved_battery_type, year):
        df_battery['battery_type'] = saved_battery_type
        col_to_del = list(set(df_battery.columns) - set(extractorModels.Battery().allowed_fields()))
        col_to_del.remove('battery_type')
        df_battery.drop(columns=col_to_del, inplace=True)
        # TODO: check if cast is possible without iterating through df
        for entry in df_battery.T.to_dict().values():
            return Battery(**entry).save(year)

    def clean_dataset(self, df_dataset):
        # TODO: assign user if exist in df
        df_dataset = df_dataset.replace("", np.nan)
        df_dataset.fillna(value=np.nan, axis='columns', inplace=True)
        df_dataset = df_dataset.where(pd.notnull(df_dataset), None)
        df_dataset.drop(columns=list(set(df_dataset.columns) - set(extractorModels.Dataset().allowed_fields())), inplace=True)
        if not set(extractorModels.Dataset.required_fields).issubset(df_dataset.columns):
            missing_attributes = set(extractorModels.Dataset.required_fields) - set(df_dataset.columns)
            self.warnings.append(f'Missing required attribute(s): {missing_attributes} in dataset-dataset')
            raise AttributeError(f'Missing required attribute(s): {missing_attributes} in dataset-dataset')
        return df_dataset

    @staticmethod
    def save_dataset(df_dataset, owner):
        df_dataset['owner'] = owner
        return helper.get_or_create_dataset(df_dataset)

    def clean_cellTest(self, df_cellTest, saved_battery, saved_dataset, file):
        df_cellTest['battery'] = saved_battery
        df_cellTest['dataset'] = saved_dataset
        df_cellTest['file'] = file
        df_cellTest = df_cellTest.replace("", np.nan)
        df_cellTest.fillna(value=np.nan, axis='columns', inplace=True)
        df_cellTest = df_cellTest.where(pd.notnull(df_cellTest), None)
        df_cellTest.drop(columns=list(set(df_cellTest.columns) - set(extractorModels.CellTest().allowed_fields())), inplace=True)
        if not set(extractorModels.CellTest.required_fields).issubset(df_cellTest.columns):
            missing_attributes = set(extractorModels.CellTest.required_fields) - set(df_cellTest.columns)
            self.warnings.append(f'Missing required attribute(s): {missing_attributes} in celltest-dataset')
            raise AttributeError(f'Missing required attribute(s): {missing_attributes} in celltest-dataset')
        return df_cellTest

    @staticmethod
    def save_cellTest(df_cellTest):
        for entry in df_cellTest.T.to_dict().values():
            return CellTest(**entry).save()
    
    def save_cyclingTest(self, file_index, test_index=0):
        return super(Hdf5Extractor, self).save_cyclingTest(file_index, test_index)

    def clean_cyclingRawData(self, df_cyclingRawData, df_error_codes):
        df_cyclingRawData['timestamp_utc'] = pd.to_datetime(df_cyclingRawData['timestamp_utc'])
        df_cyclingRawData['timestamp_utc'] = df_cyclingRawData['timestamp_utc'].fillna(pd.Timestamp.min)
        df_cyclingRawData = df_cyclingRawData.where(pd.notnull(df_cyclingRawData), None)
        df_cyclingRawData = df_cyclingRawData.rename(columns={"timestamp_utc": "time"})
        df_cyclingRawData['cycle_id'] = df_cyclingRawData['cycle_id'].astype('int')
        df_cyclingRawData['step_flag'] = df_cyclingRawData['step_flag'].astype('int')
        df_cyclingRawData = df_cyclingRawData.replace("", np.nan)
        df_cyclingRawData.fillna(value=np.nan, axis='columns', inplace=True)
        df_cyclingRawData = df_cyclingRawData.where(pd.notnull(df_cyclingRawData), None)
        df_cyclingRawData.drop(columns=list(set(df_cyclingRawData.columns) - set(extractorModels.CyclingRawData().allowed_fields())), inplace=True)
        # close cycle_id gaps
        helper.close_cycle_gaps(df_cyclingRawData, df_error_codes)

        return df_cyclingRawData

    def save_aggData(self, file_index, test_index, df_error_codes=pd.DataFrame(), additive=None):
        return super(Hdf5Extractor, self).save_aggData(file_index, test_index, df_error_codes, additive)

    def post_clean_cyclingRawData(self, file_index, test_index, cellTest_name):
        return super(Hdf5Extractor, self).post_clean_cyclingRawData(file_index, test_index, cellTest_name)

    def save_cyclingRawData(self, index, cellTest_name):
        return super(Hdf5Extractor, self).save_cyclingRawData(index, cellTest_name)
