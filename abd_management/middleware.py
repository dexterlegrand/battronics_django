from django.db import connection

from ABD_Webapp.settings import json_config


class RlsMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Set empty for annonymous user
        if request.user.is_anonymous:
            tenant_id = None
        else:
            tenant_id = request.user.company_id

        with connection.cursor() as cursor:
            cursor.execute(f'SET abd.active_tenant = "{tenant_id}" ')
            cursor.execute(f'SET abd.change_owner_battid = "{None}" ')

        response = self.get_response(request)

        return response


class DatabaseUserSwitchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_superuser:
            connection.close()
            connection.settings_dict["USER"] = json_config["db_admin_user"]
            connection.settings_dict["PASSWORD"] = json_config["db_admin_pwd"]
            connection.connect()

        response = self.get_response(request)

        connection.close()
        connection.settings_dict["USER"] = json_config["db_user"]
        connection.settings_dict["PASSWORD"] = json_config["db_pwd"]
        connection.connect()

        return response
