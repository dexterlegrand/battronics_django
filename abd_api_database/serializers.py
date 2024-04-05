from rest_framework import serializers
from abd_database.models import (
    Battery,
    BatteryType,
    CyclingTest,
    EISTest,
    AggData,
    CyclingRawData,
    UploadBatch,
    UploadFile,
    Dataset,
    CellTest,
    Proportion,
    Supplier,
)


class BatteryTypeListSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    cathode = serializers.CharField(read_only=True)
    batteryFormat = serializers.CharField(read_only=True)
    specificType = serializers.CharField(read_only=True)
    theoreticalCapacity = serializers.FloatField(read_only=True)

    class Meta:
        model = BatteryType
        fields = [
            "id",
            "cathode",
            "batteryFormat",
            "specificType",
            "theoreticalCapacity",
        ]


class BatteryListSerializer(serializers.ModelSerializer):

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    # dataset = serializers.CharField(source='cell_test.dataset', read_only=True)
    cathode = serializers.CharField(
        source="battery_type.chemical_type_cathode", read_only=True
    )
    anode = serializers.CharField(read_only=True)
    batteryFormat = serializers.CharField(
        source="battery_type.content_object", read_only=True
    )
    specificType = serializers.CharField(
        source="battery_type.specific_type", read_only=True
    )
    theoreticalCapacity = serializers.FloatField(
        source="battery_type.theoretical_capacity", read_only=True
    )
    weight = serializers.FloatField(read_only=True)

    class Meta:
        model = Battery
        fields = [
            "id",
            "name",
            # 'dataset',
            "cathode",
            "anode",
            "batteryFormat",
            "specificType",
            "theoreticalCapacity",
            "weight",
        ]


class BatteryDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Battery
        fields = "__all__"


class CellTestSerializer(serializers.ModelSerializer):
    dataset_name = serializers.CharField(source="dataset.name", read_only=True)
    date = serializers.DateField(format="%Y-%m-%d")

    class Meta:
        model = CellTest
        fields = [
            "dataset_name",
            "date",
        ]


class CyclingTestSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    cellTest = CellTestSerializer()
    aggdata_count = serializers.IntegerField(read_only=True)
    ave_temp = serializers.FloatField(read_only=True)
    charge_c_rates = serializers.ListField(
        child=serializers.FloatField(), read_only=True
    )
    discharge_c_rates = serializers.ListField(
        child=serializers.FloatField(), read_only=True
    )

    class Meta:
        model = CyclingTest
        fields = [
            # "url",
            "id",
            "cellTest",
            "aggdata_count",
            "ave_temp",
            "charge_c_rates",
            "discharge_c_rates",
        ]


class GraphDataSerializer(serializers.Serializer):
    cycle_id = serializers.IntegerField()
    discharge_capacity = serializers.FloatField()
    charge_capacity = serializers.FloatField()

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass