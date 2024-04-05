from django.db import connection


def set_active_tenant(active_tenant=None) -> None:
    with connection.cursor() as cursor:
        cursor.execute(f"SET abd.active_tenant = {active_tenant}")
        cursor.execute(f"SET abd.change_owner_battid = {None}")
