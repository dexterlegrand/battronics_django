from abd_database.models import Battery, Dataset
from jobqueue_manager.abd_extractor.extractors.baseExtractor import BaseExtractor
from jobqueue_manager.abd_extractor.readers.biologic_reader import BiologicReader


class BiologicExtractor(BaseExtractor):  # todo may put a case sensitivity in base clas to take correct reader

    def __init__(self, files, battery: Battery, equipment: str, date, dataset: Dataset):
        self.battery: Battery = battery
        self.equipment: str = equipment
        self.date = date
        self.dataset: Dataset = dataset
        self.readers = [BiologicReader(file) for file in files]
        super(BiologicExtractor, self).__init__(files)
