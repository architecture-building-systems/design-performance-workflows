# vim: set fileencoding=utf-8 :
# This file is licensed under the terms of the MIT license. See the file
# "LICENSE.txt" in the project root for more information.
#
# This module was developed by Daren Thomas at the assistant chair for
# Sustainable Architecture and Building Technologies (Suat) at the Institute of
# Technology in Architecture, ETH Zürich. See http://suat.arch.ethz.ch for
# more information.
'''
A collection of modules used for the UMEM project.
'''
identifier = 'ch.ethz.arch.suat.umem'
name = 'UMEM'
version = '0.1.0'

from vistrails.core.configuration import ConfigurationObject
configuration = ConfigurationObject(test='blah')
configuration = ConfigurationObject(
    RESULTS_PATH=r'C:\Dropbox\SuAT\UMEM\BimWorkflow\Comparison_dpv_citysimd',  # noqa
    DPWS_URL='http://sustain.arch.ethz.ch/DpTkWs/DpTkWs.asmx?wsdl',
    BIM_URL='http://localhost:8010/snapshot',
    ENERGYPLUSTOFMU_PATH=r'C:\EnergyPlusToFMU-1.0.3\Scripts\EnergyPlusToFMU.py',  # noqa
    ENERGYPLUS_IDD_PATH=r'C:\EnergyPlusV8-2-0\Energy+.idd',
    ENERGYPLUS_PATH=r'C:\EnergyPlusV8-2-0\EnergyPlus.exe',
    CITYSIM_PATH=r"C:\Dropbox\SuAT\UMEM\CitySim\CitySim_fmi_version\CitySim.exe",  # noqa
    CITYSIMD_PATH=r"C:\Dropbox\SuAT\UMEM\CitySim\CitySim_fmi_version\CitySimd.exe")  # noqa
