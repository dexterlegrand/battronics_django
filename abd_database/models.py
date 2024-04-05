import os
import re
from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from timescale.fields import TimescaleDateTimeField
from django.utils.translation import gettext_lazy as _
from abd_database.helpers.basicHelper import validate_proportions

from abd_database.managers import CyclingTestManager, AggDataManager, CyclingRawDataManager
from abd_database.templatetags.queue_tags import is_in_queue
from abd_management.models import Organisation, User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.db import models, connections, connection
from django.db.models import Q
from django.contrib.auth.models import Group, Permission

from timescale.db.models.models import TimescaleModel

from jobqueue_manager import manager
from jobqueue_manager.manager import get_queue_status


def get_type_limit(model_names):
    limits = Q()
    for name in model_names:
        limits.add(Q(app_label='abd_database', model=name), models.Q.OR)
    return limits


class ISONorm(models.Model):
    iso_number = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=32)
    height = models.FloatField()

    class Meta:
        abstract = True


class PrismaISONorm(ISONorm):
    width = models.FloatField()
    length = models.FloatField()


class CylinderISONorm(ISONorm):
    diameter = models.FloatField()


class ChemicalType(models.Model):
    shortname = models.CharField(max_length=16)
    synonyms = ArrayField(models.CharField(max_length=16), blank=True, null=True)
    name = models.CharField(max_length=256, blank=True, null=True)

    def __str__(self):
        return self.shortname


class Proportion(models.Model):
    proportions = models.CharField(max_length=16, primary_key=True, validators=[validate_proportions])

    # TODO: duplicate code in modelhelper, remove at one place
    @staticmethod
    def get_or_create(value):
        try:
            proportion = Proportion.objects.get(proportions=value)
        except Proportion.DoesNotExist:
            try:
                Proportion(proportions=value).full_clean()
                proportion = Proportion.objects.create(proportions=value)
                # message = f"Proportion {proportion.proportions} has automatically been created."
                # baseExtractor.warnings.append(message)
                # logger.warning(message)
            except ValidationError:
                # message = f"Proportion {string} does not give 100%</br>Proportion is not saved"
                # baseExtractor.warnings.append(message)
                # logger.warning(message)
                proportion = None
        finally:
            return proportion

    def __str__(self):
        return str(self.proportions)


class BatteryFormat(models.Model):
    name = models.CharField(max_length=256)
    format_type = models.CharField(max_length=32)
    height = models.FloatField(null=True, blank=True)

    # Iso Norm
    content_type = models.ForeignKey(ContentType, on_delete=models.RESTRICT, null=True, blank=True,
                                     limit_choices_to=get_type_limit(('prismaisonorm', 'cylinderisonorm')))
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        abstract = True
        unique_together = [['name', 'format_type']]

    def __str__(self):
        return self.name


class PrismaFormat(BatteryFormat):
    width = models.FloatField(null=True, blank=True)
    length = models.FloatField(null=True, blank=True)

    def get_metadata(self):
        metadata = "no metadata available"
        if self.height and self.width and self.width:
            # TODO: bugfix --> text cut off after whitespace
            metadata = f"""
            Lenght: {self.length},
            Width: {self.width},
            Height: {self.height}
            """
        return metadata


class CylinderFormat(BatteryFormat):
    diameter = models.FloatField()

    def get_metadata(self):
        metadata = "no metadata available"
        # TODO: bugfix --> text cut off after whitespace
        if self.height and self.diameter:
            metadata = f"""
            Diameter: {self.diameter},
            Height: {self.height}
            """
        return metadata


class Supplier(models.Model):
    name = models.CharField(max_length=256)
    city = models.CharField(max_length=256, blank=True, null=True)
    country = models.CharField(max_length=256, blank=True, null=True)

    def get_metadata(self):
        metadata = "no metadata available"
        if self.city and self.country:
            # TODO: bugfix --> text cut off after whitespace
            metadata = f"{self.city}, {self.country}"
        elif self.city:
            metadata = self.city
        elif self.country:
            metadata = self.country
        return metadata

    def __str__(self):
        return self.name


class BatteryType(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.RESTRICT, default=1)
    specific_type = models.CharField(max_length=256, default="UNKNOWN")
    theoretical_capacity = models.FloatField()
    chemical_type_cathode = models.ForeignKey(ChemicalType, on_delete=models.RESTRICT,
                                              related_name="chemical_type_cathode")
    cathode_proportions = models.ForeignKey(Proportion, on_delete=models.RESTRICT, null=True, blank=True)
    # BatteryFormat
    content_type = models.ForeignKey(ContentType, on_delete=models.RESTRICT,
                                     limit_choices_to=get_type_limit(('prismaformat', 'cylinderformat')))
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(force_insert, force_update, using, update_fields)
        return self

    def get_chemtype_and_proportion(self):
        if self.cathode_proportions:
            return self.chemical_type_cathode.shortname + "_" + str(self.cathode_proportions)
        else:
            return self.chemical_type_cathode.shortname

    class Meta:
        unique_together = [
            ['supplier', 'specific_type', 'theoretical_capacity', 'content_type', 'object_id', 'cathode_proportions']]


class Battery(models.Model):
    name = models.CharField(max_length=128, editable=False, unique=True)
    prod_year = models.PositiveIntegerField(null=True, blank=True)
    chemical_type_anode = models.ForeignKey(ChemicalType, on_delete=models.RESTRICT, null=True, blank=True,
                                            related_name="chemical_type_anode")
    anode_proportions = models.ForeignKey(Proportion, on_delete=models.RESTRICT, null=True, blank=True)
    battery_type = models.ForeignKey(BatteryType, on_delete=models.RESTRICT, related_name='batteries')
    weight = models.FloatField()
    vnom = models.FloatField(null=True, blank=True)
    vmax = models.FloatField()
    vmin = models.FloatField()
    comments = models.CharField(max_length=1024, null=True, blank=True)
    owner = models.ForeignKey(Organisation, on_delete=models.RESTRICT)
    private = models.BooleanField(default=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.set_name()
        super().save(force_insert, force_update, using, update_fields)
        return self

    def set_name(self):
        self.name = f'{self.battery_type.supplier.name.split(" ", 1)[0]}_{self.battery_type.specific_type}_{str(self.prod_year)}_001'.upper().replace(' ', '')

        while True:
            with connections['admin'].cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM abd_database_battery WHERE name = %s", [self.name])
                count = cursor.fetchone()[0]
            if count == 0:
                return
            else:
                temp_postfix = self.name.split('_')[-1]
                if temp_postfix.isnumeric():
                    postfix = int(temp_postfix) + 1
                    self.name = re.sub('\_' + temp_postfix + "$", '', self.name) + "_" + f"{postfix:03}"
                else:
                    raise ValidationError("Oops something went wrong setting the battery name")

    def get_chemtype_and_proportion(self):
        if self.anode_proportions and self.chemical_type_anode:
            return self.chemical_type_anode.shortname + "_" + str(self.anode_proportions)
        elif self.chemical_type_anode:
            return self.chemical_type_anode.shortname
        else:
            return None

    def update_owner(self, new_owner):
        """Updates owner of a battery

        Args:
            new_owner: Instance of new owner
        """
        self.owner = new_owner
        with connection.cursor() as cursor:
            cursor.execute(f"SET abd.change_owner_battid = {self.id}")
            self.save(update_fields=["owner"])
            cursor.execute(f"SET abd.change_owner_battid = {None}")

    def __str__(self):
        return self.name


class Dataset(models.Model):
    name = models.CharField(max_length=256)
    url = models.CharField(max_length=512, blank=True, null=True)
    doi = models.CharField(max_length=512, blank=True, null=True)
    license = models.CharField(max_length=512, blank=True, null=True)
    authors = models.CharField(max_length=512, blank=True, null=True)
    organisation = models.CharField(max_length=256)
    owner = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    private = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = [['name', 'url', 'doi', 'license', 'authors', 'organisation']]

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        super().save(force_insert, force_update, using, update_fields)
        return self

    def update_owner(self, new_owner: Organisation):
        """Owner change of dataset and associated battery instances

        Returns:
            object: Dataset Instance
        """
        self.owner = new_owner
        batts = Battery.objects.filter(cell_test__in=CellTest.objects.filter(dataset=self))
        with connection.cursor() as cursor:
            cursor.execute(f"SET abd.change_owner_battid = {self.id}")
            self.save(update_fields=["owner"])
            cursor.execute(f"SET abd.change_owner_battid = {None}")

        for battery in batts:
            battery.update_owner(new_owner)

        return self

    def __str__(self):
        return self.name


class CellTest(models.Model):
    battery = models.ForeignKey(Battery, on_delete=models.CASCADE, db_column='battery_id',
                                related_name="cell_test")
    file = models.ForeignKey("abd_database.UploadFile", on_delete=models.RESTRICT)
    equipment = models.CharField(max_length=512, blank=True, null=True)
    date = models.DateField()
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE)

    # optional data --> implement later

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        # TODO: add custom trigger in migration
        if self.battery.owner != self.dataset.owner:
            raise ValidationError("Dataset and Battery do not have the same owner")
        super().save(force_insert, force_update, using, update_fields)
        return self

    def __str__(self):
        return f'{self.dataset.name}_{self.battery.name}_{self.pk}'


class TestType(models.Model):
    cellTest = models.OneToOneField(CellTest, on_delete=models.CASCADE, related_name='%(class)s_test_type')
    cycle_offset = models.IntegerField(default=0, blank=False, null=False)
    comments = models.CharField(max_length=512, null=True, blank=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(force_insert, force_update, using, update_fields)
        return self

    class Meta:
        abstract = True


class CyclingTest(TestType):
    objects = CyclingTestManager()

    def __str__(self):
        return f'Cycling_{self.cellTest.dataset.name}_{self.cellTest.date}_{self.pk}'


class EISTest(TestType):
    voltage = models.FloatField()
    temperature = models.FloatField()


class HPPCTest(TestType):
    def __str__(self):
        return f'HPPC_{self.cellTest.date}_{self.pk}'


class BaseAggData(models.Model):
    class ErrorCodes(models.IntegerChoices):
        MISSING_CYCLES = 1,
        UTC_GAP = 2,
        NO_REAL_CYCLE = 3,
        CYCLE_DELETED = 4,
        JUMP_IN_TIME = 5

    cycle_id = models.PositiveIntegerField()
    ambient_temperature = models.FloatField(null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    error_codes = ArrayField(models.IntegerField(choices=ErrorCodes.choices), blank=True, null=True)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(force_insert, force_update, using, update_fields)
        return self

    class Meta:
        abstract = True


class AggData(BaseAggData):
    cycling_test = models.ForeignKey(CyclingTest, on_delete=models.CASCADE)

    charge_capacity = models.FloatField(null=True, blank=True)
    discharge_capacity = models.FloatField(null=True, blank=True)
    efficiency = models.FloatField(null=True, blank=True)
    charge_c_rate = models.FloatField(null=True, blank=True)
    discharge_c_rate = models.FloatField(null=True, blank=True)
    min_voltage = models.FloatField()
    max_voltage = models.FloatField()

    objects = AggDataManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="charge_or_discharge",
                check=(Q(charge_capacity__isnull=False) & Q(charge_c_rate__isnull=False) & Q(
                    discharge_capacity__isnull=True) & Q(discharge_c_rate__isnull=True)) |
                      (Q(charge_capacity__isnull=True) & Q(charge_c_rate__isnull=True) & Q(
                          discharge_capacity__isnull=False) & Q(discharge_c_rate__isnull=False)) |
                      (Q(charge_capacity__isnull=False) & Q(charge_c_rate__isnull=False) & Q(
                          discharge_capacity__isnull=False) & Q(discharge_c_rate__isnull=False))
            )
        ]


class HPPCAggData(BaseAggData):
    hppc_test = models.ForeignKey(HPPCTest, on_delete=models.CASCADE)


class TestData(TimescaleModel):
    voltage = models.FloatField()
    cell_temperature = models.FloatField(blank=True, null=True)
    ambient_temperature = models.FloatField(blank=True, null=True)

    class Meta:
        abstract = True


class CyclingRawData(TestData):
    objects = CyclingRawDataManager()
    agg_data = models.ForeignKey(AggData, on_delete=models.CASCADE)

    cycle_id = models.PositiveIntegerField()
    step_flag = models.IntegerField()
    time_in_step = models.FloatField(null=True)
    current = models.FloatField()
    capacity = models.FloatField()
    energy = models.FloatField()

    def get_required_fields(self):
        # returning all required field names (null =! True)
        req_fields = [f.name for f in CyclingRawData._meta.get_fields() if not getattr(f, 'null', False) is True]
        if 'agg_data' in req_fields:  # req_field contain agg_data this need to be deleted
            req_fields.remove('agg_data')
        if 'id' in req_fields:  # req_field contain id this need to be deleted
            req_fields.remove('id')

        return req_fields

    def get_additional_fields(self):
        # returning additional field names (null == True)
        add_fields = [f.name for f in CyclingRawData._meta.get_fields() if getattr(f, 'null', False) is True]
        if 'agg_data' in add_fields:  # add_field contain agg_data this need to be deleted
            add_fields.remove('agg_data')
        if 'id' in add_fields:  # add_field contain id this need to be deleted
            add_fields.remove('id')

        return add_fields


class EISData(TestData):
    agg_data = models.ForeignKey(AggData, on_delete=models.CASCADE)
    frequency = models.FloatField()
    z_real = models.FloatField()
    z_im = models.FloatField()


class HPPCRawData(TestData):
    agg_data = models.ForeignKey(HPPCAggData, on_delete=models.CASCADE)
    cycle_id = models.PositiveIntegerField()
    step_flag = models.IntegerField()
    time_in_step = models.FloatField(null=True)
    current = models.FloatField()
    capacity = models.FloatField(null=True)
    energy = models.FloatField(null=True)


# TODO: Maybe add field for pulse id. ID for identifying the order of the pulses during one cycle
# TODO: Calculation for SOC. SOC field should then be mandatory
class ResistanceData(models.Model):
    hppc_agg_data = models.ForeignKey(HPPCAggData, on_delete=models.CASCADE)
    cycle_id = models.PositiveIntegerField()
    cell_temperature = models.FloatField(blank=True, null=True)
    ambient_temperature = models.FloatField(blank=True, null=True)
    soc = models.FloatField(blank=True, null=True)
    test_current = models.FloatField()
    resistance = models.FloatField()


class UploadBatch(models.Model):
    class ExtractorTypes(models.TextChoices):
        UNKNOWN = 'Unknown',
        # Only for intern
        # HDF5EXTRACTOR = 'Hdf5',
        NDAEXTRACTOR = 'MTI/NEWARE',  # 'NdaExtractor'
        BIOLOGICEXTRACTOR = 'Biologic',
        DIGATRONEXTRACTOR = 'Digatron',
        CSVEXTRACTOR = 'CsvExtractor',
        # GAMRYEXTRACTOR = 'Gamry'

    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    extractor_type = models.CharField(max_length=32, default=ExtractorTypes.UNKNOWN)
    dataset = models.ForeignKey(Dataset, blank=True, null=True, on_delete=models.RESTRICT)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(force_insert, force_update, using, update_fields)
        return self

    def check_for_duplicates(self):
        """
        Checks if there are any successfully uploaded files in the database with the same checksum
        @return: returns list of tuples with the primary key of the uploaded file and a list of the primary keys of the related duplicated files
        [(uploaded_file.pk, [duplicate0.pk, duplicate1.pk, duplicate2.pk, ...]), (...), ...]
        """
        files = self.uploadfile_set.all()
        duplicates_tuples_list = []
        for uploaded_file in files:
            duplicates = uploaded_file.get_duplicates()
            if duplicates:
                duplicates_tuples_list.append((uploaded_file.pk, duplicates))

        return duplicates_tuples_list

    def check_for_duplicates_in_queue(self):
        """
        Checks if there are uploaded files with the same checksum in the queue and returns a list of filenames
        @return: returns list of tuples with the primary key of the uploaded file and list with filenames of duplicates found in the queue
        """
        files = self.uploadfile_set.all()
        duplicates_tuples_list = []
        for uploaded_file in files:
            duplicates = uploaded_file.get_duplicates_in_queue()
            if duplicates:
                duplicates_tuples_list.append((uploaded_file.pk, duplicates))

        return duplicates_tuples_list

    def get_duplicate_batteries_from_database(self):
        duplicat_batteries = []
        files = self.uploadfile_set.all()
        if files:
            queries = [Q(file_name=file.file_name) & Q(kb=file.kb) for file in files]
            query = queries.pop()
            for item in queries:
                query |= item
            uploadfiles = UploadFile.objects.filter(query)
            for file in uploadfiles:
                if hasattr(file, 'battery'):
                    duplicat_batteries.append(file.battery)
        return duplicat_batteries

    def delete_files(self):
        for file in self.uploadfile_set.all():
            if not file.is_deleted:
                file.delete_file()

    def __hash__(self):
        hash_string = ""
        for file in self.uploadfile_set.all():
            hash_string += str(hash(file.file.name))
        return hash(hash_string)


class UploadFile(models.Model):
    # TODO: extend statuscodes with all possible errors and set it correctly
    class StatusCodes(models.TextChoices):
        INITIAL = 'INIT', _('Initial')
        EXTRACTING = 'EXTRACT', _('Extracting')
        CLEANING = 'CLEAN', _('Cleaning')
        PREPARED = 'PREPARED', _('Prepared')
        SAVING = 'SAVE', _('Saving')
        SUCCESSFUL = 'SUCCESS', _('Successful')
        ERROR = 'ERROR', _('Error')
        UNHANDLED = 'UNHANDLED', _('Unhandled')

    batch = models.ForeignKey(UploadBatch, on_delete=models.RESTRICT)
    battery = models.ForeignKey(Battery, on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to='uploadfiles')
    file_name = models.CharField(max_length=256)
    kb = models.PositiveIntegerField()
    status = models.CharField(max_length=24, choices=StatusCodes.choices, default=StatusCodes.INITIAL, null=False,
                              blank=False)
    error_details = models.TextField(blank=True, null=True)
    time = TimescaleDateTimeField(interval="1 day")
    is_deleted = models.BooleanField(default=False)
    forget = models.BooleanField(default=False)
    checksum = models.CharField(max_length=32, validators=[MinLengthValidator(32, 'Checksum has to be exact 32 long')],
                                editable=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="details_only_with_error",
                check=((Q(status__exact='ERROR') & Q(error_details__isnull=False)) | (
                        ~Q(status__exact='ERROR') & Q(error_details__isnull=True)))
            ),
            models.CheckConstraint(
                name="can_not_forget_if_successful",
                check=(Q(forget=False) | (Q(forget=True) & ~Q(status__exact='SUCCESS')))
            )
        ]

    def get_path(self):
        return self.file.path

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.checksum:
            from abd_database.helpers.modelHelper import get_checksum
            self.checksum = get_checksum(self.file)
        self.file_name = self.file.name
        super().save(force_insert, force_update, using, update_fields)

    def get_duplicates(self):
        """
        Filters the database for files with the same checksum and which are successfully uploaded.
        Casts 'result'(Queryset) to 'list_result'(List<int>)
        @return: returns a list of primary keys of the hdf5-entries with the same checksum
        """
        result = UploadFile.objects.filter(Q(checksum=self.checksum) & Q(status=self.StatusCodes.SUCCESSFUL)).values('pk')
        list_result = [entry['pk'] for entry in result]
        return list_result

    def get_duplicates_in_queue(self):
        """
        @return: returns a list of filenames of duplicate files found in the queue
        """
        files_in_queue = []
        [files_in_queue.extend(batch.files) for batch in manager.public_queue.batches]
        names_and_checksums_in_queue = [(file.file_name, file.file_checksum) for file in files_in_queue]
        return [item[0] for item in names_and_checksums_in_queue if item[1] == self.checksum]

    def delete_file(self):
        """
        deletes the original file from the fileserver if the upload was successful or older than 7 days
        """
        if (self.status == "SUCCESS" and not self.is_deleted) or (
                not self.is_deleted and (datetime.now() - self.time.replace(tzinfo=None)).days > 7):
            # TODO: see why file is not closed for csv
            if not self.file.closed:
                self.file.close()
            os.remove(self.file.path)
            self.is_deleted = True
            self.save(update_fields=['is_deleted'])

    def set_status(self, status=None, details=None):
        """
        Sets the status of the file if status is not yet set so successful
        Can only change the status if is not set to successful yet
        Initial status is only set when creating the entry as default value.
        @param status: Type of StatusCodes
        @param details: detailed description of the status (e.g.: "file does not exist", "format does not exist")
        """
        if self.status != self.StatusCodes.SUCCESSFUL:
            if status:
                if status is not self.StatusCodes.INITIAL:
                    self.status = status
                    self.error_details = None
                    if status is self.StatusCodes.ERROR:
                        if details:
                            self.error_details = details
                            if type(details) == OSError:
                                self.is_deleted = True
                        else:
                            # TODO: throw error, error_details are missing
                            pass
                else:
                    # TODO: throw error, can not set status to INITIAL
                    pass
            else:
                self.status = self.StatusCodes.SUCCESSFUL
        else:
            raise Exception("Can not set Status if file is already successful")

        self.save(update_fields=['status', 'error_details', 'is_deleted'])

    def set_forget(self):
        """
        Sets the forget-flag on the file to ignore this file.
        Can only forget if status is not already successful and if the file is not in the queue.
        """
        if (self.status != "SUCCESS" and self.status != "PROCESS") or (
                self.status == "PROCESS" and not is_in_queue(self.batch.id, get_queue_status())):
            self.forget = True
            self.save(update_fields=['forget'])
            self.delete_file()
        else:
            # TODO: throw error, can not forget if status is success or process
            pass

    def set_battery(self, battery):
        """
        Sets the battery-tag on the file to trace file in error-case.
        """
        # TODO: is check necessary or do i always want to set the battery regardless of the state
        if self.status != self.StatusCodes.SUCCESSFUL:
            self.battery = battery
            self.save(update_fields=['battery'])
