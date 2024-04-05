from abc import ABC, abstractmethod
from django.views import View
from .models import AggData, Battery, CyclingRawData
from django.http import HttpResponse
from django.contrib import messages
import csv


class ExportCSV(View, ABC):
    fields = None
    units = None

    @abstractmethod
    def get_data(self):
        pass

    @abstractmethod
    def set_filename(self):
        pass

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv', headers={'filename': self.set_filename()})
        response['Content-Disposition'] = f'attachment; filename={self.set_filename()}'

        data = self.get_data()

        writer = csv.writer(response)

        if self.fields is not None:
            writer.writerow(self.fields)

        if self.units is not None:
            writer.writerow(self.units)

        for r in data:
            writer.writerow(r)

        return response


class ExportAggData(ExportCSV):
    model = AggData
    fields = ['cycle_id', 'charge_capacity', 'discharge_capacity', 'efficiency',
              'charge_c_rate', 'discharge_c_rate', 'ambient_temperature']
    units = ["", "Ah", "Ah", "%", "", "", "degreeC"]

    def get_data(self):
        return self.model.objects.get_agg_data_for_battery(self.kwargs['battery_id'], field_list=self.fields)

    def set_filename(self):
        name = Battery.objects.get(pk=self.kwargs["battery_id"]).__str__()
        return f'{name}-cycling_data.csv'


class ExportRawData(ExportCSV):
    model = CyclingRawData
    fields = ["time", "voltage", "current", "capacity", "energy", "cycle_id", "step_flag",
              "time_in_step", "cell_temperature", "ambient_temperature"]
    units = ["", "V", "A", "Ah", "Wh", "", "", "s", "degreeC", "degreeC"]

    def get_data(self):
        return self.model.objects.get_data_for_battery(self.kwargs["battery_id"], field_list=self.fields)

    def set_filename(self):
        name = Battery.objects.get(pk=self.kwargs["battery_id"]).__str__()
        return f'{name}-raw_data.csv'




