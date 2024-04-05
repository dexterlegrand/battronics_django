from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.signal import detrend


@dataclass
class Tags:
    discharge_capacity: str = 'discharge_capacity'
    discharge_c_rate: str = 'discharge_c_rate'
    charge_capacity: str = 'charge_capacity'
    start_time: str = 'start_time'
    end_time: str = 'end_time'
    cycle_id: str = 'cycle_id'


class BasePredictor(ABC):
    model = NotImplemented

    def __init__(self, tags: Tags = None):
        if tags is None:
            self.tags = Tags()
        else:
            self.tags = tags

    @abstractmethod
    def fit(self, data, *args, **kwargs):
        pass

    @abstractmethod
    def predict(self, x, *args, **kwargs):
        pass

    def _set_fit_window(self, data, fit_window=None):
        """
        Selects data for fitting. All data within the fit_window is selected
        """

        if fit_window is not None:
            window_filter = data['x'] <= fit_window
            data = data.loc[window_filter, :]

        return data

    @staticmethod
    def _shape_x(x_fit, x_shape=1):
        """
        Shape X-Vector/Array such that it can be processed by the following algorithms
        """
        if x_shape == 0:
            x_fit = x_fit.values.reshape(-1, )
        else:
            x_fit = x_fit.values.reshape(-1, x_shape)

        return x_fit

    def set_x(self, data, theoretical_capacity, x_base='Hours'):

        divider = 1

        data.dropna(subset=[self.tags.discharge_capacity, self.tags.charge_capacity], inplace=True)

        if x_base == 'Hours':
            data['dt'] = data[self.tags.end_time] - data[self.tags.start_time].min()
            data['x'] = data['dt'].apply(lambda x: x.total_seconds())
            divider = (3600 * 24)

        elif x_base == 'EFC':
            # Calculation 'capacity since start' doesn't work if there are nan in the data
            data['capacity since start'] = (data[self.tags.discharge_capacity].values.cumsum()
                                            + data[self.tags.charge_capacity].values.cumsum())
            data['EFC_id'] = data['capacity since start'] / (2 * theoretical_capacity)
            data['x'] = data['EFC_id']

        else:
            data['x'] = data[self.tags.cycle_id]

        return data, divider

    def preprocessing(self, data, fit_window=None, x_shape=1, outlier=None):

        if outlier is None:
            outlier = {'remove': False}

        # Select most occuring C-rate
        data = self._c_rate_grouping(data)

        # Remove outliers
        if outlier['remove']:
            data = self._outlier_detection(data)

        # Select data for fit
        data = self._set_fit_window(data, fit_window=fit_window)

        x_fit, y_fit = data['x'], data[self.tags.discharge_capacity]

        x_fit = self._shape_x(x_fit, x_shape=x_shape)

        return x_fit.astype(np.float64), y_fit

    def _c_rate_grouping(self, data, n_bins=10):
        """
        Group data by discharge c rate and return data slice containing only the most common c rate group.

        This function groups the data into n_bins c rate groups. The groups range from 0 to the maximum c rate in the data.
        The function returns the sliced Dataframe only containing the data of the most common c rate group.

        Parameters
        ----------
        data : DataFrame
            Cycle data.
        n_bins : int, optional
            Number of equal spaced c rate groups. The default is 10.

        Returns
        -------
        data_c : DataFrame
            Cycle data from the most common c rate group

        """
        max_c_rate = data[self.tags.discharge_c_rate].max()
        c_rate_groups = data.groupby(
            pd.cut(data[self.tags.discharge_c_rate], np.linspace(0, max_c_rate, n_bins))).groups
        # Get the indices of the largest c rate group
        index = c_rate_groups[max(c_rate_groups, key=lambda key: c_rate_groups[key].size)]
        data_c = data.loc[index]
        return data_c

    @staticmethod
    def _std_limit(data):
        std = data.std()
        mean = data.mean()
        low = mean - 3 * std
        up = mean + 3 * std
        idx = np.where(np.logical_and(data >= low, data <= up))[0]
        return idx

    # TODO: Also known as Z-Score. Maybe there are faster functions for calculating this.
    def _outlier_detection(self, data):
        """
        Detect and remove outlier from discharge capacity data.

        Parameters
        ----------
        data : DataFrame
            Cycle data.

        Returns
        -------
        DataFrame
            Cycle data without outliers in discharge capacity.

        """
        data_detrend = detrend(data[self.tags.discharge_capacity])
        idx = self._std_limit(data_detrend)
        data = data.iloc[idx]

        return data

    def iterative_outlier_detection(self, x_fit, y_fit, y_pred):
        residuals = self._calculate_residuals(y_fit, y_pred)
        idx = self._std_limit(residuals)
        x_fit = x_fit[idx]
        y_fit = y_fit.iloc[idx]
        return x_fit, y_fit

    @staticmethod
    def _calculate_residuals(y, y_pred):
        residuals = y - y_pred
        return residuals

    def calculate_rmse(self, y, y_pred):
        residuals = self._calculate_residuals(y, y_pred)
        RMSE = np.sqrt(np.mean(residuals ** 2))
        return RMSE, residuals

    def find_eol(self, x, pred_fact, eol):
        # TODO: Improve eol determination (works but not really elegant)
        #   EOL is first integer cycle under the EOL line
        x_eol = np.arange(x[0], x[-1] * 3, 1, dtype=float)
        y_eol = self.predict(x_eol.reshape(-1, ))
        x_eol_idx = np.argmax(y_eol < eol)
        x_eol = x_eol[x_eol_idx]
        if x_eol > x[-1] * pred_fact:
            x_end = x_eol
        else:
            x_end = x[-1] * pred_fact
        return x_end, x_eol


class FullPredictor(BasePredictor, ABC):

    @abstractmethod
    def fit_predict(self, df, eol, fit_time_window=None, pred_fact=1.5, outlier=None):
        x_fit, y_fit = self.fit(data=df, fit_time_window=fit_time_window, outlier=outlier)
        x = df['x'].values
        x_end, x_eol = self.find_eol(x, pred_fact, eol)
        xpred = np.linspace(x[0], x_end, 100)
        ypred = self.predict(xpred.reshape(-1, ))
        ymodel = self.predict(x_fit.reshape(-1, ))
        RMSE, residuals = self.calculate_rmse(y_fit, ymodel)
        return x_fit, y_fit, xpred, ypred, x_eol, ymodel, RMSE, residuals
