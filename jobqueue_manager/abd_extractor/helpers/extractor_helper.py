import logging
from string import digits
import pandas as pd
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, ValidationError
from django.db.models import Q

from abd_database.models import CylinderFormat, PrismaFormat, Dataset, Proportion, ChemicalType, Supplier, BatteryType
from jobqueue_manager.abd_extractor.extractors import baseExtractor

logger = logging.getLogger(__name__)

remove_digits = str.maketrans('', '', digits)


def get_battery_content_object(name, format_type):
    if not format_type:
        raise ValueError("Format Type missing!")
    elif not name:
        if format_type == "cylindrical":
            return CylinderFormat.objects.get(name="UNKNOWN")
        else:
            return PrismaFormat.objects.filter(Q(name="UNKNOWN") & Q(format_type=format_type)).get()
    content_object = CylinderFormat.objects.filter(Q(name__iexact=name) & Q(format_type=format_type))
    if len(content_object) == 1:
        return content_object[0]
    elif len(content_object) > 1:
        raise MultipleObjectsReturned
    else:
        content_object = PrismaFormat.objects.filter(Q(name__iexact=name) & Q(format_type=format_type))
        if len(content_object) == 1:
            return content_object[0]
        elif len(content_object) > 1:
            raise MultipleObjectsReturned
        else:
            raise ObjectDoesNotExist(f"No '{format_type}' format with name '{name}' exists!")


def get_or_create_dataset(clean_df_dataset):
    try:
        dataset = Dataset.objects.get(name=clean_df_dataset['name'].values[0], url=clean_df_dataset['url'].values[0], doi=clean_df_dataset['doi'].values[0], license=clean_df_dataset['license'].values[0], authors=clean_df_dataset['authors'].values[0], organisation=clean_df_dataset['organisation'].values[0], owner=clean_df_dataset['owner'].values[0])
    except Dataset.DoesNotExist:
        for entry in clean_df_dataset.T.to_dict().values():
            dataset = Dataset(**entry).save()
    finally:
        return dataset


def get_or_create_proportion(string):
    try:
        proportion = Proportion.objects.get(proportions=string)
    except Proportion.DoesNotExist:
        try:
            Proportion(proportions=string).full_clean()
            proportion = Proportion.objects.create(proportions=string)
            message = f"Proportion {proportion.proportions} has automatically been created."
            baseExtractor.warnings.append(message)
            logger.warning(message)
        except ValidationError:
            message = f"Proportion {string} does not give 100%</br>Proportion is not saved"
            baseExtractor.warnings.append(message)
            logger.warning(message)
            proportion = None
    finally:
        return proportion


def get_or_create_chemicaltype(shortname):
    chemicaltypes = ChemicalType.objects.filter(Q(shortname__iexact=shortname) | Q(synonyms__contains=[shortname]))
    if len(chemicaltypes) == 1:
        return chemicaltypes[0]
    elif len(chemicaltypes) > 1:
        raise MultipleObjectsReturned
    else:
        chemicaltype = ChemicalType.objects.create(shortname=shortname)
        message = f"{chemicaltype.shortname} has automatically been created</br>Please complete information in ChemicalType form!"
        baseExtractor.warnings.append(message)
        logger.warning(message)
        return chemicaltype


def get_or_create_supplier(name):
    if not name:
        return Supplier.objects.get(pk=1)
    else:
        try:
            supplier = Supplier.objects.get(name__iexact=name)
        except Supplier.DoesNotExist:
            supplier = Supplier.objects.create(name=name)
            message = f"{supplier.name} has automatically been created</br>Please complete information in Supplier form!"
            baseExtractor.warnings.append(message)
            logger.warning(message)
        finally:
            return supplier


def get_or_create_battery_type(clean_df_battery_type):
    if not clean_df_battery_type['specific_type'].values[0]:
        clean_df_battery_type['specific_type'] = "UNKNOWN"
    try:
        if 'cathode_proportions' in clean_df_battery_type:
            battery_type = BatteryType.objects.get(specific_type=clean_df_battery_type['specific_type'].values[0], theoretical_capacity=clean_df_battery_type['theoretical_capacity'].values[0], chemical_type_cathode=clean_df_battery_type['chemical_type_cathode'].values[0], object_id=clean_df_battery_type['content_object'].values[0].pk, content_type=ContentType.objects.get_for_model(clean_df_battery_type['content_object'].values[0]), supplier=clean_df_battery_type['supplier'].values[0], cathode_proportions=clean_df_battery_type['cathode_proportions'].values[0])
        else:
            battery_type = BatteryType.objects.get(specific_type=clean_df_battery_type['specific_type'].values[0], theoretical_capacity=clean_df_battery_type['theoretical_capacity'].values[0], chemical_type_cathode=clean_df_battery_type['chemical_type_cathode'].values[0], object_id=clean_df_battery_type['content_object'].values[0].pk, content_type=ContentType.objects.get_for_model(clean_df_battery_type['content_object'].values[0]), supplier=clean_df_battery_type['supplier'].values[0], cathode_proportions=None)
        logger.info(f'Found existing battery-type with id: {battery_type.pk}')
    except BatteryType.DoesNotExist:
        for entry in clean_df_battery_type.T.to_dict().values():
            battery_type = BatteryType(**entry).save()
        logger.info(f'Saved new battery-type with id: {battery_type.pk}')
    except Exception as e:
        logger.error(f'Error while getting or creating battery-type: {e}')
    finally:
        return battery_type


def get_nbr_of_groups(root):
    nbr_cycles = 0
    nbr_eis = 0
    for group in root._v_groups:
        if str(group).lower().translate(remove_digits) == "cyclingrawdata":
            nbr_cycles += 1
        elif str(group).lower().translate(remove_digits) == "eis":
            nbr_eis += 1
        # possible with python version 3.10+
        # match str(group._v_name).lower().translate(remove_digits):
        #     case "cyclingrawdata":
        #         nbr_cycles += 1
        #     case "eis":
        #         nbr_eis += 1
    return nbr_cycles, nbr_eis


# def close_cycle_gaps(df_cyclingRawData, df_error_codes):
#     deltas = df_cyclingRawData['cycle_id'].diff()[1:]  # todo FutureWarning: The behavior of `series[i:j]` with an integer-dtype index is deprecated. In a future version, this will be treated as *label-based* indexing, consistent with e.g. `series[i]` lookups. To retain the old behavior, use `series.iloc[i:j]`. To get the future behavior, use `series.loc[i:j]`
#     gaps = deltas[deltas > 1]
#     gap_tuples = zip(gaps.index.values, gaps.values)
#     for gap in gap_tuples:
#         # if df_error_codes.empty or gap[0] not in df_error_codes['cycle_id']:
#         df_cyclingRawData.loc[df_cyclingRawData.index > (gap[0]-gap[1]-1), 'cycle_id'] = df_cyclingRawData.loc[df_cyclingRawData.index > (gap[0]-gap[1]-1), 'cycle_id'] - gap[1]-1
#
#     return df_cyclingRawData

# todo Implement df_errror_codes
def close_cycle_gaps(df_cyclingRawData, df_error_codes):
    groups_id = pd.factorize(df_cyclingRawData['cycle_id'])[0]+1
    df_cyclingRawData['cycle_id'] = groups_id

    return df_cyclingRawData
