from django.db import models

# Create your models here.

from django.db import models
from django.contrib.auth.models import AbstractUser, Permission


class Organisation(models.Model):
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=255, null=True, blank=True)

    @staticmethod
    def get_or_create(**values):
        try:
            return Organisation.objects.get(**values)
        except Organisation.DoesNotExist:
            return Organisation.objects.create(**values)

    def __str__(self):
        return self.name


class User(AbstractUser):
    company = models.ForeignKey(Organisation, on_delete=models.CASCADE)

    class Meta:
        permissions = [
            ("can_upload", "Can upload test-files")
        ]

    def save(self, *args, **kwargs):
        # only for createsuperuser command
        if not self.company_id and self.is_superuser:
            # probably not the best way to do this, but it works
            self.company_id = 1
        # TODO: for productive use, remove this if statement --> do not set permissions on every new user
        if not self.pk:
            super(User, self).save(*args, **kwargs)
            # Get the permission object for "can_upload"
            permission = Permission.objects.get(codename='can_upload')

            # Add the permission to the user
            self.user_permissions.add(permission)
        else:
            super(User, self).save(*args, **kwargs)


def get_anonymous_user_instance(User):
    return User(username='Anonymous', company_id=1)
