import copy
import numpy as np
from sklearn.linear_model import LinearRegression, RANSACRegressor
from sklearn.preprocessing import PolynomialFeatures, MinMaxScaler
from sklearn.pipeline import make_pipeline
from .base import BasePredictor, FullPredictor
from scipy.optimize import curve_fit


def define_regressor(reg):
    estimators = {'Linear': LinearRegression(),
                  'RANSAC': RANSACRegressor()}

    # TODO Error if reg is not in estimators
    if reg in estimators:
        model = estimators[reg]

    return model


def curve_fit_regressor(model, x, y, p0, bounds=(-np.inf, np.inf)):
    """
    Fit power model to data.

    Parameters
    ----------
    model : function
        Mathematical function of the fit.
    x : numpy array
        x values for fit.
    y : numpy array
        y values for fit.
    p0 : tuple of floats
        Start values for the parameter optimization. Length of tuple must equal number of model parameters.
    bounds : tuple of lists of floats, optional
        Boundary values for every parameter of the model. First list lower boundary, second list upper boundary.
        Number of floats in each list must be equal to the number of model parameters. Default is (-np.inf, np.inf)
        which disables all boundaries.

    Returns
    -------
    popt : tuple
        Optimized model parameter.

    """

    # TODO: Better handling of error if curve_fit doesn't find a solution
    # TODO: Define appropriate number of iterations maxfev
    try:
        popt, pocv = curve_fit(
            f=model,
            xdata=x,
            ydata=y,
            p0=p0,
            bounds=bounds,
            maxfev=100000
        )
    except RuntimeError:
        print('curve_fit: No solution found')
        popt = p0
    return popt


class LinearPredictor(BasePredictor):
    """
    Predictor for polynomial fits.

    Parameters
    ----------
    regressor : str
        Linear regression model to use. 'Linear' for using standard least squares regression, 'RANSAC' for using
        the RANSAC algorithm.
    order : int
        Order of polynomial to use.

    """

    def __init__(self, regressor, order):
        super().__init__()
        self.regressor = regressor
        poly_feat = PolynomialFeatures(degree=order, include_bias=False)
        self.model = define_regressor(self.regressor)
        self.scaler = MinMaxScaler()
        self.pipeline = make_pipeline(poly_feat, self.scaler, self.model)

    def fit(self, data, fit_time_window=None, outlier=None, iter_fit=False):
        if self.regressor == 'RANSAC':
            outlier = {'remove': False}  # outlier removal not necessary for RANSAC
        x_fit, y_fit = self.preprocessing(data, fit_time_window, x_shape=1, outlier=outlier)
        self.pipeline.fit(x_fit, y_fit)
        # TODO: Maybe no iter fit if regressor is RANSAC?
        if iter_fit:
            x_fit, y_fit = self.iterative_outlier_detection(x_fit, y_fit, self.pipeline.predict(x_fit))
            self.pipeline.fit(x_fit, y_fit)
        return x_fit, y_fit

    def predict(self, x, *args, **kwargs):
        return self.pipeline.predict(x)


class PowerPredictor(BasePredictor):
    """
    Predictor for general power fits.

    """

    def __init__(self, **kwargs):
        super().__init__()
        self.popt = None

    def fit(self, data, fit_time_window=None, outlier=None, iter_fit=True):
        x_fit, y_fit = self.preprocessing(data, fit_time_window, x_shape=0, outlier=outlier)
        # TODO: User input for start values and boundaries
        p0 = (-1, data[self.tags.discharge_capacity].values[0], 0.75)
        # bounds = ([-np.inf, 0, 0.5], [0, np.inf, 1])    # hard physical bounds
        bounds = ([-np.inf, 0, 0], [1, np.inf, 1.5])  # soft bounds (non-physical)
        self.popt = curve_fit_regressor(self.model, x_fit, y_fit, p0=p0, bounds=bounds)
        if iter_fit:
            x_fit, y_fit = self.iterative_outlier_detection(x_fit, y_fit, self.model(x_fit, *self.popt))
            self.popt = curve_fit_regressor(self.model, x_fit, y_fit, p0=p0, bounds=bounds)
        print(self.popt)
        return x_fit, y_fit

    def predict(self, x, *args, **kwargs):
        return self.model(x, *self.popt)

    @staticmethod
    def model(x, a, b, c):
        return a * x ** c + b


class Predictor(FullPredictor):
    """
    Main Predictor class.

    """

    def __init__(self, models, **kwargs):
        super().__init__()
        if len(models) > 1:
            self.mode = 'piecewise'
            self.cut = kwargs['cut']
        else:
            self.mode = 'single'
        self.typ = {}
        order = {}
        method = {}
        # TODO: Combine both for loops
        for key, value in models.items():
            if value['type'] == 'Linear':
                self.typ[key] = value['type']
                order[key] = value['order']
                method[key] = value['method']
            else:
                self.typ[key] = value['type']

        self.models = []
        for fit in self.typ:
            if self.typ[fit] == 'Linear':
                self.models.append(LinearPredictor(method[fit], order[fit]))
            if self.typ[fit] == 'Power':
                self.models.append(PowerPredictor())

    def fit(self, data, fit_time_window=None, outlier=None):
        # can't use preprocessing here because I need to pass the dataframe to the other classes
        data = self._set_fit_window(data, fit_time_window)

        if self.mode == 'piecewise':
            data1, data2 = self.piecewise_data2(data)
            data = [data1, data2]
        else:
            data = [data]

        x_fit = []
        y_fit = []
        for model, d in zip(self.models, data):
            data_copy = copy.deepcopy(d)
            x_fit_i, y_fit_i = model.fit(data_copy, fit_time_window=None, outlier=outlier)
            x_fit.append(x_fit_i.reshape(-1, ))
            y_fit.append(y_fit_i)
        x_fit = np.concatenate(x_fit)
        y_fit = np.concatenate(y_fit)
        return x_fit, y_fit

    def predict(self, x, *args, **kwargs):
        if self.mode == 'piecewise':
            xs = self.piecewise_data(x)
        else:
            xs = [x]  # list needed for zip to work
        preds = []
        for model, x in zip(self.models, xs):
            # Reshape x if model is LinearPredictor
            if isinstance(model, LinearPredictor):
                x = x.reshape(-1, 1)
            preds.append(model.predict(x))
        pred = np.concatenate(preds)
        return pred

    # TODO: User input for pred_fact
    def fit_predict(self, df, eol, fit_time_window=None, pred_fact=1.5, outlier=None):
        x_fit, y_fit, xpred, ypred, x_eol, ymodel, RMSE, residuals = super(Predictor, self).fit_predict(df, eol,
                                                                                                        fit_time_window,
                                                                                                        pred_fact,
                                                                                                        outlier)

        print(RMSE)
        model = {'Equation': '',
                 'Parameter': {}
                 }
        if self.mode == 'piecewise':
            model['Parameter'][0] = {'Name': 'Cut Position', 'Value': self.cut}
        i = 0
        for model_i in self.models:
            idx = i + 1
            offset = len(model['Parameter'])
            if i != 0:
                model['Equation'] += ' | '
            if isinstance(model_i, PowerPredictor):
                para = model_i.popt
                model['Equation'] += f'a{idx}*x^c{idx} + b{idx}'
                model['Parameter'][offset] = {'Name': f'a{idx}', 'Value': para[0]}
                model['Parameter'][offset + 1] = {'Name': f'b{idx}', 'Value': para[1]}
                model['Parameter'][offset + 2] = {'Name': f'c{idx}', 'Value': para[2]}
            if isinstance(model_i, LinearPredictor):
                # TODO: Not sure if scaling correct, also it differs depending on the used scaler
                # TODO: Somehow the scaler changes the value of intercept and I don't know how to correct it
                #   Intercept ist not the same as self.predict(x[0])
                if model_i.regressor == 'RANSAC':
                    p = model_i.model.estimator_.coef_ * model_i.scaler.scale_  # correct the coef for scaling
                    p = np.insert(p, 0, model_i.model.estimator_.intercept_)
                else:
                    p = model_i.model.coef_ * model_i.scaler.scale_  # correct the coef for scaling
                    p = np.insert(p, 0, model_i.model.intercept_)
                for j in range(len(p)):
                    model['Parameter'][offset + j] = {'Name': f'p{idx}_{j}', 'Value': p[j]}
                    if j == 0:
                        model['Equation'] += f'p{idx}_{j}'
                    else:
                        model['Equation'] += f' + p{idx}_{j}*x^{j}'
            i += 1
        return xpred, ypred, x_fit.reshape(-1, ), residuals, model, RMSE, x_eol

    # TODO: Only one piecewise_data function
    def piecewise_data(self, x, y=None):
        """
        Cut data into two parts.

        Parameters
        ----------
        x : numpy array
            x values of data.
        y : numpy array, optional
            y values of data.

        Returns
        -------
        tuple of dataframes or dataframes
             Data cut into two parts.

        """
        x1 = x[x <= self.cut]
        x2 = x[x > self.cut]
        if y is None:
            return x1, x2
        else:
            y1 = y[:len(x1)]
            y2 = y[len(x1):]
            return (x1, y1), (x2, y2)

    def piecewise_data2(self, data):
        data1 = data.loc[data['x'] <= self.cut]
        data2 = data.loc[data['x'] > self.cut]
        return data1, data2


class AutoPredictor(FullPredictor):
    """
    Automatic piecewise power fit (optimization of cut position).

    """

    def __init__(self, **kwargs):
        super().__init__()
        self.popt = None

    def fit(self, data, fit_time_window=None, outlier=None, iter_fit=True):
        x_fit, y_fit = self.preprocessing(data, fit_time_window, x_shape=0, outlier=outlier)
        # TODO: User input for start values and boundaries
        p0 = np.array([1, y_fit.iloc[0], -1, 0.75, -1, 0.75], dtype=float)
        bounds = ([0, 0, -np.inf, 0, -np.inf, 0], [x_fit[-1], np.inf, 0, 1.5, 0, 1.5])
        # bounds = ([150, 0, -np.inf, 0, -np.inf, 0], [1550, np.inf, 0, 1.5, 0, 1.5])

        self.popt = curve_fit_regressor(model=self.model, x=x_fit, y=y_fit, p0=p0, bounds=bounds)
        if iter_fit:
            x_fit, y_fit = self.iterative_outlier_detection(x_fit, y_fit, self.model(x_fit, *self.popt))
            self.popt = curve_fit_regressor(self.model, x_fit, y_fit, p0=p0, bounds=bounds)
        print(self.popt)
        return x_fit, y_fit

    def predict(self, x, *args, **kwargs):
        return self.model(x, *self.popt)

    # TODO: User input for pred_fact
    def fit_predict(self, df, eol, fit_time_window=None, pred_fact=1.5, outlier=None):
        x_fit, y_fit, xpred, ypred, x_eol, ymodel, RMSE, residuals = super(AutoPredictor, self).fit_predict(df, eol,
                                                                                                            fit_time_window,
                                                                                                            pred_fact,
                                                                                                            outlier)

        # TODO: Decide if calculating residuals of full data or only on data that is used for fit
        print(RMSE)
        x0, y0, a1, c1, a2, c2 = self.popt
        model = {'Equation': 'a1*x^c1 + y0 -a1*x0^c1 | a2*x^c2 + y0 -a2*x0^c2',
                 'Parameter': {0: {'Name': 'x0 (Cut Position)', 'Value': x0},
                               1: {'Name': 'y0', 'Value': y0},
                               2: {'Name': 'a1', 'Value': a1},
                               3: {'Name': 'c1', 'Value': c1},
                               4: {'Name': 'a2', 'Value': a2},
                               5: {'Name': 'c2', 'Value': c2}}}
        return xpred, ypred, x_fit.reshape(-1, ), residuals, model, RMSE, x_eol

    @staticmethod
    def model(x, x0, y0, a1, c1, a2, c2):
        y = np.piecewise(x, [x < x0, x >= x0],
                         [lambda x: a1 * x ** c1 + y0 - (a1 * x0 ** c1), lambda x: a2 * x ** c2 + y0 - (a2 * x0 ** c2)])
        return y
