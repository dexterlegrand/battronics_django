import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from abd_management.templatetags.user_tags import has_group
from django.conf import settings


def map_extractor_types(extractor_name, files, owner, argument_list=None):
    match extractor_name.upper():
        case "HDF5EXTRACTOR":
            from jobqueue_manager.abd_extractor.extractors.hdf5_extractor import Hdf5Extractor
            return Hdf5Extractor(files, owner)
        case "CSVEXTRACTOR":
            from jobqueue_manager.abd_extractor.extractors.csv_extractor import CsvExtractor
            return CsvExtractor(files, *argument_list)
        case "NDAEXTRACTOR":
            from jobqueue_manager.abd_extractor.extractors.nda_extractor import NdaExtractor
            return NdaExtractor(files, *argument_list)
        case "GAMRYEXTRACTOR":
            from jobqueue_manager.abd_extractor.extractors.gamry_extractor import GamryExtractor
            return GamryExtractor(files, *argument_list)
        case "BIOLOGICEXTRACTOR":
            from jobqueue_manager.abd_extractor.extractors.biologic_extractor import BiologicExtractor
            return BiologicExtractor(files, *argument_list)
        case "DIGATRONEXTRACTOR":
            from jobqueue_manager.abd_extractor.extractors.digatron_extractor import DigatronExtractor
            return DigatronExtractor(files, *argument_list)
        case _:
            raise ModuleNotFoundError("Could not find a matching extractor")


# TODO: periodically call cleanup method
def cleanup_fileupload():
    dir = os.path.join(settings.MEDIA_ROOT, 'uploadfiles')
    for file in os.listdir(dir):
        os.remove(os.path.join(dir, file))


def get_priority(user) -> int:
    if user.is_superuser:
        return UploadPriority.ADMIN.value
    elif has_group(user, "Premium_Uploader"):
        return UploadPriority.PREMIUM.value
    elif has_group(user, "Standard_Uploader"):
        return UploadPriority.STANDARD.value
    elif has_group(user, "ABD_Team"):
        return UploadPriority.TEAM.value

    # TODO: Find proper fix here
    return UploadPriority.ADMIN.value


class UploadPriority(Enum):
    ADMIN = 0
    PREMIUM = 1
    STANDARD = 2
    TEAM = 3


@dataclass
class QueueFile:
    """Class for keeping track of files in one item of the queue"""
    file_name: str
    file_size: int
    file_checksum: str
    file_size_ratio: float = field(default_factory=float)

    def __init__(self, file_name, size, checksum):
        self.file_name = file_name
        self.file_size = size
        self.file_checksum = checksum
        self.file_size_ratio = None


@dataclass
class QueueBatch:
    """Class for keeping track of one item in the queue"""
    id = int
    priority: int
    user: settings.AUTH_USER_MODEL
    files: List[QueueFile]
    batch_size: int
    batch_size_ratio: float
    active: bool = False

    def __init__(self, id, user, files=[]):
        self.id = id
        self.priority = get_priority(user)
        self.user = user
        self.batch_size = 0
        self.files = files
        if files:
            self.get_batch_size()
            self.calc_file_ratio()
        self.batch_size_ratio = None

    def get_batch_size(self):
        total = 0
        for file in self.files:
            total += file.file_size
        self.batch_size = total

    def calc_file_ratio(self):
        if self.batch_size != 0:
            for file in self.files:
                file.file_size_ratio = file.file_size / self.batch_size * 100

    def add_to_files(self, files):
        self.files.append(files)
        self.get_batch_size()
        self.calc_file_ratio()


@dataclass
class PublicQueue:
    """Class for keeping track of the queue"""
    total_size: int
    batches: List[QueueBatch] = field(default_factory=list)

    def __init__(self):
        self.batches = []
        self.total_size = 0

    def get_total_size(self):
        total = 0
        for batch in self.batches:
            total += batch.batch_size
        self.total_size = total
        return total

    def calc_batch_size_ratio(self):
        if self.total_size != 0:
            for batch in self.batches:
                batch.batch_size_ratio = batch.batch_size / self.total_size * 100

    def add_to_batches(self, batch):
        self.batches.append(batch)
        self.get_total_size()
        self.calc_batch_size_ratio()
        self.sort_by_priority()

    def sort_by_priority(self):
        if len(self.batches) > 0:
            self.batches = sorted(self.batches, key=lambda x: x.priority)

    def set_active(self):
        self.sort_by_priority()
        self.batches[0].active = True

    def remove_active(self):
        self.sort_by_priority()
        del self.batches[0]
        self.get_total_size()
