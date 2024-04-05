import io

from abd_database.models import CyclingRawData

# TODO: Change naming to reflect use for cycling and HPPC data
def get_cyclingRawData_csv(df_cyclingRawData):
    """ Works for Cycling and for HPPC data"""
    df_cyclingRawData['agg_data'] = df_cyclingRawData['agg_data'].apply(lambda x: x.pk)
    df_cyclingRawData = df_cyclingRawData.rename(columns={"agg_data": "agg_data_id"})
    cyclingRawData_fields = []
    for field in CyclingRawData._meta.fields:
        cyclingRawData_fields.append(field.get_attname_column()[1])
    cyclingRawData_fields.remove('id')
    all_fields = set(cyclingRawData_fields)
    fields_in_data = set(df_cyclingRawData.columns.to_list())
    fields_to_load = list(all_fields & fields_in_data)

    # order columns
    df_cyclingRawData = df_cyclingRawData[fields_to_load]

    file = io.StringIO()
    df_cyclingRawData.to_csv(file, index=False, header=False, na_rep='None')
    file.seek(0)

    return file, tuple(df_cyclingRawData.columns.to_list())
