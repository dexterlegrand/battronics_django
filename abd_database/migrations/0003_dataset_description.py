# Generated by Django 4.0.4 on 2022-08-24 13:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('abd_database', '0002_battery_file_hdf5file_file_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='description',
            field=models.TextField(blank=True, max_length=2000, null=True),
        ),
    ]
