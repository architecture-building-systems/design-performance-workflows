# vim: set fileencoding=utf-8 :
# This file is licensed under the terms of the MIT license. See the file
# "LICENSE.txt" in the project root for more information.
#
# This module was developed by Daren Thomas at the assistant chair for
# Architecture and Building Systems (A/S) at the Institute of
# Technology in Architecture, ETH Zuerich. See http://systems.arch.ethz.ch for
# more information.

from vistrails.core.modules.vistrails_module import (
    NotCacheable, Module, IPort, OPort)
import vistrails.core.modules.basic_modules as basic

import tempfile
import subprocess
import os
import datetime
from lxml import etree


class XmlElementTree(NotCacheable, Module):
    '''
    A module to use as output and input ports that contain
    XML data.

    CONVENTION: ports with type XmlElementTree exchange
    xml.etree.ElementTree objects.
    '''
    _input_ports = [IPort(name='file',
                          signature='basic:File',
                          label='An XML file to read')]
    _output_ports = [OPort(name='xml',
                           signature='ch.ethz.arch.systems.design-performance-workflows:XmlElementTree')]  # noqa

    def compute(self):
        from lxml import etree
        path = self.get_input('file')
        xml = etree.parse(open(path, 'r'))
        self.set_output('xml', xml)


class ModelSnapshot(XmlElementTree):
    '''
    Wraps an XML serialization of a DPV ModelSnapshot object
    for use in the VisTrails system.

    CONVENTION: ports with type ModelSnapshot exchange
    xml.etree.ElementTree objects.
    '''
    _input_ports = [IPort(name='file',
                          signature='basic:File',
                          label='An XML file to read')]
    _output_ports = [OPort(name='snapshot',
                           signature='ch.ethz.arch.systems.design-performance-workflows:ModelSnapshot')]  # noqa

    def compute(self):
        path = self.get_input('file')
        snapshot = etree.parse(open(path, 'r'))
        self.set_output('snapshot', snapshot)


class CitySimXml(XmlElementTree):
    '''
    Wraps the XML file used to describe a CitySim scene for
    use in the VisTrails system.

    CONVENTION: ports with type CitySimXml exchange
    xml.etree.ElementTree objects.
    '''
    _input_ports = [IPort(name='file',
                          signature='basic:File',
                          label='A CitySim XML file to read')]
    _output_ports = [OPort(name='citysim_xml',
                           signature='ch.ethz.arch.systems.design-performance-workflows:CitySimXml')]  # noqa

    def compute(self):
        path = self.get_input('file').name
        scene = etree.parse(open(path, 'r'))
        self.set_output('citysim_xml', scene)


class Idf(NotCacheable, Module):

    '''
    Wraps an eppy IDF3 object for use in the VisTrails system.

    the default EnergyPlus IDD file will be used if none is
    specified. This is done by looking through $PATH to find
    the EnergyPlus executable and use the `Energy+.idd` file
    in the same folder.

    CONVENTION: ports with type Idf exchange eppy.IDF instances.
    '''
    _input_ports = [
        IPort(name='idf',
              signature='basic:Path',
              optional=True),
        IPort(name='idd',
              signature='basic:Path'),
    ]
    _output_ports = [OPort(name='idf',
                           signature='ch.ethz.arch.systems.design-performance-workflows:Idf')]  # noqa

    def compute(self):
        from eppy.modeleditor import IDF, IDDAlreadySetError
        from StringIO import StringIO

        idf = self.force_get_input('idf', None)
        idd = self.get_input('idd').name

        try:
            IDF.setiddname(idd)
        except IDDAlreadySetError:
            pass

        if idf:
            idf_file = open(idf.name, 'r')
        else:
            idf_file = StringIO('')
        self.idf = IDF(idf_file)
        self.set_output('idf', self.idf)


class AcquireModelSnapshot(NotCacheable, Module):
    '''
    AcquireModelSnapshot acquires an xml serialization of a ModelSnapshot
    from Revit Architecture using the DesignPerformanceViewer plugin.

    It is dependant on the BIM_URL configuration parameter, that points
    to the DPV web server (typically localhost on port 8010, but the
    port can be changed in the DPV configuration file).
    '''
    _input_ports = [IPort(name='url',
                          signature='basic:String',
                          label='URL of DPV BIM snapshot extraction',
                          default='http://localhost:8010/snapshot',
                          optional=True)]

    _output_ports = [OPort(name='snapshot',
                           signature='ch.ethz.arch.systems.design-performance-workflows:ModelSnapshot')]  # noqa

    def compute(self):
        url = self.get_input('url')
        snapshot = etree.parse(url)
        self.set_output('snapshot', snapshot)


class GenerateIdf(NotCacheable, Module):
    '''
    Send a ModelSnapshot to the BIM/DPV to be converted to an IDF file.
    '''
    _input_ports = [IPort(name='snapshot',
                          signature='ch.ethz.arch.systems.design-performance-workflows:ModelSnapshot'),  # noqa
                    IPort(name='url',
                          signature='basic:String',
                          default='http://localhost:8014/idf',
                          optional=True),
                    IPort(name='idd',
                        signature='basic:Path',
                        optional=True)]
    _output_ports = [OPort(name='idf',
                           signature='ch.ethz.arch.systems.design-performance-workflows:Idf')]  # noqa

    def compute(self):
        import requests
        from eppy.modeleditor import IDF, IDDAlreadySetError
        from StringIO import StringIO

        url = self.get_input('url')
        snapshot = self.get_input('snapshot')
        r = requests.post(url, etree.tostring(snapshot))
        if r.ok:
            idf_file = StringIO(r.text.strip().replace('\r\n', '\n'))
            idd = force_get_path(self, 'idd', find_idd())
            try:
                IDF.setiddname(idd)
            except IDDAlreadySetError:
                pass
            self.idf = IDF(idf_file)
            self.set_output('idf', self.idf)
        else:
            raise Exception('Could not request IDF from BIM')



class AddFmuToIdfLwr(NotCacheable, Module):

    """ Augment the IDF file with the information necessary for EnergyPlusToFMU
    and implement the CitySim/EnergyPlus interface. Includes the interface
    for LWR (replaces AddFmuToIdf)
    """
    _input_ports = [IPort(
        name='idf',
        signature='ch.ethz.arch.systems.design-performance-workflows:Idf')]
    _output_ports = [OPort(
        name='idf',
        signature='ch.ethz.arch.systems.design-performance-workflows:Idf')]

    def compute(self):
        import addfmutoidf
        reload(addfmutoidf)
        idf = self.get_input('idf')
        idf = addfmutoidf.process_idf(idf)
        self.set_output('idf', idf)


class RunEnergyPlus(NotCacheable, Module):
    """
    Run an IDF file with EnergyPlus in a temporary folder using a
    Weatherfile.

    The idf is expected to be a string containing the contents of the file.
    The epw_path is expected to be the path to a *.epw weather file.
    """
    _input_ports = [('idf', Idf),
                    ('epw', basic.File),
                    ('idd', basic.File, {'optional': True}),
                    ('energyplus', basic.File, {'optional': True})]
    _output_ports = [('results', basic.Path)]

    def compute(self):
        import shutil
        idf = self.get_input('idf')
        idd_path = force_get_path(self, 'idd', find_idd())
        epw_path = self.get_input('epw').name
        energyplus_path = force_get_path(self, 'energyplus', find_energyplus())
        tmp = tempfile.mkdtemp(
            prefix=datetime.datetime.now().strftime('%Y.%m.%d.%H.%M.%S')
            + "_RunEnergyPlus_")
        idf_path = os.path.join(tmp, 'in.idf')
        with open(idf_path, 'w') as out:
            out.write(idf.idfstr())
        shutil.copy(idd_path, tmp)
        shutil.copyfile(epw_path, os.path.join(tmp, 'in.epw'))
        subprocess.check_call([energyplus_path],
                              cwd=tmp)
        self.set_output('results', basic.PathObject(tmp))


class SaveEnergyPlusResults(NotCacheable, Module):
    """
    Save the results of an EnergyPlus run (.eso, .err file)
    to a specified directory, renaming them...

    use the output from RunEnergyPlus (results_path) as the input
    to source_path.
    use a directory name for target_path.
    use a basename for target_name (like: test01).
    """
    _input_ports = [('source_path', basic.Path),
                    ('target_path', basic.Path),
                    ('target_name', basic.String)]

    def compute(self):
        import shutil
        source_path = self.get_input('source_path').name
        target_path = self.get_input('target_path').name
        target_name = self.get_input('target_name')
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


class SaveCitySimResults(NotCacheable, Module):
    """
    Save the results of a CitySim simulation run to a specified directory,
    renaming them...

    use the output from RunCitySim
    (citysim_basename, results_path)
    """
    _input_ports = [IPort(name='source_path',
                          signature='basic:Directory'),
                    IPort(name='citysim_basename',
                          signature='basic:String'),
                    IPort(name='target_path',
                          signature='basic:Directory'),
                    IPort(name='target_basename',
                          signature='basic:String')]

    def compute(self):
        import shutil
        import os
        source_path = self.getInputFromPort('source_path').name
        citysim_basename = self.getInputFromPort('citysim_basename')
        target_path = self.getInputFromPort('target_path').name
        target_basename = self.getInputFromPort('target_basename')
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
    _input_ports = [
        IPort(
            name='idf',
            signature='ch.ethz.arch.systems.design-performance-workflows:Idf'),
        IPort(name='epw_path', signature='basic:Path'),
        IPort(name='EnergyPlusToFmu_path', signature='basic:Path'),
        IPort(name='idd_path', signature='basic:Path')]
    _output_ports = [
        OPort(name='fmu_path', signature='basic:Path')]

    def compute(self):
        try:
            ep2fmu_path = self.get_input('EnergyPlusToFmu_path').name
            idd_path = self.get_input('idd_path').name
            idf = self.get_input('idf')
            epw_path = self.get_input('epw_path').name
            idf_fd, idf_path = tempfile.mkstemp(suffix='.idf')
            with os.fdopen(idf_fd, 'w') as idf_file:
                idf_file.write(idf.idfstr())
            cwd = tempfile.gettempdir()
            subprocess.check_call(['python', ep2fmu_path,
                                   '-i', idd_path,
                                   '-d', '-L',
                                   '-w', epw_path,
                                   idf_path],
                                  cwd=cwd)
            self.setResult('fmu_path', basic.PathObject(idf_path[:-4] + '.fmu'))
        except:
            raise


class RevitToCitySim(NotCacheable, Module):
    """Extract a CitySim scene from Revit using the RPS
    (see also r2cs_server.py)"""

    _output_ports = [('citysim_xml', basic.String)]

    def compute(self):
        import urllib2
        url = 'http://localhost:8014/revittocitysim'
        content = urllib2.urlopen(url).read()
        self.setResult('citysim_xml', content)


class RunCoSimulation(NotCacheable, Module):
    """Run the co-simulation EnergyPlus/CitySim"""
    _input_ports = [
        IPort(
            name='citysim',
            signature='ch.ethz.arch.systems.design-performance-workflows:CitySimXml'),
                    ('fmu_path', basic.Path),
                    ('cli_path', basic.Path),
                    ('citysim_path', basic.Path)]
    _output_ports = [('results_path', basic.String),
                     ('citysim_basename', basic.String),
                     ('eplus_basename', basic.String)]

    def compute(self):
        citysim_xml = self.get_input('citysim')
        fmu_path = self.get_input('fmu_path').name
        cli_path = self.getInputFromPort('cli_path').name
        citysim_path = self.get_input('citysim_path').name
        tmp = tempfile.mkdtemp(
            prefix=datetime.datetime.now().strftime('%Y.%m.%d.%H.%M.%S')
            + "_RunCoSimulation_")
        root = citysim_xml.getroot()
        root.find('Climate').set('location', cli_path)
        building = root.find(".//Building[@Simulate='ep']")
        assert building, 'CitySimXml does not contain a Building with Simulate="ep"'
        building.set('fmu', fmu_path)
        building.set('tmp', tmp)
        citysim_xml_fd, citysim_xml_path = tempfile.mkstemp(
            suffix='.xml', dir=tmp)
        with os.fdopen(citysim_xml_fd, 'w') as citysim_xml_file:
            etree.ElementTree(root).write(citysim_xml_file)
        subprocess.check_call([citysim_path,
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
        subprocess.check_call([mock_path,
                               fmu_path,
                               tmp],
                              cwd=tmp)
        self.setResult('results_path', tmp)


class RunCitySim(NotCacheable, Module):
    """Run just the CitySim simulation (no co-simulation)"""
    _input_ports = [IPort(name='citysim_xml',
                          signature='ch.ethz.arch.systems.design-performance-workflows:CitySimXml'),
                    IPort(name='cli_path',
                          signature='basic:File',
                          label='Path to the .cli (weather) file to use for simulation.'),
                    IPort(name='citysim_exe',
                          signature='basic:File',
                          label='CitySim.exe')]
    _output_ports = [OPort(name='results_path',
                           signature='basic:Directory'),
                     OPort(name='citysim_basename',
                           signature='basic:String')]

    def compute(self):
        citysim_xml = self.get_input('citysim_xml')
        cli_path = self.get_input('cli_path').name
        citysim_exe = self.get_input('citysim_exe').name
        tmp = tempfile.mkdtemp(
            prefix=datetime.datetime.now().strftime('%Y.%m.%d.%H.%M.%S')
            + "_RunCitySim_")
        root = citysim_xml.getroot()
        root.find('Climate').set('location', cli_path)
        # make sure we turn off co-simulation buildings:
        for building in root.findall(".//Building[@Simulate='ep']"):
            building.set('Simulate', 'true')
        citysim_xml_fd, citysim_xml_path = tempfile.mkstemp(
            suffix='.xml', dir=tmp)
        with os.fdopen(citysim_xml_fd, 'w') as citysim_xml_file:
            citysim_xml.write(citysim_xml_file)
        subprocess.check_call([citysim_exe,
                               citysim_xml_path],
                              cwd=tmp)
        self.set_output('results_path', basic.PathObject(tmp))
        self.set_output('citysim_basename',
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

        idf_as_string = self.getInputFromPort('idf')
        key = self.getInputFromPort('key')
        variable = self.getInputFromPort('variable')
        frequency = self.getInputFromPort('frequency')
        idd_path = self.getInputFromPort('idd_path')


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

        idf_as_string = self.getInputFromPort('idf')
        key = self.getInputFromPort('key')
        variables = self.getInputFromPort('variables')
        frequency = self.getInputFromPort('frequency')
        idd_path = self.getInputFromPort('idd_path')


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


class CitySimToEnergyPlus(NotCacheable, Module):
    '''
    Extract an EnergyPlus model from a CitySim scene.
    Uses the CitySim building id to find the building to
    extract and uses a template for the single zone HVAC
    system added. The script adds the materials and
    constructions and surfaces to the template.
    '''
    _input_ports = [IPort(name='citysim',
                          signature='ch.ethz.arch.systems.design-performance-workflows:CitySimXml'),
                    IPort(name='building',
                          signature='basic:String'),
                    IPort(name='template',
                          signature='ch.ethz.arch.systems.design-performance-workflows:Idf')]
    _output_ports = [OPort(name='idf',
                           signature='ch.ethz.arch.systems.design-performance-workflows:Idf')]

    def compute(self):
        import citysimtoenergyplus
        reload(citysimtoenergyplus)
        citysim = self.get_input('citysim')
        building = self.get_input('building')
        template = self.get_input('template')
        idf = extractidf(citysim=citysim, building=building, template=template)
        self.set_output('idf', idf)


def find_idd():
    '''
    find the default IDD file.
    '''
    import os
    try:
        energyplus = find_energyplus()
        folder = os.path.dirname(energyplus)
        idd = os.path.join(folder, 'Energy+.idd')
        if not os.path.isfile(idd):
            raise Exception('Could not find default Energy+.idd in %s' % folder)
        return idd
    except:
        raise Exception('Could not find default Energy+.idd')

def find_energyplus():
    '''
    find the default EnergyPlus executable
    '''
    import distutils.spawn
    energyplus = distutils.spawn.find_executable('EnergyPlus')
    if not energyplus:
        raise Exception('Could not find default EnergyPlus executable')
    return energyplus


def force_get_path(module, name, default):
    '''returns a string representing the path of a Path input module
    of `module` with the name `name`. If that is not set, then `default`
    is returned.
    '''
    value = module.force_get_input(name, None)
    if value:
        return value.name
    else:
        return default

_modules = [
    AcquireModelSnapshot,
    AddFmuToIdfLwr,
    AddOutputVariable,
    AddOutputVariableList,
    CitySimXml,
    EnergyPlusToFmu,
    FileToList,
    GenerateIdf,
    Idf,
    ModelSnapshot,
    RevitToCitySim,
    RunCitySim,
    RunEnergyPlus,
    RunCoSimulation,
    RunMockCoSimulation,
    StripInternalLoads,
    SaveEnergyPlusResults,
    SaveCitySimResults,
    SaveCoSimResults,
    XmlElementTree,
    XPath,
    XPathSetAttribute,
]
