# Generated by Django 4.0.4 on 2023-09-12 12:31

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def create_public_admin(apps, schema_editor):
    Organisation = apps.get_model("abd_management", "Organisation")

    org = Organisation()
    org.name = settings.PUBLIC_DATA_ADMIN_ORG_NAME
    org.save()


def set_default_org_for_users(apps, schema_editor):
    Organisation = apps.get_model("abd_management", "Organisation")
    User = apps.get_model("abd_management", "User")

    default_org = Organisation.objects.get(name=settings.PUBLIC_DATA_ADMIN_ORG_NAME)

    for u in User.objects.all():
        u.company = default_org
        u.save()


class Migration(migrations.Migration):
    dependencies = [
        ('abd_management', '0004_organisation'),
        ('sessions', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_public_admin),
        migrations.AddField(
            model_name='user',
            name='company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                                    to='abd_management.organisation')
        ),
        migrations.RunPython(set_default_org_for_users),
        migrations.AlterField(
            model_name='user',
            name='company',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    to='abd_management.organisation')
        )
    ]
