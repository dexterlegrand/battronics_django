# Generated by Django 4.0.4 on 2023-04-03 16:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('abd_database', '0007_battery_name_battery_prod_year_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='battery',
            name='name',
            field=models.CharField(editable=False, max_length=128, unique=True),
        ),
    ]
