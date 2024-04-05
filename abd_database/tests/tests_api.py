from django.contrib.auth.hashers import make_password
from rest_framework.test import APITransactionTestCase
from abd_database import models
from abd_database import serializers
from abd_management.models import Organisation, User
from django.contrib.contenttypes.models import ContentType
from rest_framework import status
from django.conf import settings
from abd_database.helpers.db import set_active_tenant


class BatteryTestCase(APITransactionTestCase):
    databases = ['default', 'admin']

    def setUp(self) -> None:
        public_org, created = Organisation.objects.get_or_create(name=settings.PUBLIC_DATA_ADMIN_ORG_NAME)

        self.user = User.objects.create(username='admin', password=make_password("admin"), company=public_org)

        nmc = models.ChemicalType.objects.create(
            shortname='NMC532',
            synonyms=['NCM523'],
            name='NickelCobaltManganOxide532'
        )
        nmc_prop = models.Proportion.objects.create(
            proportions='50:30:20'
        )

        self.anode = models.ChemicalType.objects.create(
            shortname='G',
            synonyms=['Graphite', 'graphite'],
            name='Graphite'
        )

        cylinder = models.CylinderFormat.objects.create(
            diameter=18,
        )

        supplier = models.Supplier.objects.create(
            name='BFH',
            city='Burgdorf',
            country='Switzerland'
        )

        pris_type = ContentType.objects.create(model="CylinderFormat")

        self.batt_type = models.BatteryType.objects.create(
            supplier=supplier,
            specific_type='INR18650',
            theoretical_capacity=2.5,
            chemical_type_cathode=nmc,
            cathode_proportions=nmc_prop,
            content_type_id=pris_type.pk,
            object_id=cylinder.pk
        )

        self.battery = models.Battery(
            chemical_type_anode=self.anode,
            anode_proportions=None,
            battery_type=self.batt_type,
            weight=12.4,
            vnom=3.65,
            vmax=4.2,
            vmin=2.5,
            comments='This is a test battery',
            owner=public_org,
            private=True
        )

        set_active_tenant(public_org.id)

        self.battery.save()

    def test_get_battery_instance_no_login(self):

        response = self.client.get(f"/database/api/batteries/{self.battery.pk}/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_battery_instance_login(self):
        r = self.client.login(username="admin", password="admin")

        server_name = "http://testserver"

        response = self.client.get(f"/database/api/batteries/{self.battery.pk}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        battery_type = serializers.BatteryTypeSerializer(self.batt_type)
        chemtype_anode = serializers.NestedChemicalTypeSerializer(self.anode)

        self.assertEqual(response.data, {
            "url": f"{server_name}/database/api/batteries/{self.battery.pk}/",
            "id": self.battery.pk,
            "name": "BFH_INR18650_NONE_001",
            "battery_type": battery_type.data,
            "chemical_type_anode": chemtype_anode.data,
            "anode_proportions": None,
            "weight": 12.4,
            "vnom": 3.65,
            "vmax": 4.2,
            "vmin": 2.5,
            "comments": 'This is a test battery',
            "cell_test": []
        })

    def test_get_batteries_no_login(self):
        response = self.client.get(f"/database/api/batteries/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data, [])

    def test_get_batteries_login(self):
        r = self.client.login(username="admin", password="admin")

        response = self.client.get(f"/database/api/batteries/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 1)
