from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.models import Group
from rest_framework import serializers

UserModel = get_user_model()


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def check_user(self, clean_data):
        user = authenticate(password=clean_data['password'], username=clean_data['username'])
        if not user:
            raise serializers.ValidationError("Invalid Credentials")
        return user


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)

    class Meta:
        model = UserModel
        fields = ('email', 'username', 'groups')
