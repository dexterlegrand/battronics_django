from django.contrib.postgres.aggregates import ArrayAgg
import plotly.graph_objs as go
import pandas as pd
import seaborn as sns
from django.db import models as djangoModels
from django.db import connection
from django.apps import apps
import json

from django.db.models.functions import Round, Cast

from abd_database.helpers.basicHelper import round_c_rates


class CyclingTestManager(djangoModels.Manager):
    def get_cycling_tests_for_battery(self, battery):
        q = self.filter(cellTest__battery=battery).annotate(
            ave_temp=Round(
                Cast(djangoModels.Avg('aggdata__ambient_temperature'), output_field=djangoModels.FloatField()), 1),
            discharge_c_rates=ArrayAgg('aggdata__discharge_c_rate', distinct=True),
            charge_c_rates=ArrayAgg('aggdata__charge_c_rate', distinct=True))
        for result in q:
            result.discharge_c_rates = sorted(round_c_rates(result.discharge_c_rates))
            result.charge_c_rates = sorted(round_c_rates(result.charge_c_rates))
        return q

    def plot_cycles(self, cycles, as_dict=False):
        fig = go.Figure()
        df = pd.DataFrame(cycles.aggdata_set.all().values())
        if not df.empty:
            df['cycle_id'] = df['cycle_id'].apply(lambda x: x + cycles.cycle_offset)
            df = df.sort_values(by='cycle_id')

            max_value = max(abs(df['discharge_capacity'].max()), abs(df['charge_capacity'].max()))
            if max_value <= 1:
                df['discharge_capacity'] = df['discharge_capacity'].apply(lambda x: x * 1000)
                df['charge_capacity'] = df['charge_capacity'].apply(lambda x: x * 1000)
                unit = '(mAh)'
            else:
                unit = '(Ah)'

            fig.add_trace(go.Scatter(x=df.loc[:, 'cycle_id'],
                                     y=df.loc[:, 'charge_capacity'],
                                     mode='markers',
                                     name='Charge Capacity',
                                     showlegend=True)
                          )

            fig.add_trace(go.Scatter(x=df.loc[:, 'cycle_id'],
                                     y=df.loc[:, 'discharge_capacity'],
                                     mode='markers',
                                     name='Discharge Capacity',
                                     showlegend=True)
                          )

            fig.update_traces(marker=dict(size=12))
            fig.update_layout(xaxis_title='Cycle number',
                              yaxis_title='Capacity ' + unit,
                              height=400,
                              )
            if as_dict:
                return json.loads(fig.to_json())

            return fig.to_json()
        else:
            # TODO: errorhandling if dataframe is empty
            pass


class AggDataManager(djangoModels.Manager):

    def get_agg_data_for_battery(self, battery, field_list=None, cell_tests=None):
        # q = self.filter(cycling_test__cellTest__battery=battery).order_by('cycle_id')
        # q = q.annotate(start_date=djangoModels.Min('cyclingrawdata__time'))

        if field_list is None:
            fields = f"""
            "abd_database_aggdata"."id", "abd_database_aggdata"."cycling_test_id",
            "abd_database_aggdata"."cycle_id" + "abd_database_cyclingtest"."cycle_offset" as cycle_id, "abd_database_aggdata"."charge_capacity",
            "abd_database_aggdata"."discharge_capacity", "abd_database_aggdata"."efficiency",
            "abd_database_aggdata"."charge_c_rate", "abd_database_aggdata"."discharge_c_rate",
            "abd_database_aggdata"."ambient_temperature", "abd_database_aggdata"."error_codes"
            """
        else:
            fields = [f'"abd_database_aggdata"."{field}"' for field in field_list]
            fields = ", ".join(fields)


        # aggregationn over many entries (min(time)) very slow
        if cell_tests is None:
            SQL = f'SELECT {fields}' \
                  ' FROM "abd_database_aggdata" INNER JOIN "abd_database_cyclingtest" ON ' \
                  '("abd_database_aggdata"."cycling_test_id" = "abd_database_cyclingtest"."id") INNER JOIN ' \
                  '"abd_database_celltest" ON ("abd_database_cyclingtest"."cellTest_id" = "abd_database_celltest"."id") ' \
                  'WHERE "abd_database_celltest"."battery_id" = %s ORDER BY "abd_database_aggdata"."cycle_id" ASC'

            params = (battery,)

        else:
            SQL = f'SELECT {fields}' \
                  ' FROM "abd_database_aggdata" INNER JOIN "abd_database_cyclingtest" ON ' \
                  '("abd_database_aggdata"."cycling_test_id" = "abd_database_cyclingtest"."id") INNER JOIN ' \
                  '"abd_database_celltest" ON ("abd_database_cyclingtest"."cellTest_id" = "abd_database_celltest"."id") ' \
                  'WHERE ("abd_database_celltest"."battery_id" = %s AND "abd_database_cyclingtest"."cellTest_id" in %s) ORDER BY "abd_database_aggdata"."cycle_id" ASC'

            params = (battery, tuple(cell_tests))

        with connection.cursor() as cursor:
            cursor.execute(SQL, params)
            data_raw = cursor.fetchall()

        return data_raw


class CyclingRawDataManager(djangoModels.Manager):
    def capacity_vs_voltage_for_cycles(self, cycles, as_dict=False, api=False, field_list=None):

        if field_list is None:
            field_list = ["time", "voltage", "capacity", "step_flag", "agg_data_id"]

        fields = [f'"abd_database_cyclingrawdata"."{field}"' for field in field_list]
        fields = ", ".join(fields)

        if len(cycles) > 1:
            SQL = f"SELECT {fields} FROM abd_database_cyclingrawdata" \
                  f" WHERE agg_data_id IN {tuple(cycles)}"
        else:
            SQL = f"SELECT {fields} FROM abd_database_cyclingrawdata" \
                  f" WHERE agg_data_id={cycles[0]}"

        with connection.cursor() as cursor:
            cursor.execute(SQL)
            data_raw = cursor.fetchall()

        if api:
            return data_raw

        fig = go.Figure()
        # df = pd.DataFrame(self.filter(agg_data_id__in=cycles).values()).sort_values(by='time')
        df = pd.DataFrame(data_raw, columns=['time', 'voltage', 'capacity', 'step_flag', 'agg_data_id'])
        df.sort_values(by='time')

        color_list = sns.cubehelix_palette(len(cycles)).as_hex()

        # TODO: either check before iterating through selection or don't check at all
        # TODO: buggy implementation
        # max_value = abs(df_temp['capacity'].max())
        # if max_value <= 1:
        #     df_temp['capacity'] = df_temp['capacity'].apply(lambda x: x * 1000)
        #     unit = '(mAh)'
        # else:
        #     unit = '(Ah)'

        for i, cycle in enumerate(cycles):
            aggdata = apps.get_model('abd_database', 'aggdata').objects.get(pk=cycle)
            cycid = aggdata.cycle_id + aggdata.cycling_test.cycle_offset
            cycle_charge = (df['agg_data_id'] == cycle) & (df['step_flag'].isin([2, 3]))
            df_temp = df.loc[cycle_charge, :].sort_values(by='capacity')
            fig.add_trace(go.Scatter(x=df_temp.loc[:, 'capacity'],
                                     y=df_temp.loc[:, 'voltage'],
                                     mode='markers',
                                     name=f'{cycid}_Charge',
                                     showlegend=True,
                                     marker_color=color_list[i])
                          )

            cycle_discharge = (df['agg_data_id'] == cycle) & (df['step_flag'].isin([4]))
            df_temp = df.loc[cycle_discharge, :].sort_values(by='capacity')
            fig.add_trace(go.Scatter(x=df_temp.loc[:, 'capacity'].abs(),
                                     y=df_temp.loc[:, 'voltage'],
                                     mode='markers',
                                     name=f'{cycid}_Discharge',
                                     showlegend=True,
                                     marker_color=color_list[i])
                          )

        fig.update_traces(marker=dict(size=12))
        fig.update_layout(xaxis_title='Capacity (Ah)',
                          yaxis_title='Voltage (V)',
                          height=400
                          )
        if as_dict:
            return json.loads(fig.to_json())

        return fig.to_json()

    def get_data_for_battery(self, battery, field_list=None):

        # TODO check usage of ".objects.raw(SQL)"

        if field_list is None:
            field_list = ["id", "time", "voltage", "current", "capacity", "energy", "agg_data_id", "cycle_id",
                          "step_flag", "time_in_step", "cell_temperature", "ambient_temperature"]

        fields = [f'"abd_database_cyclingrawdata"."{field}"' for field in field_list]
        fields = ", ".join(fields)

        SQL = f"""
        SELECT {fields} FROM "abd_database_cyclingrawdata"
        INNER JOIN "abd_database_aggdata" ON ("abd_database_cyclingrawdata"."agg_data_id" = "abd_database_aggdata"."id")
        INNER JOIN "abd_database_cyclingtest" ON ("abd_database_aggdata"."cycling_test_id" = "abd_database_cyclingtest"."id")
        INNER JOIN "abd_database_celltest" ON ("abd_database_cyclingtest"."cellTest_id" = "abd_database_celltest"."id")
        WHERE "abd_database_celltest"."battery_id" = %s ORDER BY "abd_database_cyclingrawdata"."time" ASC
        """
        SQL = SQL.replace('"abd_database_cyclingrawdata"."cycle_id"',
                          '"abd_database_cyclingrawdata"."cycle_id" + "abd_database_cyclingtest"."cycle_offset" as cycle_id')

        params = (battery,)

        with connection.cursor() as cursor:
            cursor.execute(SQL, params)
            data_raw = cursor.fetchall()

        return data_raw
