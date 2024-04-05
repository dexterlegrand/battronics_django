from django.db import connection, transaction

from django.db.models import Max
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver

from abd_database.models import CellTest, CyclingTest, Dataset, Battery


@receiver(pre_delete, sender=CellTest)
@transaction.atomic
def pre_cleanup_cycle_offset(sender, **kwargs):
    """Adjusts cycle_offset when deleting a test

        When a CellTest is deleted, the cycle_offset for related tests will be updated

    Args:
        sender:
        **kwargs:
    """

    # TODO: Make tests for this function

    if sender == CellTest:

        t = kwargs['instance'].cyclingtest_test_type.aggdata_set.filter(
            cycling_test=kwargs['instance'].cyclingtest_test_type).aggregate(Max('end_time'))['end_time__max']

        if t is not None:
            # gets all cycle_id's from battery where time is later than last timestamp in deleting celltest
            sql = f'''SELECT DISTINCT(cyclingtest.id)
                FROM public.abd_database_battery as battery
                INNER JOIN public.abd_database_celltest as celltest on battery.id=celltest.battery_id
                INNER JOIN public.abd_database_cyclingtest as cyclingtest on celltest.id=cyclingtest."cellTest_id"
                INNER JOIN public.abd_database_aggdata as aggdata on cyclingtest.id=aggdata."cycling_test_id"
                INNER JOIN public.abd_database_cyclingrawdata as rawdata on aggdata.id=rawdata.agg_data_id
                WHERE battery.id={kwargs['instance'].cyclingtest_test_type.cellTest.battery.id} AND time>'{t}'
                ORDER BY cyclingtest.id ASC'''

            cycletest_ids = None
            with connection.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchall()
                if result:
                    cycletest_ids = [x[0] for x in result]

        else:
            # if time query returns none no relevant tests can be selected
            cycletest_ids = []

        cycle_offset = kwargs['instance'].cyclingtest_test_type.aggdata_set.count()

        # subtracts the length of the deleting test from the offset from all tests after the deleting one.
        if cycletest_ids:
            for id in cycletest_ids:
                cycletest = CyclingTest.objects.get(pk=id)
                cycletest.cycle_offset = cycletest.cycle_offset - cycle_offset
                cycletest.save(update_fields=['cycle_offset'])


@receiver(post_save, sender=Dataset)
def sync_privacy_dataset_battery(sender, instance, **kwargs):
    """Update battery private field according to data set settings

    If private field of dataset is updated all associated batteries will be updated

    Args:
        instance: Instance of dataset that has been saved
        sender: Dataset model class
    """
    batts = Battery.objects.filter(cell_test__in=CellTest.objects.filter(dataset=instance))

    for battery in batts:
        if battery.private != instance.private:
            battery.private = instance.private
            battery.save(update_fields=["private"])
