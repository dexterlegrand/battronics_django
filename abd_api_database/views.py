from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
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
from . import serializers


class BatteryTypeAPIView(ListAPIView):
    def get_queryset(self):
        return BatteryType.objects.all()

    def get(self, request):
        try:
            queryset = self.get_queryset()
            serializer = serializers.BatteryTypeListSerializer(queryset, many=True)
            print(serializer.data)
            return Response(
                {"data": serializer.data},
                status=200,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class BatteryListAPIView(ListAPIView):
    def get_queryset(self):
        return Battery.objects.all()

    def get(self, request):
        try:
            page = request.GET.get("page")
            pageSize = request.GET.get("pageSize")
            searchKey = request.GET.get("searchKey")
            sortKey = request.GET.get("sortKey")
            print(page, pageSize, searchKey, sortKey)

            queryset = self.get_queryset()
            serializer = serializers.BatteryListSerializer(queryset, many=True)
            return Response(
                {"data": serializer.data},
                status=200,
            )
        # except ObjectDoesNotExist:
        #     return Response({"error": "Battery List not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


# class BatteryListView(ListAPIView):
#     serializer_class = BatteryListSerializer

#     def get_queryset(self):
#         # ds = self.kwargs.get("ds")
#         # print(ds)
#         # if ds and ds != "0":
#         #     return Battery.objects.filter(
#         #         dataset_id=ds
#         #     )  # Assuming a ForeignKey relation to Dataset
#         return Battery.objects.all()

#     def get(self, request, *args, **kwargs):
#         queryset = self.get_queryset()
#         # ds = self.kwargs.get("ds")
#         # dataset_name = "All"
#         # if ds and ds != "0":
#         #     dataset_name = Dataset.objects.get(pk=ds).name

#         # page = self.paginate_queryset(queryset)
#         # if page is not None:
#         #     serializer = self.get_serializer(page, many=True)
#         #     return self.get_paginated_response(serializer.data)
#         serializer = self.get_serializer(queryset, many=True)
#         # return Response({"data": serializer.data, "dataset": dataset_name})
#         return Response({"data": serializer.data})


# class BatteryListByDatasetView(ListAPIView):

#     def list(self, request, ds):
#         dataset_pk = ds
#         queryset = Battery.objects.all()

#         serializer = BatteryListSerializer(queryset, many=True)

#         return Response(serializer.data)


class BatteryDetailAPIView(APIView):
    def get(self, request, pk):
        try:
            battery = Battery.objects.get(pk=pk)
            cycling_tests = CyclingTest.objects.get_cycling_tests_for_battery(battery)
            if cycling_tests:
                graph_data = CyclingTest.objects.plot_cycles(cycling_tests[0])
            graph_ser = serializers.GraphDataSerializer(graph_data, many=True)
            serializer = serializers.CyclingTestSerializer(cycling_tests, many=True)
            print("serializer", serializer.data)
            # serializer = serializers.BatteryDetailSerializer(battery)
            return Response(
                {"data": {"test": serializer.data, "graph": 'graph_ser.data'}},
                status=200,
            )
        except Battery.DoesNotExist:
            return Response({"error": "Battery not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

        # has_tests = battery.cell_test.exists()
        # cycling_tests = CyclingTest.objects.get_cycling_tests_for_battery(battery)
        # graph = None
        # if cycling_tests:
        #     graph = CyclingTest.objects.plot_cycles(cycling_tests[0])

        # upload_test_formset = MyUploadTestFormSet(queryset=CellTest.objects.none())
        # form_class = self.get_form_class()
        # form = self.get_form(form_class)

        # context = {
        #     "battery": battery,
        #     "has_tests": has_tests,
        #     "cycling_tests": cycling_tests,
        #     "graph": graph,
        #     "upload_test_formset": upload_test_formset,
        #     "form": form,
        # }
        # return Response("context")

    # def post(self, request, pk):
    #     if request.headers.get("x-requested-with") == "XMLHttpRequest":
    #         tab = request.POST.get("tab")
    #         if tab == "cycles-tab":
    #             test_pk = int(request.POST["selection"])
    #             graph = CyclingTest.objects.plot_cycles(
    #                 CyclingTest.objects.get(pk=test_pk), as_dict=True
    #             )
    #             return JsonResponse({"graph": graph}, status=200)
    #         elif tab == "capacity-tab":
    #             data = {}
    #             agg_data = AggData.objects.get_agg_data_for_battery(
    #                 request.POST["battery_pk"]
    #             )
    #             if not agg_data:
    #                 return JsonResponse({"error": "AggData not found"}, status=400)
    #             data["agg_data"] = agg_data
    #             if len(request.POST.getlist("selected_cycles[]")) == 0:
    #                 cycles = [agg_data[0][0]]
    #             else:
    #                 cycles = list(map(int, request.POST.getlist("selected_cycles[]")))
    #             data["graph"] = CyclingRawData.objects.capacity_vs_voltage_for_cycles(
    #                 cycles=cycles, as_dict=True
    #             )
    #             return JsonResponse(data, status=200)
    #         return JsonResponse({"error": "Invalid tab"}, status=400)
    #     elif "delete-test" in request.POST:
    #         form_class = self.get_form_class()
    #         form = self.get_form(form_class)
    #         test_pk = int(request.POST["delete-test"])
    #         try:
    #             cell_test = CellTest.objects.get(pk=test_pk)
    #             cell_test.delete()
    #             return self.form_valid(form)
    #         except CellTest.DoesNotExist:
    #             return JsonResponse({"error": "Test not found"}, status=400)
    #     return JsonResponse({"error": "Invalid request"}, status=400)

    # def get_success_url(self):
    #     return reverse(
    #         viewname="abd_db:battery_detail", kwargs={"pk": self.kwargs["pk"]}
    #     )
