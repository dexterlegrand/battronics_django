from django.contrib.auth import login, logout
from django.views import generic
# Create your views here.
from django.shortcuts import render
from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from abd_database.models import Dataset
from django.db.models import Count

from abd_management.serializers import UserLoginSerializer, UserSerializer


def index(request):
    return render(request, 'abd_management/index.html')


def contact(request):
    return render(request, 'abd_management/contact.html')


def imprint(request):
    return render(request, 'abd_management/imprint.html')


def disclaimer(request):
    return render(request, 'abd_management/disclaimer.html')


class Resources(generic.View):
    model = Dataset
    template_name = "abd_management/resources.html"

    def get(self, request):
        context = {"datasets":
                    Dataset.objects.all().exclude(pk=1).annotate(nb_batteries=Count('celltest__battery', distinct=True))
                }
        return render(request, self.template_name, context)

class UserLogin(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = (SessionAuthentication,)

    def post(self, request):
        data = request.data
        # TODO: validate email and password
        serializer = UserLoginSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            user = serializer.check_user(data)
            login(request, user)
            return Response(serializer.data, status=status.HTTP_200_OK)

class UserLogout(APIView):
    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_200_OK)

class UserView(APIView):
    permission_classes = (permissions.IsAuthenticated, TokenHasReadWriteScope)
    # authentication_classes = (SessionAuthentication,)

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({'user': serializer.data}, status=status.HTTP_200_OK)