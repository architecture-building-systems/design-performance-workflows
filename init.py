# vim: set fileencoding=utf-8 :
# This file is licensed under the terms of the MIT license. See the file
# "LICENSE.txt" in the project root for more information.
#
# This module was developed by Daren Thomas at the assistant chair for
# Architecture and Building Systems (A/S) at the Institute of
# Technology in Architecture, ETH Zürich. See http://systems.arch.ethz.ch for
# more information.

from vistrails.core.modules.vistrails_module import NotCacheable, Module
import vistrails.core.modules.basic_modules as basic

import xml.etree.ElementTree as ET
import tempfile
import subprocess
import os
import datetime

# set up logging
import logging
LOG_FILENAME = os.path.join(tempfile.gettempdir(),
                            'UmemVistrailsModules.log')
logging.basicConfig(filename=LOG_FILENAME,
                    level=logging.INFO)


class AcquireModelSnapshot(NotCacheable, Module):
    '''
    AcquireModelSnapshot acquires an xml serialization of a ModelSnapshot
    from Revit Architecture using the DesignPerformanceViewer plugin.

    It is dependant on the BIM_URL configuration parameter, that points
    to the DPV web server (typically localhost on port 8010, but the
    port can be changed in the DPV configuration file).
    '''
    _output_ports = [('snapshot', basic.String)]

    def compute(self):
        import urllib2
        url = configuration.BIM_URL
        logger = logging.getLogger('UMEM.AcquireModelSnapshot')
        logger.info('url=%s', url)
        content = urllib2.urlopen(url).read()
        self.setResult('snapshot', content)


class GenerateIdf(NotCacheable, Module):
    '''
    Send a ModelSnapshot to the BIM/DPV to be converted to an IDF file.
    '''
    _input_ports = [('snapshot', basic.String)]
    _output_ports = [('idf', basic.String)]

    def compute(self):
        import requests
        url = 'http://localhost:8014/idf'
        logger = logging.getLogger('UMEM.GenerateIdf')
        logger.info('url=%s', url)
        snapshot = self.getInputFromPort('snapshot')
        r = requests.post(url, snapshot)
        self.setResult('idf', r.text)


class AddFmuToIdf(NotCacheable, Module):
    '''
    Augment the IDF file with the information necessary for EnergyPlusToFMU
    and implement the CitySim/EnergyPlus interface.
    '''
    _input_ports = [('idf', basic.String)]
    _output_ports = [('idf', basic.String)]

    def compute(self):
        import addfmutoidf
        reload(addfmutoidf)
        idf = self.getInputFromPort('idf')

        TMP_PATH = tempfile.gettempdir()
        with open(os.path.join(TMP_PATH, 'addfmutoidf.in.idf'), 'w') as out:
            out.write(idf)
        idf = addfmutoidf.writeidf(addfmutoidf.process_idf(idf))
        with open(os.path.join(TMP_PATH, 'addfmutoidf.out.idf'), 'w') as out:
            out.write(idf)
        self.setResult('idf', idf)


class AddFmuToIdfLwr(NotCacheable, Module):
    """
    Augment the IDF file with the information necessary for EnergyPlusToFMU
    and implement the CitySim/EnergyPlus interface. Includes the interface
    for LWR (replaces AddFmuToIdf)
    """
    _input_ports = [('idf', basic.String)]
    _output_ports = [('idf', basic.String)]

    def compute(self):
        import addfmutoidf
        reload(addfmutoidf)
        import tempfile
        idf = self.getInputFromPort('idf')

        TMP_PATH = tempfile.gettempdir()
        with open(os.path.join(
                  TMP_PATH, 'addfmutoidflwr.in.idf'), 'w') as out:
            out.write(idf)
        idf = addfmutoidf.writeidf(addfmutoidf.process_idf_lwr(idf))
        with open(os.path.join(
                  TMP_PATH, 'addfmutoidflwr.out.idf'), 'w') as out:
            out.write(idf)
        self.setResult('idf', idf)


class RunEnergyPlus(NotCacheable, Module):
    """
    Run an IDF file with EnergyPlus in a temporary folder using a
    Weatherfile.

    The idf is expected to be a string containing the contents of the file.
    The epw_path is expected to be the path to a *.epw weather file.
    """
    _input_ports = [('idf', basic.String),
                    ('epw_path', basic.String),
                    ('energyplus_path', basic.String, {'optional': True})]
    _output_ports = [('results_path', basic.String)]

    def compute(self):
        import os
        import shutil
        idf = self.getInputFromPort('idf')
        epw_path = self.getInputFromPort('epw_path')
        energyplus_path = self.forceGetInputFromPort(
            'energyplus_path',
            configuration.ENERGYPLUS_PATH)
        logger = logging.getLogger('UMEM.RunEnergyPlus')
        logger.info('epw_path=%s', epw_path)

        tmp = tempfile.mkdtemp(
            prefix=datetime.datetime.now().strftime('%Y.%m.%d.%H.%M.%S')
            + "_RunEnergyPlus_")
        logger.info('cwd=%s', tmp)
        idf_path = os.path.join(tmp, 'in.idf')
        with open(idf_path, 'w') as out:
            out.write(idf)
        logger.info('idf_path=%s', idf_path)
        shutil.copy(configuration.ENERGYPLUS_IDD_PATH, tmp)
        shutil.copyfile(epw_path, os.path.join(tmp, 'in.epw'))

        logger.info('energyplus_path=%s', energyplus_path)
        subprocess.check_call([energyplus_path],
                              cwd=tmp)

        self.setResult('results_path', tmp)


class SaveResults(NotCacheable, Module):
    """
    Save a results file to the RESULTS_PATH for further
    analysis.
    """
    _input_ports = [('base_path', basic.String),
                    ('relative_path', basic.String),
                    ('new_file_name', basic.String)]

    def compute(self):
        import shutil
        import os
        base_path = self.getInputFromPort('base_path')
        relative_path = self.getInputFromPort('relative_path')
        new_file_name = self.getInputFromPort('new_file_name')
        shutil.copyfile(os.path.join(base_path, relative_path),
                        os.path.join(
                            configuration.RESULTS_PATH,
                            new_file_name))


class SaveEnergyPlusResults(NotCacheable, Module):
    """
    Save the results of an EnergyPlus run (.eso, .err file)
    to a specified directory, renaming them...

    use the output from RunEnergyPlus (results_path) as the input
    to source_path.
    use a directory name for target_path.
    use a basename for target_name (like: test01).
    """
    _input_ports = [('source_path', basic.String),
                    ('target_path', basic.String),
                    ('target_name', basic.String)]

    def compute(self):
        import shutil
        import os
        source_path = self.getInputFromPort('source_path')
        target_path = self.getInputFromPort('target_path')
        target_name = self.getInputFromPort('target_name')
        shutil.copyfile(os.path.join(source_path, 'eplusout.eso'),
                        os.path.join(target_path, target_name + '.eso'))
        shutil.copyfile(os.path.join(source_path, 'eplusout.err'),
                        os.path.join(target_path, target_name + '.err'))
        shutil.copyfile(os.path.join(source_path, 'eplusout.rdd'),
                        os.path.join(target_path, target_name + '.rdd'))
        shutil.copyfile(os.path.join(source_path, 'in.idf'),
                        os.path.join(target_path, target_name + '.idf'))


class SaveCoSimResults(NotCacheable, Module):
    """
    Save the results of a co-simulation run (.eso, .err file, but also the
    CitySim stuff) to a specified directory, renaming them...

    use the output from RunCoSimulation
    (citysim_basename, results_path, eplus_basename)
    """
    _input_ports = [('source_path', basic.String),
                    ('citysim_basename', basic.String),
                    ('eplus_basename', basic.String),
                    ('target_path', basic.String),
                    ('target_basename', basic.String)]

    def compute(self):
        import shutil
        import os
        source_path = self.getInputFromPort('source_path')
        citysim_basename = self.getInputFromPort('citysim_basename')
        eplus_basename = self.getInputFromPort('eplus_basename')
        target_path = self.getInputFromPort('target_path')
        target_basename = self.getInputFromPort('target_basename')
        shutil.copyfile(os.path.join(source_path, eplus_basename + '.eso'),
                        os.path.join(target_path, target_basename + '.eso'))
        shutil.copyfile(os.path.join(source_path, eplus_basename + '.err'),
                        os.path.join(target_path, target_basename + '.err'))
        shutil.copyfile(os.path.join(source_path, eplus_basename + '.rdd'),
                        os.path.join(target_path, target_basename + '.rdd'))
        shutil.copyfile(os.path.join(source_path, eplus_basename + '.idf'),
                        os.path.join(target_path, target_basename + '.idf'))
        shutil.copyfile(os.path.join(source_path,
                                     citysim_basename + '_TH.out'),
                        os.path.join(target_path, target_basename + '_TH.out'))
        shutil.copyfile(os.path.join(source_path, citysim_basename + '.xml'),
                        os.path.join(target_path, target_basename + '.xml'))


class StripInternalLoads(NotCacheable, Module):
    """
    Remove these objects:

    People, IntGainsPeop_DEFAULT_ZONE, DEFAULT_ZONE, OccupationSchedule, ...

    Schedule:Compact, OccupationSchedule, ...

    Lights, Lights_DEFAULT_ZONE, DEFAULT_ZONE, LightSchedule, Watts/Area, 0,
    10.7600, , 0.2000, 0.2, 0.2, 1, General, , , ;

    ElectricEquipment, ElectricEquipment_DEFAULT_ZONE, DEFAULT_ZONE,
    EquipSchedule, Watts/Area, 0, 13.9900, 0, 0, 0.5000, 0, General;

    Perhaps we should we take out infiltration/ventilation:

    ZoneInfiltration:DesignFlowRate, DEFAULT_ZONE_Infiltration, DEFAULT_ZONE,
    InfiltrationSchedule, AirChanges/Hour, , , , 0.4000, 1, 0, 0, 0;

    ZoneVentilation:DesignFlowRate, DEFAULT_ZONE_VentilationSystem,
    DEFAULT_ZONE, VentilationSchedule, AirChanges/Hour, , , , 0.7000, Natural,
    0.0000, 1.0000, 1,
    0, 0, 0, 20, , 100, , 1, , -10, , 26, , 40;
    """
    _input_ports = [('idf', basic.String)]
    _output_ports = [('idf', basic.String)]

    def compute(self):
        import stripinternalloads
        reload(stripinternalloads)
        idf = self.getInputFromPort('idf')
        TMP_PATH = r'C:\Users\darthoma\AppData\Local\Temp'
        with open(os.path.join(TMP_PATH, 'strip.in.idf'), 'w') as out:
            out.write(idf)
        idf = stripinternalloads.process_idf(idf)
        with open(os.path.join(TMP_PATH, 'strip.out.idf'), 'w') as out:
            out.write(idf)
        self.setResult('idf', idf)


class EnergyPlusToFmu(NotCacheable, Module):
    """Run the EnergyPlusToFMU.py script. Use VisTrails
    variables to configure where the script is.
    """
    _input_ports = [('idf', basic.String),
                    ('epw_path', basic.String),
                    ('EnergyPlusToFmu_path', basic.Path, {'optional': True})]
    _output_ports = [('fmu_path', basic.String)]

    def compute(self):
        try:
            path = self.forceGetInputFromPort(
                'EnergyPlusToFmu_path', configuration.ENERGYPLUSTOFMU_PATH)
            if hasattr(path, 'name'):
                path = path.name
            idd_path = configuration.ENERGYPLUS_IDD_PATH
            idf = self.getInputFromPort('idf')
            epw_path = self.getInputFromPort('epw_path')
            idf_fd, idf_path = tempfile.mkstemp(suffix='.idf')
            logger = logging.getLogger('UMEM.EnergyPlusToFmu')
            logger.info('idf_path=%s', idf_path)
            with os.fdopen(idf_fd, 'w') as idf_file:
                idf_file.write(idf)
            cwd = tempfile.gettempdir()
            logger.info('cwd=%s', cwd)
            logger.info('EnergyPlusToFmu_path=%s', path)
            subprocess.check_call(['python', path,
                                   '-i', idd_path,
                                   '-d', '-L',
                                   '-w', epw_path,
                                   idf_path],
                                  cwd=cwd)
            self.setResult('fmu_path', idf_path[:-4] + '.fmu')
            logger.info('fmu_path=%s', idf_path[:-4] + '.fmu')
        except:
            logger.exception('Could not generate FMU')
            raise


class RevitToCitySim(NotCacheable, Module):
    """Extract a CitySim scene from Revit using the RPS
    (see also r2cs_server.py)"""

    _output_ports = [('citysim_xml', basic.String)]

    def compute(self):
        import urllib2
        url = 'http://localhost:8014/revittocitysim'
        logger = logging.getLogger('UMEM.RevitToCitySim')
        logger.info('url=%s', url)
        content = urllib2.urlopen(url).read()
        self.setResult('citysim_xml', content)


class RunCoSimulation(NotCacheable, Module):
    """Run the co-simulation EnergyPlus/CitySim"""
    _input_ports = [('citysim_xml', basic.String),
                    ('fmu_path', basic.String),
                    ('cli_path', basic.String)]
    _output_ports = [('results_path', basic.String),
                     ('citysim_basename', basic.String),
                     ('eplus_basename', basic.String)]

    def compute(self):
        citysim_xml = self.getInputFromPort('citysim_xml')
        fmu_path = self.getInputFromPort('fmu_path')
        cli_path = self.getInputFromPort('cli_path')
        tmp = tempfile.mkdtemp(
            prefix=datetime.datetime.now().strftime('%Y.%m.%d.%H.%M.%S')
            + "_RunCoSimulation_")
        logger = logging.getLogger('UMEM.RunCoSimulation')
        logger.info('fmu_path=%s', fmu_path)
        logger.info('cli_path=%s', cli_path)
        logger.info('tmp=%s', tmp)
        root = ET.fromstring(citysim_xml)
        root.find('Climate').set('location', cli_path)
        building = root.find(".//Building[@Simulate='ep']")
        building.set('fmu', fmu_path)
        building.set('tmp', tmp)
        citysim_xml_fd, citysim_xml_path = tempfile.mkstemp(
            suffix='.xml', dir=tmp)
        with os.fdopen(citysim_xml_fd, 'w') as citysim_xml_file:
            ET.ElementTree(root).write(citysim_xml_file)
        logger.info('%s %s', configuration.CITYSIMD_PATH, citysim_xml_path)
        subprocess.check_call([configuration.CITYSIMD_PATH,
                               citysim_xml_path],
                              cwd=tmp)
        self.setResult('results_path', tmp)
        self.setResult('citysim_basename',
                       os.path.basename(citysim_xml_path)[:-4])
        self.setResult('eplus_basename',
                       os.path.join('Output_EPExport_RevitToCitySim',
                                    os.path.basename(fmu_path)[:-4]))


class RunMockCoSimulation(NotCacheable, Module):
    """Run the co-simulation with the Mock instead of CitySim"""
    _input_ports = [('fmu_path', basic.String),
                    ('mock_path', basic.String)]
    _output_ports = [('results_path', basic.String)]

    def compute(self):
        fmu_path = self.getInputFromPort('fmu_path')
        mock_path = self.getInputFromPort('mock_path')
        tmp = tempfile.mkdtemp(
            prefix=datetime.datetime.now().strftime('%Y.%m.%d.%H.%M.%S')
            + "_RunMockCoSimulation_")
        logger = logging.getLogger('UMEM.RunMockCoSimulation')
        logger.info('fmu_path=%s', fmu_path)
        logger.info('mock_path=%s', mock_path)
        logger.info('tmp=%s', tmp)
        subprocess.check_call([mock_path,
                               fmu_path,
                               tmp],
                              cwd=tmp)
        self.setResult('results_path', tmp)


class RunCitySim(NotCacheable, Module):
    """Run just the CitySim simulation (no co-simulation)"""
    _input_ports = [('citysim_xml', basic.String),
                    ('cli_path', basic.String)]
    _output_ports = [('results_path', basic.String),
                     ('citysim_basename', basic.String)]

    def compute(self):
        citysim_xml = self.getInputFromPort('citysim_xml')
        cli_path = self.getInputFromPort('cli_path')
        tmp = tempfile.mkdtemp(
            prefix=datetime.datetime.now().strftime('%Y.%m.%d.%H.%M.%S')
            + "_RunCitySim_")
        logger = logging.getLogger('UMEM.RunCitySim')
        logger.info('cli_path=%s', cli_path)
        logger.info('cwd=%s', tmp)
        logger.info('citysim_xml_path=%s', citysim_xml)
        logger.info('CITYSIM_PATH=%s', configuration.CITYSIM_PATH)
        root = ET.fromstring(citysim_xml)
        root.find('Climate').set('location', cli_path)
        building = root.find(".//Building[@Simulate='ep']")
        building.set('Simulate', 'true')
        citysim_xml_fd, citysim_xml_path = tempfile.mkstemp(
            suffix='.xml', dir=tmp)
        with os.fdopen(citysim_xml_fd, 'w') as citysim_xml_file:
            ET.ElementTree(root).write(citysim_xml_file)
        subprocess.check_call([configuration.CITYSIM_PATH,
                               citysim_xml_path],
                              cwd=tmp)
        self.setResult('results_path', tmp)
        self.setResult('citysim_basename',
                       os.path.basename(citysim_xml_path)[:-4])


class XPath(NotCacheable, Module):
    '''
    applies an XPATH expression to a string containing
    xml code. The result is a list of matches, each
    converted back to strings.
    '''
    _input_ports = [
        ('xml', basic.String),
        ('xpath', basic.String)]
    _output_ports = [('matches', basic.List)]

    def compute(self):
        from lxml import etree
        xml = self.getInputFromPort('xml')
        xpath = self.getInputFromPort('xpath')
        print 'xpath:', xpath, type(xpath)
        tree = etree.fromstring(xml)
        matches = tree.xpath(xpath)

        def s(e):
            if isinstance(e, etree._Element):
                return etree.tostring(e)
            return e
        matches = [s(e) for e in matches]
        self.setResult('matches', matches)


class XPathSetAttribute(NotCacheable, Module):
    '''
    applies an XPATH expression to a string containing
    xml code. The result is a list of matches, each
    converted back to strings.
    '''
    _input_ports = [
        ('xml', basic.String),
        ('xpath', basic.String),
        ('attrib', basic.String),
        ('new_value', basic.String)]
    _output_ports = [('xml', basic.String)]

    def compute(self):
        from xml.etree import ElementTree as etree
        xml = self.getInputFromPort('xml')
        xpath = self.getInputFromPort('xpath')
        attrib = self.getInputFromPort('attrib')
        new_value = self.getInputFromPort('new_value')
        tree = etree.fromstring(xml)
        for element in tree.findall(xpath):
            element.set(attrib, new_value)
        self.setResult('xml', etree.tostring(tree))


class AddOutputVariable(NotCacheable, Module):
    '''
    adds an Output:Variable object to the IDF file.
    input and output are both strings containing the
    contents of the IDF file (as opposed to paths)
    '''
    _input_ports = [
        ('idf', basic.String),
        ('idd_path', basic.Path),
        ('key', basic.String),
        ('variable', basic.String),
        ('frequency', basic.String)]

    _output_ports = [('idf', basic.String)]

    def compute(self):
        from eppy.modeleditor import IDF, IDDAlreadySetError
        from StringIO import StringIO
        logger = logging.getLogger('UMEM.AddOutputVariable')

        idf_as_string = self.getInputFromPort('idf')
        key = self.getInputFromPort('key')
        variable = self.getInputFromPort('variable')
        frequency = self.getInputFromPort('frequency')
        idd_path = self.getInputFromPort('idd_path')

        logger.info('key=%s', key)
        logger.info('variable=%s', variable)
        logger.info('frequency=%s', frequency)
        logger.info('idd_path=%s', idd_path.name)

        try:
            IDF.setiddname(idd_path.name)
        except IDDAlreadySetError:
            pass

        idf = IDF(StringIO(idf_as_string))

        output_variable = idf.newidfobject('OUTPUT:VARIABLE')
        output_variable.Key_Value = key
        output_variable.Variable_Name = variable
        output_variable.Reporting_Frequency = frequency

        # output the result
        self.setResult('idf', idf.idfstr())


class AddOutputVariableList(NotCacheable, Module):
    '''
    adds an Output:Variable object to the IDF file
    for each variable name in `variables`.
    input and output are both strings containing the
    contents of the IDF file (as opposed to paths)
    '''
    _input_ports = [
        ('idf', basic.String),
        ('idd_path', basic.Path),
        ('key', basic.String),
        ('variables', basic.List),
        ('frequency', basic.String)]

    _output_ports = [('idf', basic.String)]

    def compute(self):
        from eppy.modeleditor import IDF, IDDAlreadySetError
        from StringIO import StringIO
        logger = logging.getLogger('UMEM.AddOutputVariableList')

        idf_as_string = self.getInputFromPort('idf')
        key = self.getInputFromPort('key')
        variables = self.getInputFromPort('variables')
        frequency = self.getInputFromPort('frequency')
        idd_path = self.getInputFromPort('idd_path')

        logger.info('key=%s', key)
        logger.info('variables=%s', variables)
        logger.info('frequency=%s', frequency)
        logger.info('idd_path=%s', idd_path.name)

        try:
            IDF.setiddname(idd_path.name)
        except IDDAlreadySetError:
            pass

        idf = IDF(StringIO(idf_as_string))

        for variable in variables:
            output_variable = idf.newidfobject('OUTPUT:VARIABLE')
            output_variable.Key_Value = key
            output_variable.Variable_Name = variable
            output_variable.Reporting_Frequency = frequency

        # output the result
        self.setResult('idf', idf.idfstr())


class FileToList(NotCacheable, Module):
    '''
    Read in a text file and output a list
    with one item per line in the text file.
    Whitespace is stripped from the front and back
    of each line (str.strip())
    '''
    _input_ports = [('file', basic.Path)]
    _output_ports = [('list', basic.List)]

    def compute(self):
        file_path = self.getInputFromPort('file').name
        with open(file_path, 'r') as f:
            result = [line.strip() for line in f]
        self.setResult('list', result)


_modules = [
    AcquireModelSnapshot,
    AddFmuToIdf,
    AddFmuToIdfLwr,
    AddOutputVariable,
    AddOutputVariableList,
    EnergyPlusToFmu,
    FileToList,
    GenerateIdf,
    RevitToCitySim,
    RunCitySim,
    RunEnergyPlus,
    RunCoSimulation,
    RunMockCoSimulation,
    StripInternalLoads,
    SaveEnergyPlusResults,
    SaveCoSimResults,
    SaveResults,
    XPath,
    XPathSetAttribute,
]
