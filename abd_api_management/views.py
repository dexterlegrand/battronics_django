from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from abd_database.models import Dataset
from django.db.models import Count
from .serializers import DatasetSerializer


class DatasetView(ListAPIView):
    def get_queryset(self):
        return (
            Dataset.objects.all()
            .exclude(pk=1)
            .annotate(nb_batteries=Count("celltest__battery", distinct=True))
        )

    def get(self, request):
        try:
            queryset = self.get_queryset()
            serializer = DatasetSerializer(queryset, many=True)
            return Response({"data": serializer.data}, status=200)
        except ObjectDoesNotExist:
            return Response({"error": "Dataset not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
