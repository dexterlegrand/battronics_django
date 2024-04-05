from django.apps import apps
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

# Create your views here.

from django.views import View
from .models import CycleAgingFit
from abd_database.models import Battery

import numpy as np


class CycleAgingView(View):
    template_name = 'abd_predictions/aging_predictions.html'
    x_axis = 'EFC' #'Hours', 'Cycle', EFC' # todo this should come from the html could be Time, Cycle, EFC others?
    model = CycleAgingFit

    def get(self, request, battery_pk):
        Battery = apps.get_model('abd_database', 'Battery')
        # maybe add check if battery has tests
        if Battery.objects.filter(pk=battery_pk).exists():
            try:
                # initialize model
                ca = self.create_or_get_model(battery_pk)
                # can not do any predictions if battery has no tests
                if not ca.batt.cell_test.all():
                    # TODO: do not raise exception but handle it
                    raise Exception
                # fit and store model and create predictions
                xpred, predictions, x, x_fit, residuals, eol, model, RMSE, x_eol = ca.fit_predict(x_base=self.x_axis) if ca._state.adding\
                    else ca.predict(self.x_axis)

                # TODO: Maybe only plot the data that is used for the fit (or make it optional)
                context = {'cap_dis': list(ca.data['discharge_capacity']),
                           'cap_chg': list(ca.data['charge_capacity']),
                           'battery': Battery.objects.get(pk=battery_pk),
                           'predictions': list(predictions),
                           'x': list(x),
                           'xpred': list(xpred),
                           'residuals': list(residuals),
                           'baseline': list([0] * len(x)),
                           'x_fit': list(x_fit),
                           'x_label': self.x_axis,
                           'eol': list(eol * np.ones_like(ca.data.x)),
                           'equation': model['Equation'],
                           'RMSE': np.format_float_positional(RMSE, 4, fractional=False),
                           'x_eol': x_eol}

                values = []
                names = []
                for i in range(len(model['Parameter'])):
                    values.append(np.format_float_positional(model['Parameter'][i]['Value'], 4, fractional=False))     # round Parameter to 4 significant digits
                    names.append(model['Parameter'][i]['Name'])
                context['parameter'] = zip(names, values)
                return render(request, self.template_name, context)
            except Exception as e:
                # TODO: do not catch general exception, do error handling (eg logging, etc)
                return render(request, self.template_name)
        else:
            raise PermissionDenied()

    def create_or_get_model(self, battery_pk):
        # for now nothing is stored
        #
        # models = self.model.objects.models_for_battery(battery_pk)
        # model = models[0] if models.exists() else self.model()

        model = self.model()
        model.batt = Battery.objects.get(pk=battery_pk)
        return model

