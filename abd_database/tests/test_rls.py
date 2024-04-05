from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone
from django.db.utils import ProgrammingError, DatabaseError
from django.db.models import ObjectDoesNotExist
from django.core.exceptions import ValidationError

from abd_database.models import Battery, BatteryType, Supplier, ChemicalType, Dataset, CellTest, UploadFile, \
    CyclingTest, AggData, CyclingRawData
from abd_management.models import Organisation, User
from abd_database.helpers.db import set_active_tenant

from django.conf import settings

initial = False


def create_initial_objects():
    set_active_tenant(1)
    # 0001_initial.py
    call_command('loaddata', 'abd_database/fixtures/data.json', verbosity=0)
    set_active_tenant(1)
    # 0005_uploadfile_remove_battery_file_remove_battery_name_and_more.py
    # Got changed in later version to raw-sql
    call_command('loaddata', 'abd_database/fixtures/dummy-entries.json', verbosity=0)


class RLSTestCase(TransactionTestCase):
    databases = {'default', 'admin'}

    ###################################################################################################################
    # Create-Statements
    def create_org_user_and_batterytype(self) -> None:
        print("create_org_user_and_batterytype\n")
        self.owner_org = Organisation(name="OwnerOrg")
        self.owner_org.save()
        self.other_org = Organisation(name="OtherOrg")
        self.other_org.save()
        self.public_org = Organisation.get_or_create(name=settings.PUBLIC_DATA_ADMIN_ORG_NAME)

        # Create users
        self.owner_user = User.objects.create_user(username="OwnerUser", password="12345", company=self.owner_org)
        self.other_user = User.objects.create_user(username="OtherUser", password="12345", company=self.other_org)

        # Create battery type
        self.default_battery_type = BatteryType.objects.create(supplier=Supplier.objects.all().first(),
                                                               theoretical_capacity=100,
                                                               chemical_type_cathode=ChemicalType.objects.all().first(),
                                                               content_type=ContentType.objects.get(
                                                                   model='prismaformat'), object_id=1)

    def create_public_battery(self, current_time, time_to_add):
        # Public Data
        set_active_tenant(self.public_org.id)
        # Create battery
        self.public_battery = Battery.objects.create(owner=self.public_org, battery_type=self.default_battery_type,
                                                     weight=100, vmax=4.2, vnom=3.7, vmin=3.0, prod_year=2010, private=False)
        # Create dataset
        self.public_dataset = Dataset.objects.create(name="PublicDataset", owner=self.public_org, private=False)
        # Create cell test
        self.public_celltest = CellTest.objects.create(battery=self.public_battery,
                                                       file=UploadFile.objects.all().first(), date=timezone.now(),
                                                       dataset=self.public_dataset)
        # Create cycling test
        self.public_cyclingtest = CyclingTest.objects.create(cellTest=self.public_celltest)
        # Create AggData
        self.public_aggdata = AggData.objects.create(cycling_test=self.public_cyclingtest, cycle_id=1,
                                                     start_time=current_time, end_time=current_time + time_to_add,
                                                     min_voltage=100, max_voltage=101, charge_capacity=10,
                                                     charge_c_rate=1)
        # Create CyclingRawData
        self.public_cyclingrawdatas = []
        self.public_cyclingrawdatas.append(
            CyclingRawData.objects.create(agg_data=self.public_aggdata, voltage=10, cycle_id=1, step_flag=1, current=1,
                                          capacity=1, energy=1, time=current_time))
        self.public_cyclingrawdatas.append(
            CyclingRawData.objects.create(agg_data=self.public_aggdata, voltage=10, cycle_id=1, step_flag=2, current=1,
                                          capacity=1, energy=1, time=current_time))
        self.public_cyclingrawdatas.append(
            CyclingRawData.objects.create(agg_data=self.public_aggdata, voltage=10, cycle_id=1, step_flag=3, current=1,
                                          capacity=1, energy=1, time=current_time))

    def create_owned_battery(self, current_time, time_to_add):
        # Owned Data
        set_active_tenant(self.owner_user.company_id)
        # Create battery
        self.owned_battery = Battery.objects.create(owner=self.owner_org, battery_type=self.default_battery_type,
                                                    weight=100, vmax=4.2, vnom=3.7, vmin=3.0, prod_year=2015, private=True)
        # Create datasets
        self.private_dataset_owner = Dataset.objects.create(name="PrivateDatasetOwner", owner=self.owner_org,
                                                            private=True)
        # Create cell tests
        self.owned_celltest = CellTest.objects.create(battery=self.owned_battery, file=UploadFile.objects.all().first(),
                                                      date=timezone.now(), dataset=self.private_dataset_owner)
        # Create cycling tests
        self.owned_cyclingtest = CyclingTest.objects.create(cellTest=self.owned_celltest)
        # Create AggData
        self.owned_aggdata = AggData.objects.create(cycling_test=self.owned_cyclingtest, cycle_id=1,
                                                    start_time=current_time, end_time=current_time + time_to_add,
                                                    min_voltage=100, max_voltage=101, charge_capacity=10,
                                                    charge_c_rate=1)
        # Create CyclingRawData
        self.owned_cyclingrawdatas = []
        self.owned_cyclingrawdatas.append(
            CyclingRawData.objects.create(agg_data=self.owned_aggdata, voltage=10, cycle_id=1, step_flag=1, current=1,
                                          capacity=1, energy=1, time=current_time))
        self.owned_cyclingrawdatas.append(
            CyclingRawData.objects.create(agg_data=self.owned_aggdata, voltage=10, cycle_id=1, step_flag=2, current=1,
                                          capacity=1, energy=1, time=current_time))
        self.owned_cyclingrawdatas.append(
            CyclingRawData.objects.create(agg_data=self.owned_aggdata, voltage=10, cycle_id=1, step_flag=3, current=1,
                                          capacity=1, energy=1, time=current_time))

    def create_other_battery(self, current_time, time_to_add):
        # Other Data
        set_active_tenant(self.other_user.company_id)
        # Create battery
        self.other_battery = Battery.objects.create(owner=self.other_org, battery_type=self.default_battery_type,
                                                    weight=100, vmax=4.2, vnom=3.7, vmin=3.0, prod_year=2020,
                                                    private=True)
        # Create datasets
        self.private_dataset_other = Dataset.objects.create(name="PrivateDatasetOther", owner=self.other_org,
                                                            private=True)
        # Create cell tests
        self.other_celltest = CellTest.objects.create(battery=self.other_battery, file=UploadFile.objects.all().first(),
                                                      date=timezone.now(), dataset=self.private_dataset_other)
        # Create cycling tests
        self.other_cyclingtest = CyclingTest.objects.create(cellTest=self.other_celltest)
        # Create AggData
        self.other_aggdata = AggData.objects.create(cycling_test=self.other_cyclingtest, cycle_id=1,
                                                    start_time=current_time, end_time=current_time + time_to_add,
                                                    min_voltage=100, max_voltage=101, charge_capacity=10,
                                                    charge_c_rate=1)
        # Create CyclingRawData
        self.other_cyclingrawdatas = []
        self.other_cyclingrawdatas.append(
            CyclingRawData.objects.create(agg_data=self.other_aggdata, voltage=10, cycle_id=1, step_flag=1, current=1,
                                          capacity=1, energy=1, time=current_time))
        self.other_cyclingrawdatas.append(
            CyclingRawData.objects.create(agg_data=self.other_aggdata, voltage=10, cycle_id=1, step_flag=2, current=1,
                                          capacity=1, energy=1, time=current_time))
        self.other_cyclingrawdatas.append(
            CyclingRawData.objects.create(agg_data=self.other_aggdata, voltage=10, cycle_id=1, step_flag=3, current=1,
                                          capacity=1, energy=1, time=current_time))

    def create_batteries(self) -> None:
        print("create_batteries\n")
        current_time = timezone.now()
        time_to_add = timezone.timedelta(hours=1)

        with connection.cursor() as cursor:
            cursor.execute(f"SET abd.change_owner_battid={None}")

        self.create_public_battery(current_time, time_to_add)
        self.create_owned_battery(current_time, time_to_add)
        self.create_other_battery(current_time, time_to_add)

    ####################################################################################################################
    # SetUp-Function

    def setUp(self) -> None:
        print("SetUp-Function:\n")
        global initial

        if initial:
            # recreates objects from migrations
            # required since TransactionTestCase truncates all tables after each test
            create_initial_objects()

        self.create_org_user_and_batterytype()
        self.create_batteries()
        initial = True

    ####################################################### BATTERY ###################################################
    ###################################################################################################################
    # Select-Statements-Tests
    def test_get_all_batteries_no_tenant(self):
        print("test_get_all_batteries_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        all_batteries = Battery.objects.all()
        # Should only return 1 entry, public Battery
        self.assertEqual(len(all_batteries), 1)
        # ID should be same
        self.assertEqual(all_batteries[0].id, self.public_battery.id)

    def test_get_all_batteries_tenant_1(self):
        print("test_get_all_batteries_tenant_1\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        all_batteries = Battery.objects.all()
        # Should return 2 entries, public and private owned Battery
        self.assertEqual(len(all_batteries), 2)
        # Check if the correct batteries are returned
        expected_battery_ids = [self.public_battery.id, self.owned_battery.id]
        self.assertIn(all_batteries[0].id, expected_battery_ids)
        self.assertIn(all_batteries[1].id, expected_battery_ids)

    def test_get_all_batteries_tenant_2(self):
        print("test_get_all_batteries_tenant_2\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        all_batteries = Battery.objects.all()
        # Should return 2 entries, public and private owned Battery
        self.assertEqual(len(all_batteries), 2)
        # Check if the correct batteries are returned
        expected_battery_ids = [self.public_battery.id, self.other_battery.id]
        self.assertIn(all_batteries[0].id, expected_battery_ids)
        self.assertIn(all_batteries[1].id, expected_battery_ids)

    ###################################################################################################################
    # Update-/Insert-Statements-Tests
    # Insert
    def test_create_public_battery_no_tenant(self):
        """Test if anonymous user can insert battery for public data admin

        Insert should not succeed as anonymous user can't to any write actions
        """
        print("test_create_public_battery_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Check number of batteries
        nbr_batteries_before = Battery.objects.all().count()
        with self.assertRaises(ProgrammingError) as context:
            new_public_battery = Battery.objects.create(owner=self.public_org, battery_type=self.default_battery_type,
                                                        weight=100, vmax=4.2, vnom=3.7, vmin=3.0, prod_year=2010)
        # Check number of batteries
        nbr_batteries_after = Battery.objects.all().count()
        self.assertEqual(nbr_batteries_before, nbr_batteries_after)

    def test_create_public_battery_wrong_tenant(self):
        """Test if other user than public admin can create battery for public admin

        Should fail since only public admin can manage data under its jurisdiction

        """
        print("test_create_public_battery_tenant_1\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Check number of batteries
        nbr_batteries_before = Battery.objects.all().count()

        with self.assertRaises(ProgrammingError) as context:
            new_public_battery = Battery.objects.create(owner=self.public_org, battery_type=self.default_battery_type,
                                                        weight=100, vmax=4.2, vnom=3.7, vmin=3.0, prod_year=2010)
        # Check number of batteries
        nbr_batteries_after = Battery.objects.all().count()
        self.assertEqual(nbr_batteries_before, nbr_batteries_after)

    def test_create_private_battery_wrong_tenant(self):
        print("test_create_private_battery_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Check number of batteries
        nbr_batteries_before = Battery.objects.all().count()
        # Create battery should fail
        with self.assertRaises(ProgrammingError) as context:
            Battery.objects.create(owner=self.owner_org, battery_type=self.default_battery_type, weight=100, vmax=4.2,
                                   vnom=3.7, vmin=3.0, prod_year=2015)
        # Check number of batteries
        nbr_batteries_after = Battery.objects.all().count()
        self.assertEqual(nbr_batteries_before, nbr_batteries_after)

    # Update
    def test_update_public_battery_no_tenant(self):
        print("test_update_public_battery_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get weight of public battery before update
        weight_before = self.public_battery.weight
        # Update some values in public battery, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.public_battery.weight = 200
            self.public_battery.save()
        # Get weight of public battery after update
        weight_after = Battery.objects.get(id=self.public_battery.id).weight
        # Check if weight is still the same
        self.assertEqual(weight_before, weight_after)

    def test_update_public_battery_wrong_tenant(self):
        print("test_update_public_battery_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get weight of public battery before update
        weight_before = self.public_battery.weight
        # Update some values in public battery, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.public_battery.weight = 200
            self.public_battery.save()
        # Get weight of public battery after update
        weight_after = Battery.objects.get(id=self.public_battery.id).weight
        # Check if weight is still the same
        self.assertEqual(weight_before, weight_after)

    def test_update_public_battery_correct_tenant(self):
        print("test_update_public_battery_correct_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Get weight of public battery before update
        weight_before = self.public_battery.weight
        # Update some values in public battery, should succeed
        weight_to_update = 200
        self.public_battery.weight = weight_to_update
        self.public_battery.save()
        # Get weight of public battery after update
        weight_after = Battery.objects.get(id=self.public_battery.id).weight
        # Check if weight got updated
        self.assertNotEqual(weight_before, weight_after)
        self.assertEqual(weight_to_update, weight_after)

    def test_update_private_battery_no_tenant(self):
        print("test_update_private_battery_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get weight of owned battery before update
        weight_before = self.owned_battery.weight
        # Update some values in owned battery, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.owned_battery.weight = 200
            self.owned_battery.save()
        # Get weight of owned battery after update
        # Set tenant to OwnerOrg for getting the correct battery
        set_active_tenant(self.owner_user.company_id)
        weight_after = Battery.objects.get(id=self.owned_battery.id).weight
        # Reset tenant to None
        set_active_tenant()
        # Check if weight is still the same
        self.assertEqual(weight_before, weight_after)

    def test_update_private_battery_wrong_tenant(self):
        print("test_update_private_battery_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get weight of owned battery before update
        weight_before = self.owned_battery.weight
        # Update some values in owned battery, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.owned_battery.weight = 200
            self.owned_battery.save()
        # Get weight of owned battery after update
        # Set tenant to OwnerOrg for getting the correct battery
        set_active_tenant(self.owner_user.company_id)
        weight_after = Battery.objects.get(id=self.owned_battery.id).weight
        # Reset tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Check if weight is still the same
        self.assertEqual(weight_before, weight_after)

    def test_update_private_battery_correct_tenant(self):
        print("test_update_private_battery_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Get weight of owned battery before update
        weight_before = self.owned_battery.weight
        # Update some values in owned battery, should succeed
        weight_to_update = 200
        self.owned_battery.weight = weight_to_update
        self.owned_battery.save()
        # Get weight of owned battery after update
        weight_after = Battery.objects.get(id=self.owned_battery.id).weight
        # Check if weight got updated
        self.assertNotEqual(weight_before, weight_after)
        self.assertEqual(weight_to_update, weight_after)

    def test_update_private_battery_change_owner_no_tenant(self):
        print("test_update_private_battery_change_owner_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Update owner of owned battery to PublicOrg, should fail
        with self.assertRaises(DatabaseError) as context:
            self.owned_battery.update_owner(self.public_org)
        # Get owner of battery after update
        # Set tenant to OwnerOrg for getting the correct battery
        set_active_tenant(self.owner_user.company_id)
        owner_after = Battery.objects.get(id=self.owned_battery.id).owner
        # Check if owner is still the same
        self.assertEqual(self.owner_org, owner_after)

    def test_update_private_battery_change_owner_wrong_tenant(self):
        print("test_update_private_battery_change_owner_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get owner of owned battery before update
        owner_before = self.owned_battery.owner
        # Update owner of owned battery to OtherOrg, should fail
        with self.assertRaises(DatabaseError) as context:
            self.owned_battery.update_owner(self.other_org)
        # Get owner of owned battery after update
        # Set tenant to OwnerOrg for getting the correct battery
        set_active_tenant(self.owner_user.company_id)
        owner_after = Battery.objects.get(id=self.owned_battery.id).owner
        # Check if owner is still the same
        self.assertEqual(owner_before.id, owner_after.id)
        # Reset tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)

    def test_update_private_battery_change_owner_correct_tenant(self):
        print("test_update_private_battery_change_owner_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_org.id)
        print(f"Owner Org ID: {self.owner_org.id}")
        # Get owner of owned battery before update
        owner_id_before = self.owned_battery.owner.id
        print(f"Owner ID before: {owner_id_before}")
        # Update owner of owned battery to PublicOrg, should succeed
        self.owned_battery.update_owner(self.other_org)
        print(f"Owner ID to be updated: {self.other_org.id}")
        # Get owner of owned battery after update
        set_active_tenant(self.other_org.id)
        owner_id_after = Battery.objects.get(id=self.owned_battery.id).owner.id
        print(f"Owner ID after: {owner_id_after}")
        # Check if owner got updated
        self.assertNotEqual(owner_id_before, owner_id_after)

    # if update includes a WHERE the SELECT policy is also checked!
    def test_update_public_battery_change_owner_no_tenant(self):
        print("test_update_public_battery_change_owner_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get owner of public battery before update
        owner_before = self.public_battery.owner
        # Update owner of public battery to PublicOrg, should fail
        with self.assertRaises(DatabaseError) as context:
            self.public_battery.update_owner(self.public_org)
        # Get owner of public battery after update
        owner_after = Battery.objects.get(id=self.public_battery.id).owner
        # Check if owner is still the same
        self.assertEqual(owner_before.id, owner_after.id)

    def test_update_public_battery_change_owner_wrong_tenant(self):
        print("test_update_public_battery_change_owner_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get owner of public battery before update
        owner_before = self.public_battery.owner
        # Update owner of public battery to PublicOrg, should fail
        with self.assertRaises(DatabaseError) as context:
            self.public_battery.update_owner(self.other_org)
        # Get owner of public battery after update
        owner_after = Battery.objects.get(id=self.public_battery.id).owner
        # Check if owner is still the same
        self.assertEqual(owner_before.id, owner_after.id)

    def test_update_public_battery_change_owner_correct_tenant(self):
        print("test_update_public_battery_change_owner_correct_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Get owner of public battery before update
        owner_before = self.public_battery.owner
        # Update owner of public battery to PublicOrg, should succeed
        self.public_battery.update_owner(self.other_org)

        # Get owner of public battery after update
        # Change tenant to OwnerOrg for getting the correct battery
        set_active_tenant(self.other_org.id)
        owner_after = Battery.objects.get(id=self.public_battery.id).owner
        # Check if owner got updated
        self.assertNotEqual(owner_before.id, owner_after.id)

    ########################################################################################################################
    # Delete-Statements-Tests
    def test_delete_public_battery_no_tenant(self):
        print("test_delete_public_battery_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Query number of batteries before delete from database
        nbr_batteries_before = Battery.objects.all().count()
        # Delete public battery should fail
        result = self.public_battery.delete()
        # Check result for number of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Query number of batteries after delete from database
        nbr_batteries_after = Battery.objects.all().count()
        self.assertEqual(nbr_batteries_before, nbr_batteries_after)

    def test_delete_public_battery_wrong_tenant(self):
        print("test_delete_public_battery_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Query number of batteries before delete from database
        nbr_batteries_before = Battery.objects.all().count()
        # Get Id of public battery
        battery_id = self.public_battery.id
        # Delete public battery should fail
        result = self.public_battery.delete()
        # Check result for number of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Query number of batteries after delete from database;
        nbr_batteries_after = Battery.objects.all().count()
        self.assertEqual(nbr_batteries_before, nbr_batteries_after)
        # Check if public battery still exists
        set_active_tenant(self.public_org.id)
        self.assertTrue(Battery.objects.filter(id=battery_id).exists())

    def test_delete_public_battery_correct_tenant(self):
        print("test_delete_public_battery_correct_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Query number of batteries before delte from database
        nbr_batteries_before = Battery.objects.all().count()
        # Get id of battery to delete
        battery_id = self.public_battery.id
        # Delete public battery should succeed
        result = self.public_battery.delete()
        # Check result for number of deleted objects should be >=1 (1 battery, 1 celltest, 1 cyclingtest, 1 aggdata, 3 cyclingrawdata)
        self.assertGreaterEqual(result[0], 1)
        # Check number of deleted batteries from result (should be 1)
        self.assertEqual(result[1]['abd_database.Battery'], 1)
        # Query number of batteries after delete from database
        nbr_batteries_after = Battery.objects.all().count()
        self.assertEqual(nbr_batteries_before - 1, nbr_batteries_after)
        # Check if battery still exists
        self.assertFalse(Battery.objects.filter(id=battery_id).exists())

    def test_delete_owned_battery_no_tenant(self):
        print("test_delete_owned_battery_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Query number of batteries before delete from database
        nbr_batteries_before = Battery.objects.all().count()
        # Get Id of owned battery
        battery_id = self.owned_battery.id
        # Delete owned battery should not delete anything
        result = self.owned_battery.delete()
        # Check result for number of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Query number of batteries after delete from database
        nbr_batteries_after = Battery.objects.all().count()
        self.assertEqual(nbr_batteries_before, nbr_batteries_after)
        # Check if battery still exists
        set_active_tenant(self.owner_org.id)
        self.assertTrue(Battery.objects.filter(id=battery_id).exists())

    def test_delete_owned_battery_wrong_tenant(self):
        print("test_delete_owned_battery_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Query number of batteries before delete from database
        nbr_batteries_before = Battery.objects.all().count()
        # Get id of owned battery
        battery_id = self.owned_battery.id
        # Delete owned battery not delete anything
        result = self.owned_battery.delete()
        # Check result for number of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Query number of batteries after delete from database
        nbr_batteries_after = Battery.objects.all().count()
        self.assertEqual(nbr_batteries_before, nbr_batteries_after)
        # Check if battery still exists
        set_active_tenant(self.owner_org.id)
        self.assertTrue(Battery.objects.filter(id=battery_id).exists())

    def test_delete_owned_battery_correct_tenant(self):
        print("test_delete_owned_battery_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Query number of batteries before delete from database
        nbr_batteries_before = Battery.objects.all().count()
        # Get Id of owned battery
        battery_id = self.owned_battery.id
        # Delete owned battery should succeed
        result = self.owned_battery.delete()
        # Check result for number of deleted objects should be >=1 (1 battery, 1 celltest, 1 cyclingtest, 1 aggdata, 3 cyclingrawdata)
        self.assertGreaterEqual(result[0], 1)
        # Check number of deleted batteries from result (should be 1)
        self.assertEqual(result[1]['abd_database.Battery'], 1)
        # Query number of batteries after delete from database
        nbr_batteries_after = Battery.objects.all().count()
        self.assertEqual(nbr_batteries_before - 1, nbr_batteries_after)
        # Check if battery still exists
        self.assertFalse(Battery.objects.filter(id=battery_id).exists())

    ####################################################### DATASET ########################################################
    ########################################################################################################################
    # Select-Statements-Tests
    def test_get_all_datasets_no_tenant(self):
        print("test_get_all_datasets_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get all datasets
        all_datasets = Dataset.objects.all()
        # Should only return 1 entry, public Dataset
        self.assertEqual(len(all_datasets), 1)
        # ID should be same
        self.assertEqual(all_datasets[0].id, self.public_dataset.id)

    def test_get_all_datasets_owner_tenat(self):
        print("test_get_all_datasets_owner_tenat\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Get all datasets
        all_datasets = Dataset.objects.all()
        # Should return 2 entries, public and private owned Dataset
        self.assertEqual(len(all_datasets), 2)
        # Check if the correct datasets are returned
        expected_dataset_ids = [self.public_dataset.id, self.private_dataset_owner.id]
        self.assertIn(all_datasets[0].id, expected_dataset_ids)
        self.assertIn(all_datasets[1].id, expected_dataset_ids)

    def test_get_all_datasets_other_tenant(self):
        print("test_get_all_datasets_other_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get all datasets
        all_datasets = Dataset.objects.all()
        # Should return 2 entries, public and private owned Dataset
        self.assertEqual(len(all_datasets), 2)
        # Check if the correct datasets are returned
        expected_dataset_ids = [self.public_dataset.id, self.private_dataset_other.id]
        self.assertIn(all_datasets[0].id, expected_dataset_ids)
        self.assertIn(all_datasets[1].id, expected_dataset_ids)

    def test_get_not_owned_dataset(self):
        print("test_get_not_owned_dataset\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get owned dataset
        with self.assertRaises(ObjectDoesNotExist) as context:
            Dataset.objects.get(id=self.private_dataset_owner.id)
        # Get all datasets
        all_datasets = Dataset.objects.all()
        # Private Dataset Owner should not be in all datasets
        self.assertNotIn(self.private_dataset_owner.id, all_datasets)

    ########################################################################################################################
    # Update-/Insert-Statements-Tests
    # Insert
    def test_create_public_dataset_no_tenant(self):
        print("test_create_public_dataset_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Check number of datasets
        nbr_datasets_before = Dataset.objects.all().count()
        # Create dataset should fail
        with self.assertRaises(ProgrammingError) as context:
            new_public_dataset = Dataset.objects.create(name="PublicDataset2", owner=self.public_org, private=False)
        # Check number of datasets
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before, nbr_datasets_after)

    def test_create_public_dataset_with_public_tenant(self):
        print("test_create_public_dataset_with_public_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.public_org.id)
        # Check number of datasets
        nbr_datasets_before = Dataset.objects.all().count()
        # Create dataset should succeed
        new_public_dataset = Dataset.objects.create(name="PublicDataset2", owner=self.public_org, private=False)
        # Check number of datasets
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before + 1, nbr_datasets_after)
        # Check if new dataset exists
        self.assertTrue(Dataset.objects.filter(id=new_public_dataset.id).exists())

    def test_create_public_dataset_with_wrong_tenant(self):
        print("test_create_public_dataset_with_wrong_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Check number of datasets
        nbr_datasets_before = Dataset.objects.all().count()
        # Create dataset should fail
        with self.assertRaises(ProgrammingError) as context:
            new_public_dataset = Dataset.objects.create(name="PublicDataset2", owner=self.public_org, private=False)
        # Check number of datasets
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before, nbr_datasets_after)

    def test_create_public_dataset_with_wrong_owner(self):
        print("test_create_public_dataset_with_wrong_owner\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Check number of datasets
        nbr_datasets_before = Dataset.objects.all().count()
        # Create dataset should fail
        with self.assertRaises(ProgrammingError) as context:
            new_public_dataset = Dataset.objects.create(name="PublicDataset2", owner=self.owner_org, private=False)
        # Check number of datasets
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before, nbr_datasets_after)

    def test_create_private_dataset_no_tenant(self):
        print("test_create_private_dataset_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Check number of datasets
        nbr_datasets_before = Dataset.objects.all().count()
        # Create dataset should fail
        with self.assertRaises(ProgrammingError) as context:
            new_private_dataset = Dataset.objects.create(name="PrivateDataset2", owner=self.owner_org, private=True)
        # Check number of datasets
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before, nbr_datasets_after)

    def test_create_private_dataset_wrong_tenant(self):
        print("test_create_private_dataset_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Check number of datasets
        nbr_datasets_before = Dataset.objects.all().count()
        # Create dataset should fail
        with self.assertRaises(ProgrammingError) as context:
            new_private_dataset = Dataset.objects.create(name="PrivateDataset2", owner=self.owner_org, private=True)
        # Check number of datasets
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before, nbr_datasets_after)

    def test_create_private_dataset_correct_tenant(self):
        print("test_create_private_dataset_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Check number of datasets
        nbr_datasets_before = Dataset.objects.all().count()
        # Create dataset should succeed
        new_private_dataset = Dataset.objects.create(name="PrivateDataset2", owner=self.owner_org, private=True)
        # Check number of datasets
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before + 1, nbr_datasets_after)
        # Check if new dataset exists
        self.assertTrue(Dataset.objects.filter(id=new_private_dataset.id).exists())

    def test_create_private_dataset_wrong_owner(self):
        print("test_create_private_dataset_wrong_owner\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Check number of datasets
        nbr_datasets_before = Dataset.objects.all().count()
        # Create dataset should fail
        with self.assertRaises(ProgrammingError) as context:
            new_private_dataset = Dataset.objects.create(name="PrivateDataset2", owner=self.other_org, private=True)
        # Check number of datasets
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before, nbr_datasets_after)

    # Update
    def test_update_public_dataset_no_tenant(self):
        print("test_update_public_dataset_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get name of public dataset before update
        name_before = self.public_dataset.name
        # Update some values in public dataset, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.public_dataset.name = "PublicDataset2"
            self.public_dataset.save()
        # Get name of public dataset after update
        name_after = Dataset.objects.get(id=self.public_dataset.id).name
        # Check if name is still the same
        self.assertEqual(name_before, name_after)

    def test_update_public_dataset_change_owner_correct_tenant(self):
        print("test_update_public_dataset_change_owner_correct_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Get name of public dataset before update
        owner_before = self.public_dataset.owner.id
        batts_before = Battery.objects.filter(
            cell_test__in=CellTest.objects.filter(dataset=self.public_dataset)).values("owner")

        self.public_dataset.update_owner(self.owner_user.company)

        set_active_tenant(self.owner_user.company.id)

        # Get name of public dataset after update
        ds = Dataset.objects.get(id=self.public_dataset.id)
        owner_after = ds.owner.id
        batts_after = Battery.objects.filter(
            cell_test__in=CellTest.objects.filter(dataset=ds)).values("owner")

        # Check if owner id changed
        self.assertNotEqual(owner_before, owner_after)
        # Check of number of batteries in dataset remained
        self.assertEqual(len(batts_before), len(batts_after))

        # check if battery owner changed
        for b in batts_after:
            self.assertEqual(self.owner_user.company.id, b["owner"])

    def test_update_public_dataset_change_owner_wrong_tenant(self):
        print("test_update_public_dataset_change_owner_wrong_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company)
        # Get name of public dataset before update
        owner_before = self.public_dataset.owner.id
        batts_before = Battery.objects.filter(
            cell_test__in=CellTest.objects.filter(dataset=self.public_dataset)).values("owner")

        with self.assertRaises(DatabaseError) as context:
            self.public_dataset.update_owner(self.owner_user.company)

        set_active_tenant(self.owner_user.company.id)

        # Get name of public dataset after update
        ds = Dataset.objects.get(id=self.public_dataset.id)
        owner_after = ds.owner.id
        batts_after = Battery.objects.filter(
            cell_test__in=CellTest.objects.filter(dataset=ds)).values("owner")

        # Check if owner id changed
        self.assertEqual(owner_before, owner_after)
        # Check of number of batteries in dataset remained
        self.assertEqual(len(batts_before), len(batts_after))

        # check if battery owner changed
        for b in batts_after:
            self.assertEqual(owner_before, b["owner"])

    def test_update_private_dataset_change_owner_correct_tenant(self):
        print("test_update_private_dataset_change_owner_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_org.id)
        # Get name of public dataset before update
        owner_before = self.private_dataset_owner.owner.id
        batts_before = Battery.objects.filter(
            cell_test__in=CellTest.objects.filter(dataset=self.private_dataset_owner)).values("owner")

        self.private_dataset_owner.update_owner(self.other_user.company)

        set_active_tenant(self.other_user.company.id)

        # Get name of public dataset after update
        ds = Dataset.objects.get(id=self.private_dataset_owner.id)
        owner_after = ds.owner.id
        batts_after = Battery.objects.filter(
            cell_test__in=CellTest.objects.filter(dataset=ds)).values("owner")

        # Check if owner id changed
        self.assertNotEqual(owner_before, owner_after)
        # Check of number of batteries in dataset remained
        self.assertEqual(len(batts_before), len(batts_after))

        # check if battery owner changed
        for b in batts_after:
            self.assertEqual(self.other_user.company.id, b["owner"])

    def test_update_private_dataset_change_owner_wrong_tenant(self):
        print("test_update_private_dataset_change_owner_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company.id)
        # Get name of public dataset before update
        owner_before = self.private_dataset_owner.owner.id
        batts_before = Battery.objects.filter(
            cell_test__in=CellTest.objects.filter(dataset=self.private_dataset_owner)).values("owner")

        with self.assertRaises(DatabaseError) as context:
            self.private_dataset_owner.update_owner(self.other_user.company)

        set_active_tenant(self.other_user.company.id)

        # Get name of dataset after update

        with self.assertRaises(ObjectDoesNotExist) as context:
            ds = Dataset.objects.get(id=self.private_dataset_owner.id)


    def test_update_public_dataset_wrong_tenant(self):
        print("test_update_public_dataset_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get name of public dataset before update
        name_before = self.public_dataset.name
        # Update some values in public dataset, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.public_dataset.name = "PublicDataset2"
            self.public_dataset.save()
        # Get name of public dataset after update
        name_after = Dataset.objects.get(id=self.public_dataset.id).name
        # Check if name is still the same
        self.assertEqual(name_before, name_after)

    def test_update_public_dataset_correct_tenant(self):
        print("test_update_public_dataset_correct_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Get name of public dataset before update
        name_before = self.public_dataset.name
        # Update some values in public dataset, should succeed
        name_to_update = "PublicDataset2"
        self.public_dataset.name = name_to_update
        self.public_dataset.save()
        # Get name of public dataset after update
        name_after = Dataset.objects.get(id=self.public_dataset.id).name
        # Check if name got updated
        self.assertNotEqual(name_before, name_after)
        self.assertEqual(name_to_update, name_after)

    def test_update_private_dataset_no_tenant(self):
        print("test_update_private_dataset_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get name of owned dataset before update
        name_before = self.private_dataset_owner.name
        # Update some values in owned dataset, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.private_dataset_owner.name = "PrivateDataset2"
            self.private_dataset_owner.save()
        # Get name of owned dataset after update
        # Set tenant to OwnerOrg for getting the correct dataset
        set_active_tenant(self.owner_user.company_id)
        name_after = Dataset.objects.get(id=self.private_dataset_owner.id).name
        # Reset tenant to None
        set_active_tenant()
        # Check if name is still the same
        self.assertEqual(name_before, name_after)

    def test_update_private_dataset_wrong_tenant(self):
        print("test_update_private_dataset_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get name of owned dataset before update
        name_before = self.private_dataset_owner.name
        # Update some values in owned dataset, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.private_dataset_owner.name = "PrivateDataset2"
            self.private_dataset_owner.save()
        # Get name of owned dataset after update
        # Set tenant to OwnerOrg for getting the correct dataset
        set_active_tenant(self.owner_user.company_id)
        name_after = Dataset.objects.get(id=self.private_dataset_owner.id).name

        # Reset tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Check if name is still the same
        self.assertEqual(name_before, name_after)

    def test_update_private_dataset_correct_tenant(self):
        print("test_update_private_dataset_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Get name of owned dataset before update
        name_before = self.private_dataset_owner.name
        # Update some values in owned dataset, should succeed
        name_to_update = "PrivateDataset2"
        self.private_dataset_owner.name = name_to_update
        self.private_dataset_owner.save()
        # Get name of owned dataset after update
        name_after = Dataset.objects.get(id=self.private_dataset_owner.id).name
        # Check if name got updated
        self.assertNotEqual(name_before, name_after)
        self.assertEqual(name_to_update, name_after)

    ###################################################################################################################
    # Delete-Statements-Tests
    def test_delete_public_dataset_no_tenant(self):
        print("test_delete_public_dataset_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Query number of datasets before delete from database
        nbr_datasets_before = Dataset.objects.all().count()
        # Get Id of public dataset
        dataset_id = self.public_dataset.id
        # Delete public dataset should not delete anything
        result = self.public_dataset.delete()
        # Check nbr of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Query number of datasets after delete from database
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before, nbr_datasets_after)
        # Check if public dataset still exists
        set_active_tenant(self.public_org.id)
        self.assertTrue(Dataset.objects.filter(id=dataset_id).exists())

    def test_delete_public_dataset_wrong_tenant(self):
        print("test_delete_public_dataset_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Query number of datasets before delete from database
        nbr_datasets_before = Dataset.objects.all().count()
        # Get Id from public dataset
        dataset_id = self.public_dataset.id
        # Delete public dataset should not delete anything
        result = self.public_dataset.delete()
        # Check nbr of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Check number of datasets after delete
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before, nbr_datasets_after)
        # Check if dataset still exists
        set_active_tenant(self.public_org.id)
        self.assertTrue(Dataset.objects.filter(id=dataset_id).exists())

    def test_delete_public_dataset_correct_tenant(self):
        print("test_delete_public_dataset_correct_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Query number of datasets before delete from database
        nbr_datasets_before = Dataset.objects.all().count()
        # Get Id of public dataset
        dataset_id = self.public_dataset.id
        # Delete public dataset should succeed
        result = self.public_dataset.delete()
        # Check nbr of deleted objects should be 7 (1 dataset, 1 celltest, 1cyclingtest, 1 aggdata, 3 cyclingrawdata)
        self.assertEqual(result[0], 7)
        # Check number of deleted datasets from result (should be 1)
        self.assertEqual(result[1]['abd_database.Dataset'], 1)
        self.assertEqual(result[1]['abd_database.CellTest'], 1)
        self.assertEqual(result[1]['abd_database.CyclingTest'], 1)
        self.assertEqual(result[1]['abd_database.AggData'], 1)
        self.assertEqual(result[1]['abd_database.CyclingRawData'], 3)

        # Check number of datasets after delete
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before - 1, nbr_datasets_after)
        # Check if dataset still exists
        self.assertFalse(Dataset.objects.filter(id=dataset_id).exists())

    def test_delete_owned_dataset_no_tenant(self):
        print("test_delete_owned_dataset_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Query number of datasets before delete from database
        nbr_datasets_before = Dataset.objects.all().count()
        # Get id of owned dataset
        dataset_id = self.private_dataset_owner.id
        # Delete owned dataset should not delete anything
        result = self.private_dataset_owner.delete()
        # Check number of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Query number of datasets after delete
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before, nbr_datasets_after)
        # Check if dataset still exists
        set_active_tenant(self.owner_org.id)
        self.assertTrue(Dataset.objects.filter(id=dataset_id).exists())

    def test_delete_owned_dataset_wrong_tenant(self):
        print("test_delete_owned_dataset_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Query number of datasets before delete from database
        nbr_datasets_before = Dataset.objects.all().count()
        # Get id of owned dataset
        dataset_id = self.private_dataset_owner.id
        # Delete owned dataset should not delete anything
        result = self.private_dataset_owner.delete()
        # Check number of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Check number of datasets after delete
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before, nbr_datasets_after)
        # Check if dataset still exists
        set_active_tenant(self.owner_org.id)
        self.assertTrue(Dataset.objects.filter(id=dataset_id).exists())

    def test_delete_owned_dataset_correct_tenant(self):
        print("test_delete_owned_dataset_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Query number of datasets before delete from database
        nbr_datasets_before = Dataset.objects.all().count()
        # Get Id of owned dataset
        dataset_id = self.private_dataset_owner.id
        # Delete owned dataset should succeed
        result = self.private_dataset_owner.delete()
        # Check nbr of deleted objects should be =>1 (1 dataset, 1 celltest, 1 cyclingtest, 1 aggdata, 3 cyclingrawdata)
        self.assertGreaterEqual(result[0], 1)
        # Check number of deleted datasets from result (should be 1)
        self.assertEqual(result[1]['abd_database.Dataset'], 1)
        self.assertEqual(result[1]['abd_database.CellTest'], 1)
        self.assertEqual(result[1]['abd_database.CyclingTest'], 1)
        self.assertEqual(result[1]['abd_database.AggData'], 1)
        self.assertEqual(result[1]['abd_database.CyclingRawData'], 3)
        # Check number of datasets after delete
        nbr_datasets_after = Dataset.objects.all().count()
        self.assertEqual(nbr_datasets_before - 1, nbr_datasets_after)
        # Check if dataset still exists
        self.assertFalse(Dataset.objects.filter(id=dataset_id).exists())

    ####################################################### CELLTEST ###################################################
    ####################################################################################################################
    # Select-Statements-Tests
    def test_get_all_celltests_no_tenant(self):
        print("test_get_all_celltests_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get all celltests
        all_celltests = CellTest.objects.all()
        # Should only return 1 entry, public CellTest
        self.assertEqual(len(all_celltests), 1)
        # ID should be same
        self.assertEqual(all_celltests[0].id, self.public_celltest.id)

    def test_get_all_celltests_public_tenant(self):
        print("test_get_all_celltests_public_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Get all celltests
        all_celltests = CellTest.objects.all()
        # Should return 1 entry, public CellTest
        self.assertEqual(len(all_celltests), 1)
        # ID should be same
        self.assertEqual(all_celltests[0].id, self.public_celltest.id)

    def test_get_all_cellltests_owner_tenant(self):
        print("test_get_all_cellltests_owner_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Get all celltests
        all_celltests = CellTest.objects.all()
        # Should return 2 entries, public and private owned CellTest
        self.assertEqual(len(all_celltests), 2)
        # Check if the correct celltests are returned
        expected_celltest_ids = [self.public_celltest.id, self.owned_celltest.id]
        self.assertIn(all_celltests[0].id, expected_celltest_ids)
        self.assertIn(all_celltests[1].id, expected_celltest_ids)

    def test_get_all_celltests_other_tenant(self):
        print("test_get_all_celltests_other_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get all celltests
        all_celltests = CellTest.objects.all()
        # Should return 2 entries, public and private owned CellTest
        self.assertEqual(len(all_celltests), 2)
        # Check if the correct celltests are returned
        expected_celltest_ids = [self.public_celltest.id, self.other_celltest.id]
        self.assertIn(all_celltests[0].id, expected_celltest_ids)
        self.assertIn(all_celltests[1].id, expected_celltest_ids)

    def test_get_not_owned_celltest(self):
        print("test_get_not_owned_celltest\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get owned celltest
        with self.assertRaises(ObjectDoesNotExist) as context:
            CellTest.objects.get(id=self.owned_celltest.id)
        # Get all celltests
        all_celltests = CellTest.objects.all()
        # Private CellTest Owner should not be in all celltests
        self.assertNotIn(self.owned_celltest, all_celltests)

    def test_get_owned_celltest(self):
        print("test_get_owned_celltest\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Get owned celltest
        owned_celltest = CellTest.objects.get(id=self.owned_celltest.id)
        # Get all celltests
        all_celltests = CellTest.objects.all()
        # Private CellTest Owner should be in all celltests
        self.assertIn(self.owned_celltest, all_celltests)

    ########################################################################################################################
    # Update-/Insert-Statements-Tests
    # Insert
    def test_create_public_celltest_no_tenant(self):
        print("test_create_public_celltest_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Check number of celltests
        nbr_celltests_before = CellTest.objects.all().count()
        # Create celltest should fail
        with self.assertRaises(ProgrammingError) as context:
            new_public_celltest = CellTest.objects.create(battery=self.public_battery,
                                                          file=UploadFile.objects.all().first(), date=timezone.now(),
                                                          dataset=self.public_dataset)
        # Check number of celltests
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before, nbr_celltests_after)

    def test_create_public_celltest_with_wrong_tenant(self):
        print("test_create_public_celltest_with_wrong_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Check number of celltests
        nbr_celltests_before = CellTest.objects.all().count()
        # Create celltest should fail
        with self.assertRaises(ProgrammingError) as context:
            new_public_celltest = CellTest.objects.create(battery=self.public_battery,
                                                          file=UploadFile.objects.all().first(), date=timezone.now(),
                                                          dataset=self.public_dataset)
        # Check number of celltests
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before, nbr_celltests_after)

    def test_create_public_celltest_correct_tenant(self):
        print("test_create_public_celltest_correct_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Check number of celltests
        nbr_celltests_before = CellTest.objects.all().count()
        # Create celltest should succeed
        new_public_celltest = CellTest.objects.create(battery=self.public_battery,
                                                      file=UploadFile.objects.all().first(), date=timezone.now(),
                                                      dataset=self.public_dataset)
        # Check number of celltests
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before + 1, nbr_celltests_after)
        # Check if new celltest exists
        self.assertTrue(CellTest.objects.filter(id=new_public_celltest.id).exists())

    def test_create_private_celltest_no_tenant(self):
        print("test_create_private_celltest_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Check number of celltests
        nbr_celltests_before = CellTest.objects.all().count()
        # Create celltest should fail
        with self.assertRaises(ProgrammingError) as context:
            new_private_celltest = CellTest.objects.create(battery=self.owned_battery,
                                                           file=UploadFile.objects.all().first(), date=timezone.now(),
                                                           dataset=self.private_dataset_owner)
        # Check number of celltests
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before, nbr_celltests_after)

    def test_create_private_celltest_wrong_tenant(self):
        print("test_create_private_celltest_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Check number of celltests
        nbr_celltests_before = CellTest.objects.all().count()
        # Create celltest should fail
        with self.assertRaises(ProgrammingError) as context:
            new_private_celltest = CellTest.objects.create(battery=self.owned_battery,
                                                           file=UploadFile.objects.all().first(), date=timezone.now(),
                                                           dataset=self.private_dataset_owner)
        # Check number of celltests
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before, nbr_celltests_after)

    def test_create_private_celltest_owner_mistmatch(self):
        """Create test with mismatching battery and data set owners

            Should raise a Validation error as this is not allowed
        """
        print("test_create_private_celltest_owner_mismatch\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Check number of celltests
        nbr_celltests_before = CellTest.objects.all().count()
        # Create celltest should fail
        with self.assertRaises(ValidationError) as context:
            new_private_celltest = CellTest.objects.create(battery=self.owned_battery,
                                                           file=UploadFile.objects.all().first(), date=timezone.now(),
                                                           dataset=self.private_dataset_other)
        # Check number of celltests
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before, nbr_celltests_after)

    def test_create_private_celltest_wrong_owner(self):
        """Create test for a wrong tenant

            Should be blocked by RLS
        """
        print("test_create_private_celltest_wrong_owner\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Check number of celltests
        nbr_celltests_before = CellTest.objects.all().count()
        # Create celltest should fail
        with self.assertRaises(ProgrammingError) as context:
            new_private_celltest = CellTest.objects.create(battery=self.other_battery,
                                                           file=UploadFile.objects.all().first(), date=timezone.now(),
                                                           dataset=self.private_dataset_other)
        # Check number of celltests
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before, nbr_celltests_after)

    # Update
    def test_update_public_celltest_no_tenant(self):
        print("test_update_public_celltest_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get public celltest equipment before update
        equipment_before = self.public_celltest.equipment
        # Update some values in public celltest, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.public_celltest.equipment = "Test"
            self.public_celltest.save()
        # Get public celltest equipment after update
        equipment_after = CellTest.objects.get(id=self.public_celltest.id).equipment
        # Check if equipment is still the same
        self.assertEqual(equipment_before, equipment_after)

    def test_update_public_celltest_wrong_tenant(self):
        print("test_update_public_celltest_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get public celltest equipment before update
        equipment_before = self.public_celltest.equipment
        # Update some values in public celltest, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.public_celltest.equipment = "Test"
            self.public_celltest.save()
        # Get public celltest equipment after update
        equipment_after = CellTest.objects.get(id=self.public_celltest.id).equipment
        # Check if equipment is still the same
        self.assertEqual(equipment_before, equipment_after)

    def test_update_public_celltest_correct_tenant(self):
        print("test_update_public_celltest_correct_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Get public celltest equipment before update
        equipment_before = self.public_celltest.equipment
        # Update some values in public celltest, should succeed
        equipment_to_update = "Test"
        self.public_celltest.equipment = equipment_to_update
        self.public_celltest.save()
        # Get public celltest equipment after update
        equipment_after = CellTest.objects.get(id=self.public_celltest.id).equipment
        # Check if equipment got updated
        self.assertNotEqual(equipment_before, equipment_after)
        self.assertEqual(equipment_to_update, equipment_after)

    def test_update_private_celltest_no_tenant(self):
        print("test_update_private_celltest_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get owned celltest equipment before update
        equipment_before = self.owned_celltest.equipment
        # Update some values in owned celltest, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.owned_celltest.equipment = "Test"
            self.owned_celltest.save()
        # Change to correct tenant to get object
        set_active_tenant(self.owner_user.company_id)
        # Get owned celltest equipment after update
        equipment_after = CellTest.objects.get(id=self.owned_celltest.id).equipment
        # Check if equipment is still the same
        self.assertEqual(equipment_before, equipment_after)

    def test_update_private_celltest_wrong_tenant(self):
        print("test_update_private_celltest_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get owned celltest equipment before update
        equipment_before = self.owned_celltest.equipment
        # Update some values in owned celltest, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.owned_celltest.equipment = "Test"
            self.owned_celltest.save()
        # Change to correct tenant to get object
        set_active_tenant(self.owner_user.company_id)
        # Get owned celltest equipment after update
        equipment_after = CellTest.objects.get(pk=self.owned_celltest.id).equipment
        # Check if equipment is still the same
        self.assertEqual(equipment_before, equipment_after)

    def test_update_private_celltest_correct_tenant(self):
        print("test_update_private_celltest_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Get owned celltest equipment before update
        equipment_before = self.owned_celltest.equipment
        # Update some values in owned celltest, should succeed
        equipment_to_update = "Test"
        self.owned_celltest.equipment = equipment_to_update
        self.owned_celltest.save()
        # Get owned celltest equipment after update
        equipment_after = CellTest.objects.get(id=self.owned_celltest.id).equipment
        # Check if equipment got updated
        self.assertNotEqual(equipment_before, equipment_after)
        self.assertEqual(equipment_to_update, equipment_after)

    ########################################################################################################################
    # Delete-Statements-Tests
    def test_delete_public_celltest_no_tenant(self):
        print("test_delete_public_celltest_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Query number of celltests before delete from database
        nbr_celltests_before = CellTest.objects.all().count()
        # Get Id of public celltest
        celltest_id = self.public_celltest.id
        # Delete public celltest should not delete anything
        result = self.public_celltest.delete()
        # Check nbr of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Query number of celltests after delete from database
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before, nbr_celltests_after)
        # Check if celltest still exists
        set_active_tenant(self.public_org.id)
        self.assertTrue(CellTest.objects.filter(id=celltest_id).exists())

    def test_delete_public_celltest_wrong_tenant(self):
        print("test_delete_public_celltest_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Query number of celltests before delete from database
        nbr_celltests_before = CellTest.objects.all().count()
        # Get Id of public celltest
        celltest_id = self.public_celltest.id
        # Delete public celltest should not delete anything
        result = self.public_celltest.delete()
        # Check nbr of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Query number of celltests after delete from database
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before, nbr_celltests_after)
        # Check if celltest still exists
        set_active_tenant(self.public_org.id)
        self.assertTrue(CellTest.objects.filter(id=celltest_id).exists())

    def test_delete_public_celltest_correct_tenant(self):
        print("test_delete_public_celltest_correct_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Query number of celltests before delete from database
        nbr_celltests_before = CellTest.objects.all().count()
        # Get Id of public celltest
        celltest_id = self.public_celltest.id
        # Delete public celltest should succeed
        result = self.public_celltest.delete()
        # Check result of delete number of deleted objects should be >=1 (1 celltest, 1 cyclingtest, 1 aggdata, 3 cyclingdata)
        self.assertGreaterEqual(result[0], 1)
        # Check nbr of deleted celltest objects
        self.assertEqual(result[1]['abd_database.CellTest'], 1)
        self.assertEqual(result[1]['abd_database.CyclingTest'], 1)
        self.assertEqual(result[1]['abd_database.AggData'], 1)
        self.assertEqual(result[1]['abd_database.CyclingRawData'], 3)
        # Query number of celltests after delete from database
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before - 1, nbr_celltests_after)
        # Check if celltest still exists
        self.assertFalse(CellTest.objects.filter(id=celltest_id).exists())

    def test_delete_private_celltest_no_tenant(self):
        print("test_delete_private_celltest_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Query number of celltests before delete from database
        nbr_celltests_before = CellTest.objects.all().count()
        # Get Id of owned celltest
        celltest_id = self.owned_celltest.id
        # Delete owned celltest should not delete anything
        result = self.owned_celltest.delete()
        # Check nbr of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Query number of celltests after delete from database
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before, nbr_celltests_after)
        # Check if celltest still exists
        # Set correct tenant to get object
        set_active_tenant(self.owner_user.company_id)
        self.assertTrue(CellTest.objects.filter(id=celltest_id).exists())

    def test_delete_private_celltest_wrong_tenant(self):
        print("test_delete_private_celltest_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Query number of celltests before delete from database
        nbr_celltests_before = CellTest.objects.all().count()
        # Get Id of owned celltest
        celltest_id = self.owned_celltest.id
        # Delete owned celltest should not delete anything
        result = self.owned_celltest.delete()
        # Check nbr of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Query number of celltests after delete from database
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before, nbr_celltests_after)
        # Check if celltest still exists
        # Set correct tenant to get object
        set_active_tenant(self.owner_user.company_id)
        self.assertTrue(CellTest.objects.filter(id=celltest_id).exists())

    def test_delete_private_celltest_correct_tenant(self):
        print("test_delete_private_celltest_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Query number of celltests before delete from database
        nbr_celltests_before = CellTest.objects.all().count()
        # Get Id of owned celltest
        celltest_id = self.owned_celltest.id
        # Delete owned celltest should succeed
        result = self.owned_celltest.delete()
        # Check result of delete number of deleted objects should be >=1 (1 celltest, 1 cyclingtest, 1 aggdata, 3 cyclingdata)
        self.assertGreaterEqual(result[0], 1)
        # Check nbr of deleted celltest objects from result (should be 1)
        self.assertEqual(result[1]['abd_database.CellTest'], 1)
        self.assertEqual(result[1]['abd_database.CyclingTest'], 1)
        self.assertEqual(result[1]['abd_database.AggData'], 1)
        self.assertEqual(result[1]['abd_database.CyclingRawData'], 3)
        # Query number of celltests after delete from database
        nbr_celltests_after = CellTest.objects.all().count()
        self.assertEqual(nbr_celltests_before - 1, nbr_celltests_after)
        # Check if celltest still exists
        self.assertFalse(CellTest.objects.filter(id=celltest_id).exists())

    ####################################################### CYCLINGTEST #######################################################
    # Select-Statements-Tests

    def test_get_all_cyclingtests_no_tenant(self):
        print("test_get_all_cyclingtests_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get all cyclingtests
        all_cyclingtests = CyclingTest.objects.all()
        # Should only return 1 entry, public CyclingTest
        self.assertEqual(len(all_cyclingtests), 1)
        # Check if the correct cyclingtest is returned
        self.assertEqual(all_cyclingtests[0].id, self.public_cyclingtest.id)

    def test_get_all_cyclingtests_owner_tenant(self):
        print("test_get_all_cyclingtests_owner_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Get all cyclingtests
        all_cyclingtests = CyclingTest.objects.all()
        # Should return 2 entries, public and private owned CyclingTest
        self.assertEqual(len(all_cyclingtests), 2)
        # Check if the correct cyclingtests are returned
        expected_cyclingtest_ids = [self.public_cyclingtest.id, self.owned_cyclingtest.id]
        self.assertIn(all_cyclingtests[0].id, expected_cyclingtest_ids)
        self.assertIn(all_cyclingtests[1].id, expected_cyclingtest_ids)

    def test_get_all_cyclingtests_other_tenant(self):
        print("test_get_all_cyclingtests_other_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get all cyclingtests
        all_cyclingtests = CyclingTest.objects.all()
        # Should return 2 entries, public and private owned CyclingTest
        self.assertEqual(len(all_cyclingtests), 2)
        # Check if the correct cyclingtests are returned
        expected_cyclingtest_ids = [self.public_cyclingtest.id, self.other_cyclingtest.id]
        self.assertIn(all_cyclingtests[0].id, expected_cyclingtest_ids)
        self.assertIn(all_cyclingtests[1].id, expected_cyclingtest_ids)

    def test_get_not_owned_cyclingtest(self):
        print("test_get_not_owned_cyclingtest\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get owned cyclingtest
        with self.assertRaises(Exception) as context:
            CyclingTest.objects.get(id=self.owned_cyclingtest.id)

    def test_get_owned_cyclingtest(self):
        print("test_get_owned_cyclingtest\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Get owned cyclingtest
        owned_cyclingtest = CyclingTest.objects.get(id=self.owned_cyclingtest.id)
        self.assertIsInstance(owned_cyclingtest, CyclingTest)

    ########################################################################################################################
    # Update-/Insert-Statements-Tests
    # Insert
    def test_create_public_cyclingtest_no_tenant(self):
        print("test_create_public_cyclingtest_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Check number of cyclingtests
        nbr_cyclingtests_before = CyclingTest.objects.all().count()
        # Create cyclingtest should fail
        with self.assertRaises(ProgrammingError) as context:
            new_public_cyclingtest = CyclingTest.objects.create(cellTest=self.public_celltest)
        # Check number of cyclingtests
        nbr_cyclingtests_after = CyclingTest.objects.all().count()
        self.assertEqual(nbr_cyclingtests_before, nbr_cyclingtests_after)

    def test_create_public_cyclingtest_public_tenant(self):
        print("test_create_public_cyclingtest_public_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Check number of cyclingtests
        nbr_cyclingtests_before = CyclingTest.objects.all().count()
        # One-to-One Relation --> Do not add new cyclingtest to existing celltest but create new celltest
        new_celltest = CellTest.objects.create(battery=self.public_battery, file=UploadFile.objects.all().first(),
                                               date=timezone.now(), dataset=self.public_dataset)
        # Create cyclingtest should succeed
        new_public_cyclingtest = CyclingTest.objects.create(cellTest=new_celltest)
        # Check number of cyclingtests
        nbr_cyclingtests_after = CyclingTest.objects.all().count()
        self.assertEqual(nbr_cyclingtests_before + 1, nbr_cyclingtests_after)
        # Check if new cyclingtest exists
        self.assertTrue(CyclingTest.objects.filter(id=new_public_cyclingtest.id).exists())

    def test_create_public_cyclingtest_wrong_tenant(self):
        print("test_create_public_cyclingtest_wrong_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Check number of cyclingtests
        nbr_cyclingtests_before = CyclingTest.objects.all().count()
        # Create cyclingtest should fail
        with self.assertRaises(ProgrammingError) as context:
            new_public_cyclingtest = CyclingTest.objects.create(cellTest=self.public_celltest)
        # Check number of cyclingtests
        nbr_cyclingtests_after = CyclingTest.objects.all().count()
        self.assertEqual(nbr_cyclingtests_before, nbr_cyclingtests_after)

    def test_create_private_cyclingtest_wrong_tenant(self):
        print("test_create_private_cyclingtest_wrong_tenant\n")
        # One-to-One Relation --> Do not add new cyclingtest to existing celltest but create new celltest
        # Set tenant to OwnerOrg to create new celltest
        set_active_tenant(self.owner_user.company_id)
        new_celltest = CellTest.objects.create(battery=self.owned_battery, file=UploadFile.objects.all().first(),
                                               date=timezone.now(), dataset=self.private_dataset_owner)
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Check number of cyclingtests
        nbr_cyclingtests_before = CyclingTest.objects.all().count()
        # Create cyclingtest should fail
        with self.assertRaises(ProgrammingError) as context:
            new_private_cyclingtest = CyclingTest.objects.create(cellTest=new_celltest)

    def test_create_private_cyclingtest_correct_tenant(self):
        print("test_create_private_cyclingtest_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Check number of cyclingtests
        nbr_cyclingtests_before = CyclingTest.objects.all().count()
        # Create cyclingtest should succeed
        # One-to-One Relation --> Do not add new cyclingtest to existing celltest but create new celltest
        new_celltest = CellTest.objects.create(battery=self.owned_battery, file=UploadFile.objects.all().first(),
                                               date=timezone.now(), dataset=self.private_dataset_owner)
        new_private_cyclingtest = CyclingTest.objects.create(cellTest=new_celltest)
        # Check number of cyclingtests
        nbr_cyclingtests_after = CyclingTest.objects.all().count()
        self.assertEqual(nbr_cyclingtests_before + 1, nbr_cyclingtests_after)
        # Check if new cyclingtest exists
        self.assertTrue(CyclingTest.objects.filter(id=new_private_cyclingtest.id).exists())

    # Update
    def test_update_public_cyclingtest_no_tenant(self):
        print("test_update_public_cyclingtest_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get public cyclingtest comment before update
        comment_before = self.public_cyclingtest.comments
        # Update some values in public cyclingtest, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.public_cyclingtest.comments = "Test"
            self.public_cyclingtest.save()
        # Get public cyclingtest equipment after update
        comment_after = CyclingTest.objects.get(id=self.public_cyclingtest.id).comments
        # Check if comment is still the same
        self.assertEqual(comment_before, comment_after)

    def test_update_public_cyclingtest_wrong_tenant(self):
        print("test_update_public_cyclingtest_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get public cyclingtest comment before update
        comment_before = self.public_cyclingtest.comments
        # Update some values in public cyclingtest, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.public_cyclingtest.comments = "Test"
            self.public_cyclingtest.save()
        # Get public cyclingtest equipment after update
        comment_after = CyclingTest.objects.get(id=self.public_cyclingtest.id).comments
        # Check if comment is still the same
        self.assertEqual(comment_before, comment_after)

    def test_update_private_cyclingtest_no_tenant(self):
        print("test_update_private_cyclingtest_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get owned cyclingtest comment before update
        comment_before = self.owned_cyclingtest.comments
        # Update some values in owned cyclingtest, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.owned_cyclingtest.comments = "Test"
            self.owned_cyclingtest.save()
        # Change to correct tenant to get object
        set_active_tenant(self.owner_user.company_id)
        # Get owned cyclingtest equipment after update
        comment_after = CyclingTest.objects.get(id=self.owned_cyclingtest.id).comments
        # Check if comment is still the same
        self.assertEqual(comment_before, comment_after)

    def test_update_private_cyclingtest_wrong_tenant(self):
        print("test_update_private_cyclingtest_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get owned cyclingtest comment before update
        comment_before = self.owned_cyclingtest.comments
        # Update some values in owned cyclingtest, should fail
        with self.assertRaises(ProgrammingError) as context:
            self.owned_cyclingtest.comments = "Test"
            self.owned_cyclingtest.save()
        # Change to correct tenant to get object
        set_active_tenant(self.owner_user.company_id)
        # Get owned cyclingtest equipment after update
        comment_after = CyclingTest.objects.get(pk=self.owned_cyclingtest.id).comments
        # Check if comment is still the same
        self.assertEqual(comment_before, comment_after)

    def test_update_private_cyclingtest_correct_tenant(self):
        print("test_update_private_cyclingtest_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Get owned cyclingtest comment before update
        comment_before = self.owned_cyclingtest.comments
        # Update some values in owned cyclingtest, should succeed
        comment_to_update = "Test"
        self.owned_cyclingtest.comments = comment_to_update
        self.owned_cyclingtest.save()
        # Get owned cyclingtest comments after update
        comment_after = CyclingTest.objects.get(id=self.owned_cyclingtest.id).comments
        # Check if comment got updated
        self.assertNotEqual(comment_before, comment_after)
        self.assertEqual(comment_to_update, comment_after)

    ########################################################################################################################
    # Delete-Statements-Tests
    def test_delete_public_cyclingtest_no_tenant(self):
        print("test_delete_public_cyclingtest_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Query number of cyclingtests before delete from database
        nbr_cyclingtests_before = CyclingTest.objects.all().count()
        # Get Id of public cyclingtest
        cyclingtest_id = self.public_cyclingtest.id
        # Delete public cyclingtest should not delete anything
        result = self.public_cyclingtest.delete()
        # Check nbr of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Check number of cyclingtests after delete
        nbr_cyclingtests_after = CyclingTest.objects.all().count()
        self.assertEqual(nbr_cyclingtests_before, nbr_cyclingtests_after)
        # Check if cyclingtest still exists
        set_active_tenant(self.public_org.id)
        self.assertTrue(CyclingTest.objects.filter(id=cyclingtest_id).exists())

    def test_delete_public_cyclingtest_wrong_tenant(self):
        print("test_delete_public_cyclingtest_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Query number of cyclingtests before delete from database
        nbr_cyclingtests_before = CyclingTest.objects.all().count()
        # Get Id of public cyclingtest
        cyclingtest_id = self.public_cyclingtest.id
        # Delete public cyclingtest should not delete anything
        result = self.public_cyclingtest.delete()
        # Check nbr of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Query number of cyclingtests after delete from database
        nbr_cyclingtests_after = CyclingTest.objects.all().count()
        self.assertEqual(nbr_cyclingtests_before, nbr_cyclingtests_after)
        # Check if cyclingtest still exists
        self.assertTrue(CyclingTest.objects.filter(id=cyclingtest_id).exists())

    def test_delete_public_cyclingtest_correct_tenant(self):
        print("test_delete_public_cyclingtest_correct_tenant\n")
        # Set tenant to PublicOrg
        set_active_tenant(self.public_org.id)
        # Query number of cyclingtests before delete from database
        nbr_cyclingtests_before = CyclingTest.objects.all().count()
        # Get Id of public cyclingtest
        cyclingtest_id = self.public_cyclingtest.id
        # Delete public cyclingtest should succeed
        result = self.public_cyclingtest.delete()
        # Check result of delete number of deleted objects should be >=1 (1 cyclingtest, 1 aggdata, 3 cyclingdata)
        self.assertGreaterEqual(result[0], 1)
        # Check nbr of deleted cyclingtest objects from result (should be 1)
        self.assertEqual(result[1]['abd_database.CyclingTest'], 1)
        self.assertEqual(result[1]['abd_database.AggData'], 1)
        self.assertEqual(result[1]['abd_database.CyclingRawData'], 3)
        # Query number of cyclingtests after delete from database
        nbr_cyclingtests_after = CyclingTest.objects.all().count()
        self.assertEqual(nbr_cyclingtests_before - 1, nbr_cyclingtests_after)
        # Check if cyclingtest still exists
        self.assertFalse(CyclingTest.objects.filter(id=cyclingtest_id).exists())

    def test_delete_private_cyclingtest_no_tenant(self):
        """ Tests deletion of a privately owned CyclingTest when no tenant is assigned

            It should not be possible to delete the record since an anonymous tenant is not allowed to delete a record.
        """

        print("test_delete_private_cyclingtest_no_tenant\n")
        # Do not set any tenant
        set_active_tenant()
        # Get Id of owned cyclingtest
        cyclingtest_id = self.owned_cyclingtest.id
        # Delete owned cyclingtest should not delete anything
        result = self.owned_cyclingtest.delete()
        # Check nbr of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Check if cyclingtest still exists
        # Set correct tenant to get object
        set_active_tenant(self.owner_user.company_id)
        self.assertTrue(CyclingTest.objects.filter(id=cyclingtest_id).exists())

    def test_delete_private_cyclingtest_wrong_tenant(self):
        print("test_delete_private_cyclingtest_wrong_tenant\n")
        # Set tenant to OtherOrg
        set_active_tenant(self.other_user.company_id)
        # Get cyclingtest Id
        cyclingtest_id = self.owned_cyclingtest.id
        # Delete owned cyclingtest should not delete anything
        result = self.owned_cyclingtest.delete()
        # Check nbr of deleted objects (should be 0)
        self.assertEqual(result[0], 0)
        # Check if cyclingtest still exists
        # Set correct tenant to get object
        set_active_tenant(self.owner_org.id)
        self.assertTrue(CyclingTest.objects.filter(id=cyclingtest_id).exists())

    def test_delete_private_cyclingtest_correct_tenant(self):
        print("test_delete_private_cyclingtest_correct_tenant\n")
        # Set tenant to OwnerOrg
        set_active_tenant(self.owner_user.company_id)
        # Query number of cyclingtests before delete from database
        nbr_cyclingtests_before = CyclingTest.objects.all().count()
        # Get Id of owned cyclingtest
        cyclingtest_id = self.owned_cyclingtest.id
        # Delete owned cyclingtest should succeed
        result = self.owned_cyclingtest.delete()
        # Check result of delete number of deleted objects should be >=1 (1 cyclingtest, 1 aggdata, 3 cyclingdata)
        self.assertGreaterEqual(result[0], 1)
        # Check nbr of deleted cyclingtest objects from result (should be 1)
        self.assertEqual(result[1]['abd_database.CyclingTest'], 1)
        self.assertEqual(result[1]['abd_database.AggData'], 1)
        self.assertEqual(result[1]['abd_database.CyclingRawData'], 3)
        # Query number of cyclingtests after delete from database
        nbr_cyclingtests_after = CyclingTest.objects.all().count()
        self.assertEqual(nbr_cyclingtests_before - 1, nbr_cyclingtests_after)
        # Check if cyclingtest still exists
        self.assertFalse(CyclingTest.objects.filter(id=cyclingtest_id).exists())
