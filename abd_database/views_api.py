from rest_framework import generics
from rest_framework import viewsets, response

from .models import Battery, BatteryType, AggData, CyclingRawData, CellTest, Dataset, CyclingTest
from .permissions import ReadOnly
from .serializers import BatterySerializer, BatteryTypeSerializer, AggDataSerializer, CyclingRawDataSerializer, \
    CellTestSerializer, DatasetSerializer, CyclingTestSerializer

from .helpers.modelHelper import save_files
from .helpers.upload import add_duplicates_to_queue

def string_to_list(string_list):
    return [int(c) for c in string_list.split(',')]


class BatteryDetail(generics.RetrieveAPIView):
    queryset = Battery.objects.all()
    serializer_class = BatterySerializer
    permission_classes = [ReadOnly]


class BatteryTypeDetail(generics.RetrieveAPIView):
    queryset = BatteryType.objects.all()
    serializer_class = BatteryTypeSerializer
    permission_classes = [ReadOnly]


class DatasetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to view and Datasets
    """
    queryset = Dataset.objects.all()
    serializer_class = DatasetSerializer


class BatteryTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to view and edit Battery types
    """
    queryset = BatteryType.objects.all()
    serializer_class = BatteryTypeSerializer


class BatteryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Batteries to be viewed and edited
    """
    queryset = Battery.objects.all()
    serializer_class = BatterySerializer
    # filter_backends = [HasPermissionFilterBackend]

    def get_queryset(self):
        """
        Custom queryset

        Filter per Dataset
        """
        if 'pk' in self.kwargs:
            return super().get_queryset()

        dataset_pk = self.request.query_params.get('dataset')
        if dataset_pk is not None:
            queryset = Battery.objects.filter(
                cell_test__dataset=dataset_pk).distinct()
        else:
            queryset = Battery.objects.all()

        return queryset


class CellTestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows CellTests to be viewed
    """
    queryset = CellTest.objects.all()
    serializer_class = CellTestSerializer


class CyclingTestViewSet(viewsets.ModelViewSet):
    queryset = CyclingTest.objects.all()
    serializer_class = CyclingTestSerializer


class AggDataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to view and edit aggregated cycling data
    """
    serializer_class = AggDataSerializer
    queryset = AggData.objects.all()

    def get_queryset(self):
        """
        Custom queryset

        Filter for battery required, optional additional filter for cell test for that battery.
        """

        # todo: allow many batteries as well

        if 'pk' in self.kwargs:
            return super().get_queryset()

        queryset = None

        battery = self.request.query_params.get('battery')
        celltest = self.request.query_params.get('cell_tests')

        if battery is not None:
            if celltest is not None:
                celltest = string_to_list(celltest)
            queryset = AggData.objects.get_agg_data_for_battery(battery=battery, cell_tests=celltest)

        else:
            raise Exception('GET without battery filter not allowed')

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Custom implementation of list view:
        Returns a list of fields and nested list with the data, instead of default behaviour (field-value pairs for each
        query item)
        """

        fields = ["id", "cycling_test_id", "cycle_id", "charge_capacity", "discharge_capacity", "efficiency",
                  "charge_c_rate", "discharge_c_rate", "ambient_temperature", "error_codes"]

        queryset = self.get_queryset()

        return response.Response({"fields": fields, "data": queryset})


class CyclingRawDataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to retrieve and edit cycling raw data
    """
    serializer_class = CyclingRawDataSerializer

    def get_queryset(self):
        cycles = self.request.query_params.get('cycles')
        battery = self.request.query_params.get('battery')
        fields = self.request.query_params.get('fields')

        assert (battery is None) or (cycles is None), 'filtering cycles and battery is not allowed'

        if fields is None:
            fields = ["id", "time", "voltage", "current", "capacity", "energy", "agg_data_id", "cycle_id",
                      "step_flag", "time_in_step", "cell_temperature", "ambient_temperature"]
        else:
            fields = [field for field in fields.split(',')]

        queryset = None

        if cycles is not None:
            cycles = string_to_list(cycles)
            queryset = CyclingRawData.objects.capacity_vs_voltage_for_cycles(cycles=cycles, api=True,
                                                                             field_list=fields)

        if battery is not None:
            queryset = CyclingRawData.objects.get_data_for_battery(battery, fields)

        if queryset is None:
            raise Exception('Not supported request string')

        return queryset, fields

    def list(self, request, *args, **kwargs):
        """
        Custom implementation of list view:
        Returns a list of fields and nested list with the data, instead of default behaviour (field-value pairs for each
        query item)
        """

        queryset, fields = self.get_queryset()

        return response.Response({"fields": fields, "data": queryset})

# not rdy for release
# class H5Upload(viewsets.ViewSet):
#     # parser_classes = (FileUploadParser, FormParser)
#     parser_classes = (MultiPartParser,)
#
#     # serializer_class = UploadSerializer
#
#     def create(self, request):
#         serializer = FileSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         files = serializer.validated_data["files"]
#
#         batch, duplicates = save_files(files, request.user, "Hdf5Extractor")
#
#         if batch:
#             if not duplicates[0] and not duplicates[1]:
#                 add_duplicates_to_queue(request, batch, len(files))
#             else:
#                 # TODO: handle duplicates
#                 raise Exception("Duplicates")
#         else:
#             # TODO: add error handling --> occurs if in save_files returns nothing
#             raise Exception("Other error")
#
#         return response.Response({"batch_id": batch.id}, status.HTTP_201_CREATED)
