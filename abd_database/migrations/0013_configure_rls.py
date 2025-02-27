# Generated by Django 4.0.4 on 2023-09-12 13:01

from django.db import migrations


# TODO: could be worth to implement a function that this is not enforced if system is setup as a single tenant system

def activate_row_level_security(table: str):
    """Generates SQL code to activate RLS

    Args:
        table: name of table to activate RLS for

    Returns: SQL code as string to activate RLS

    """
    return f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY; " \
           f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"


sql_policy_dataset_select = "CREATE POLICY owner_access ON abd_database_dataset FOR SELECT " \
                            "USING ((owner_id::TEXT = current_setting('abd.active_tenant')) OR (private = False) " \
                            "OR (id::TEXT = current_setting('abd.change_owner_battid')::TEXT));"

sql_policy_dataset_insert = "CREATE POLICY owner_insert ON abd_database_dataset FOR INSERT " \
                            "WITH CHECK (owner_id::TEXT = current_setting('abd.active_tenant'));"

sql_policy_dataset_update = "CREATE POLICY owner_update ON abd_database_dataset FOR UPDATE " \
                            "USING (owner_id::TEXT = current_setting('abd.active_tenant')) " \
                            "WITH CHECK ((owner_id::TEXT = current_setting('abd.active_tenant')) " \
                            "OR (id::TEXT = current_setting('abd.change_owner_battid')::TEXT));"

sql_policy_dataset_delete = "CREATE POLICY owner_delete ON abd_database_dataset FOR DELETE " \
                            "USING (owner_id::TEXT = current_setting('abd.active_tenant'));"

# SELECT allowed for owned and public data, INSERT, UPDATE, DELETE only allowed for owned data
sql_policy_celltest_select = "CREATE POLICY owner_access ON abd_database_celltest FOR SELECT " \
                             "USING (dataset_id IN (SELECT id FROM abd_database_dataset));"

sql_policy_celltest_update = f"""
CREATE POLICY owner_access_update ON abd_database_celltest
FOR UPDATE
USING (dataset_id IN (SELECT id FROM abd_database_dataset WHERE (
owner_id::TEXT = current_setting('abd.active_tenant'))));
"""

sql_policy_celltest_insert = f"""
CREATE POLICY owner_access_insert ON abd_database_celltest
FOR INSERT
WITH CHECK (dataset_id IN (SELECT id FROM abd_database_dataset WHERE (
owner_id::TEXT = current_setting('abd.active_tenant'))))
"""

sql_policy_celltest_delete = "CREATE POLICY owner_access_del ON abd_database_celltest FOR DELETE " \
                             "USING (dataset_id IN (SELECT id FROM abd_database_dataset WHERE (owner_id::TEXT = " \
                             "current_setting('abd.active_tenant'))));"

# SELECT allowed for owned and public data, INSERT, UPDATE, DELETE only allowed for owned data
sql_policy_cyclingtest_select = f'CREATE POLICY owner_access_select ON abd_database_cyclingtest FOR SELECT ' \
                                f'USING ("cellTest_id" IN (SELECT id FROM abd_database_celltest));'

sql_policy_cyclingtest_update = f"""
CREATE POLICY owner_access_update ON abd_database_cyclingtest
FOR UPDATE
USING ("cellTest_id" IN (SELECT id FROM abd_database_celltest
WHERE dataset_id IN (SELECT id FROM abd_database_dataset
WHERE (owner_id::TEXT = current_setting('abd.active_tenant')))));
"""

sql_policy_cyclingtest_insert = f"""
CREATE POLICY owner_access_insert ON abd_database_cyclingtest
FOR INSERT
WITH CHECK ("cellTest_id" IN (SELECT id FROM abd_database_celltest
WHERE dataset_id IN (SELECT id FROM abd_database_dataset
WHERE (owner_id::TEXT = current_setting('abd.active_tenant')))));
"""

sql_policy_cyclingtest_delete = f'CREATE POLICY owner_delete ON abd_database_cyclingtest FOR DELETE ' \
                                f'USING ("cellTest_id" IN (SELECT id FROM abd_database_celltest ' \
                                f'WHERE dataset_id IN (SELECT id FROM abd_database_dataset ' + \
                                "WHERE (owner_id::TEXT = current_setting('abd.active_tenant')))));"

sql_policy_aggdata_select = f"""CREATE POLICY owner_access_select ON abd_database_aggdata FOR SELECT
                                USING ("cycling_test_id" IN (SELECT id FROM abd_database_cyclingtest));
                                """

sql_policy_aggdata_update = f"""
CREATE POLICY owner_access_update ON abd_database_aggdata
FOR UPDATE USING 
("cycling_test_id" IN (SELECT id FROM abd_database_cyclingtest
WHERE "cellTest_id" IN (SELECT id FROM abd_database_celltest
WHERE dataset_id IN (SELECT id FROM abd_database_dataset
WHERE (owner_id::TEXT = current_setting('abd.active_tenant'))))));
"""

sql_policy_aggdata_insert = f"""
CREATE POLICY owner_access_insert ON abd_database_aggdata 
FOR INSERT WITH CHECK 
("cycling_test_id" IN (SELECT id FROM abd_database_cyclingtest
WHERE "cellTest_id" IN (SELECT id FROM abd_database_celltest
WHERE dataset_id IN (SELECT id FROM abd_database_dataset
WHERE (owner_id::TEXT = current_setting('abd.active_tenant'))))));
"""

sql_policy_aggdata_delete = f'CREATE POLICY owner_delete ON abd_database_aggdata FOR DELETE ' \
                            f'USING ("cycling_test_id" IN (SELECT id FROM abd_database_cyclingtest ' \
                            f'WHERE "cellTest_id" IN (SELECT id FROM abd_database_celltest ' \
                            f'WHERE dataset_id IN (SELECT id FROM abd_database_dataset ' + \
                            "WHERE (owner_id::TEXT = current_setting('abd.active_tenant'))))));"


sql_policy_rawdata_select = f'CREATE POLICY owner_select ON abd_database_cyclingrawdata FOR SELECT ' \
                            f'USING ("agg_data_id" IN (SELECT id FROM abd_database_aggdata));'

sql_policy_rawdata_update = f'CREATE POLICY owner_update ON abd_database_cyclingrawdata FOR UPDATE ' \
                            f'WITH CHECK ("agg_data_id" IN (SELECT id FROM abd_database_aggdata ' \
                            f'WHERE "cycling_test_id" IN (SELECT id FROM abd_database_cyclingtest ' \
                            f'WHERE "cellTest_id" IN (SELECT id FROM abd_database_celltest ' \
                            f'WHERE dataset_id IN (SELECT id FROM abd_database_dataset ' + \
                            "WHERE (owner_id::TEXT = current_setting('abd.active_tenant')))))));"

sql_policy_rawdata_insert = f'CREATE POLICY owner_insert ON abd_database_cyclingrawdata FOR INSERT ' \
                            f'WITH CHECK ("agg_data_id" IN (SELECT id FROM abd_database_aggdata ' \
                            f'WHERE "cycling_test_id" IN (SELECT id FROM abd_database_cyclingtest ' \
                            f'WHERE "cellTest_id" IN (SELECT id FROM abd_database_celltest ' \
                            f'WHERE dataset_id IN (SELECT id FROM abd_database_dataset ' + \
                            "WHERE (owner_id::TEXT = current_setting('abd.active_tenant')))))));"

sql_policy_rawdata_delete = f'CREATE POLICY owner_delete ON abd_database_cyclingrawdata FOR DELETE ' \
                            f'USING ("agg_data_id" IN (SELECT id FROM abd_database_aggdata ' \
                            f'WHERE "cycling_test_id" IN (SELECT id FROM abd_database_cyclingtest ' \
                            f'WHERE "cellTest_id" IN (SELECT id FROM abd_database_celltest ' \
                            f'WHERE dataset_id IN (SELECT id FROM abd_database_dataset ' + \
                            "WHERE (owner_id::TEXT = current_setting('abd.active_tenant')))))));"


class Migration(migrations.Migration):
    dependencies = [
        ('abd_database', '0012_alter_dataset_owner'),
        ('abd_management', '0006_configure_rls'),
    ]

    operations = [
        migrations.RunSQL(sql=activate_row_level_security("abd_database_dataset")),
        migrations.RunSQL(sql=sql_policy_dataset_select),
        migrations.RunSQL(sql=sql_policy_dataset_insert),
        migrations.RunSQL(sql=sql_policy_dataset_update),
        migrations.RunSQL(sql=sql_policy_dataset_delete),
        migrations.RunSQL(sql=activate_row_level_security("abd_database_celltest")),
        migrations.RunSQL(sql=sql_policy_celltest_select),
        migrations.RunSQL(sql=sql_policy_celltest_update),
        migrations.RunSQL(sql=sql_policy_celltest_insert),
        migrations.RunSQL(sql=sql_policy_celltest_delete),
        migrations.RunSQL(sql=activate_row_level_security("abd_database_cyclingtest")),
        migrations.RunSQL(sql=sql_policy_cyclingtest_select),
        migrations.RunSQL(sql=sql_policy_cyclingtest_update),
        migrations.RunSQL(sql=sql_policy_cyclingtest_insert),
        migrations.RunSQL(sql=sql_policy_cyclingtest_delete),
        migrations.RunSQL(sql=activate_row_level_security("abd_database_aggdata")),
        migrations.RunSQL(sql=sql_policy_aggdata_delete),
        migrations.RunSQL(sql=sql_policy_aggdata_insert),
        migrations.RunSQL(sql=sql_policy_aggdata_update),
        migrations.RunSQL(sql=sql_policy_aggdata_select),
        migrations.RunSQL(sql=activate_row_level_security("abd_database_cyclingrawdata")),
        migrations.RunSQL(sql=sql_policy_rawdata_select),
        migrations.RunSQL(sql=sql_policy_rawdata_insert),
        migrations.RunSQL(sql=sql_policy_rawdata_update),
        migrations.RunSQL(sql=sql_policy_rawdata_delete)
    ]
