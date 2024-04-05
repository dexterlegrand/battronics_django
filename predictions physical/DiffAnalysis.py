# -*- coding: utf-8 -*-
###############################################################################
#
# Import section
###############################################################################
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.util import loadmat

###############################################################################
#
# Header
###############################################################################
__author__ = ['Matthias Steck']
__maintainer__ = ['Matthias Steck']
__email__ = ['matthias.steck@bfh.ch']

"""
Created on Thu Jun 23 09:18:43 2022

@author: Sem7
"""
###############################################################################
#
# Methods
###############################################################################
def diff_analysis(s,win_len=50):
    """
    Diffrentiating data with a shift of 1 and then filtering with a
    rolling mean window of length win_len.

    Parameters
    ----------
    s : Series Pandas
        Series of data.
    win_len : int, optional
        Window length. The default is 50.

    Returns
    -------
    df_diffAnalysis : Series Pandas
        Series of diffrentiating and filtered data.

    """
    df_diff_analysis = s.diff().rolling(win_len,center=True,min_periods=1).mean()
    return df_diff_analysis


def plot_diff_analysis(ave_current, ave_voltage, voltage):
    diff_aveC_aveV = np.divide(ave_current, ave_voltage)
    plt.plot(voltage,diff_aveC_aveV)

    plt.title('Charge',fontweight='bold')
    plt.xlabel('U / V')
    plt.ylabel('|dQ/dU| / Ah*V^-1')

###############################################################################
 #
 # Main
###############################################################################

if __name__ == "__main__":
    
    
    print('Test diffAmalysis function with test data from matlab')
    filename = r"C:\Users\Sem7\Desktop\Temp\Projekte\ADB\Prelim. Diff. Analysis\Chargedata.mat"
    data = loadmat(filename)

    dataset01C = pd.DataFrame(data['Dataset01C']).iloc[353:34614:5,:]
    dataset05C = pd.DataFrame(data['Dataset05C']).iloc[300:6306:5,:]
    dataset1C = pd.DataFrame(data['Dataset1C']).iloc[397:3107:5,:]
    dataset2C = pd.DataFrame(data['Dataset2C']).iloc[397:1274:5,:]

    datasets = [dataset01C,
                dataset05C,
                dataset1C,
                dataset2C]

    dataset01C['ave_voltage'] = diff_analysis(dataset01C['U'],120)
    dataset01C['ave_current'] = diff_analysis(dataset01C['AhCharge'],120)

    dataset05C['ave_voltage'] = diff_analysis(dataset05C['U'],50)
    dataset05C['ave_current'] = diff_analysis(dataset05C['AhCharge'],50)

    dataset1C['ave_voltage'] = diff_analysis(dataset1C['U'],30)
    dataset1C['ave_current'] = diff_analysis(dataset1C['AhCharge'],30)

    dataset2C['ave_voltage'] = diff_analysis(dataset2C['U'],7)
    dataset2C['ave_current'] = diff_analysis(dataset2C['AhCharge'],7)

    for item in datasets:
        plot_diff_analysis(item['ave_current'],item['ave_voltage'],item['U'])

    plt.legend(['C/10', 'C/2', '1C', '2C'])
    plt.grid()
