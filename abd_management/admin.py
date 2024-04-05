from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from . import models


class UserAdmin(DjangoUserAdmin):
    # to add custom fields to admin page
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            'Organisation', # you can also use None
            {
                'fields': (
                    'company',
                ),
            },
        ),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            'Organisation', # you can also use None
            {
                'fields': (
                    'company',
                ),
            },
        ),
    )


admin.site.register(models.User, UserAdmin)
admin.site.register(models.Organisation)
