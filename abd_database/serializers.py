from rest_framework import serializers

from abd_management.models import User
from .models import Battery, BatteryType, AggData, CyclingRawData, CellTest, Dataset, ChemicalType, PrismaFormat, \
    CylinderFormat, Supplier, CyclingTest


class ChemicalTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChemicalType
        fields = '__all__'


class NestedChemicalTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChemicalType
        fields = ['id', 'shortname']


class PrismaFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrismaFormat
        fields = '__all__'


class CylinderFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = CylinderFormat
        fields = '__all__'


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = '__all__'


class DatasetSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Dataset
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['owner'] = instance.owner.username
        return representation


class NestedBatterySerializer(serializers.ModelSerializer):
    cell_test = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    chemical_type_anode = NestedChemicalTypeSerializer(read_only=True)

    class Meta:
        model = Battery
        # fields = '__all__'
        fields = (
            'url', 'id', 'name', 'weight', 'vnom', 'vmax', 'vmin', 'chemical_type_anode', 'cell_test', 'battery_type')
        extra_kwargs = {
            'url': {'view_name': 'abd_db:battery-detail', 'lookup_field': 'pk'}
        }


class BatteryTypeSerializer(serializers.ModelSerializer):
    batteries = NestedBatterySerializer(many=True, read_only=True, source='battery_set')
    chemical_type_cathode = NestedChemicalTypeSerializer(read_only=True)
    battery_format = serializers.SerializerMethodField()

    class Meta:
        model = BatteryType
        fields = '__all__'
        # fields = ('url', 'id', 'specific_type', 'theoretical_capacity', 'object_id', 'chemical_type_cathode', 'batteries')

    def get_battery_format(self, obj):
        content_type = obj.content_type
        object_id = obj.object_id

        if content_type.model == 'prismaformat':
            serializer = PrismaFormatSerializer
        elif content_type.model == 'cylinderformat':
            serializer = CylinderFormatSerializer
        else:
            return None

        try:
            instance = content_type.get_object_for_this_type(id=object_id)
        except content_type.model_class().DoesNotExist:
            return None  # Handle if object does not exist

        return serializer(instance, context=self.context).data


class BatterySerializer(serializers.HyperlinkedModelSerializer):
    battery_type = BatteryTypeSerializer(many=False, read_only=False)
    cell_test = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    chemical_type_anode = NestedChemicalTypeSerializer()
    anode_proportions = serializers.StringRelatedField()

    class Meta:
        model = Battery
        fields = (
            'url', 'id', 'name', 'battery_type', 'chemical_type_anode', 'anode_proportions', 'weight', 'vnom', 'vmax',
            'vmin', 'comments', 'cell_test')
        extra_kwargs = {
            'url': {'view_name': 'abd_db:battery-detail', 'lookup_field': 'pk'}
        }


class CellTestSerializer(serializers.HyperlinkedModelSerializer):
    battery = serializers.HyperlinkedRelatedField(view_name="abd_db:battery-detail", read_only=False,
                                                  queryset=Battery.objects.all())
    dataset = serializers.HyperlinkedRelatedField(view_name="abd_db:dataset-detail", read_only=False,
                                                  queryset=Dataset.objects.all())

    class Meta:
        model = CellTest
        fields = ["url", "id", "battery", "battery_id", "dataset", "dataset_id", "equipment", "date"]
        extra_kwargs = {
            'url': {'view_name': 'abd_db:celltest-detail', 'lookup_field': 'pk'}
        }


class CyclingTestSerializer(serializers.HyperlinkedModelSerializer):
    cellTest = serializers.HyperlinkedRelatedField(view_name="abd_db:celltest-detail", read_only=False,
                                                   queryset=CellTest.objects.all())

    class Meta:
        model = CyclingTest
        fields = '__all__'
        extra_kwargs = {
            'url': {'view_name': 'abd_db:cyclingtest-detail', 'lookup_field': 'pk'}
        }


class AggDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = AggData
        fields = '__all__'


class CyclingRawDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CyclingRawData
        fields = '__all__'


class FileSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False)
    )
