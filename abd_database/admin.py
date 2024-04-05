from django.contrib import admin
from .models import *

admin.site.register(Battery)
admin.site.register(BatteryType)
admin.site.register(ChemicalType)
admin.site.register(PrismaFormat)
admin.site.register(CylinderFormat)
admin.site.register(PrismaISONorm)
admin.site.register(CylinderISONorm)
admin.site.register(CellTest)
admin.site.register(CyclingTest)
admin.site.register(EISTest)
# admin.site.register(User)
admin.site.register(Supplier)
admin.site.register(Proportion)
admin.site.register(Dataset)

