from rest_framework import serializers
from abd_database.models import (
    Dataset,
)


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = '__all__'
        # fields = [
        #     "id",
        #     "name",
        #     "url",
        #     "license",
        #     "description",
        # ]
