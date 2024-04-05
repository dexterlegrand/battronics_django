
# Create your models here.
from abd_database.models import Battery, AggData
from django.db import models
import pandas as pd

from .predictors.cycle_aging import Predictor, AutoPredictor
from abc import abstractmethod


class PredictionModelManager(models.Manager):
    def models_for_battery(self, battery: int):
        return self.filter(batteries__pk=battery)


class PredictionModel(models.Model):
    batteries = models.ManyToManyField(Battery)  # Für CalendarAging wird wohl nur ein Modell pro Batterie erstellt
    # und ein Modell ist immer nur für eine Batterie brauchbar, aber für ML-Modelle, kann sein, dass mehere Modelle
    # exisitiern und diese für mehrer Batterien gültig sind
    last_update = models.DateTimeField()

    objects = PredictionModelManager()

    class Meta:
        abstract = True

    @abstractmethod
    def fit_predict(self, *args, **kwargs):
        pass

    @abstractmethod
    def predict(self, *args, **kwargs):
        pass


class CycleAgingFit(PredictionModel):
    time_window: float = 0.8
    divider = 1

    auto = True

    if auto:
        regressor = AutoPredictor()
    else:
        # TODO: Take parameter from user input
        # Example piecewise prediction
        regressor = Predictor({'Fit1': {'type': 'Power'},
                               'Fit2': {'type': 'Linear',
                                        'order': 1,
                                        'method': 'Linear'
                                        }},
                              cut=110.5)

        # Example single prediction
        # regressor = Predictor({'Fit1': {'type': 'Power'}})
    data = None
    batt = None
    eol = None

    def __get_data(self, x_base='Hours'):

        self.data = pd.DataFrame(
            AggData.objects.filter(cycling_test__cellTest__battery=self.batt).order_by('start_time').values())

        # select variable for X-axis and remove NaN
        self.data, self.divider = self.regressor.set_x(self.data, self.batt.battery_type.theoretical_capacity,
                                                       x_base=x_base)

        self.eol = 0.8 * self.batt.battery_type.theoretical_capacity

        return self.data, self.divider

    def fit_predict(self, x_base):

        if self.data is None:
            self.__get_data(x_base)

        fit_time_window = self.data.iloc[int(len(self.data) * 0.75), self.data.columns.get_indexer(['x'])].values[
            0]
        outlier = {'remove': True}
        # todo load regressor here ?
        xpred, ypred, x_fit, residuals, model, RMSE, x_eol = self.regressor.fit_predict(self.data, self.eol,
                                                                                        fit_time_window=fit_time_window,
                                                                                        outlier=outlier)

        self.time_window = fit_time_window
        # self.last_update = datetime.datetime.now()
        # self.save()
        return xpred / self.divider, ypred, self.data[
            'x'].values / self.divider, x_fit / self.divider, residuals, self.eol, model, RMSE, x_eol

    def predict(self, x_base):
        pass

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(CycleAgingFit, self).save(force_insert=force_insert, force_update=force_update,
                                        using=using, update_fields=update_fields)
        self.batteries.add(self.batt)
