'''
addfmutoidf.py is a command line utility to augment an idf file
with the idf objects necessary to use this file as an fmu in
conjunction with CitySim as defined in the interface document from the
UMEM project.

The script expects the idf file to be mentioned as the first argument and
then parses that using the parseidf module.

The output is printed to stdout.
'''
import parseidf
import polygons
import itertools


# some helper functions for creating ids and idfs
def next_id():
    """create unique ids"""
    if not hasattr(next_id, '__id'):
        next_id.__id = 0
    id = next_id.__id
    next_id.__id += 1
    return id


def id_map(key):
    """map a key to an id, so that each new key gets a new id
    (next_id()), and each invocation with the same key gets
    the same id."""
    if not hasattr(id_map, '__map'):
        id_map.__map = {}
    if key not in id_map.__map:
        id_map.__map[key] = next_id()
    return id_map.__map[key]


def find(idf, *obj):
    """
    locate the first object matching *obj and return it (an array).
    """
    key = obj[0].upper()
    if key in idf:
        for o in idf[key]:
            if map(upper, obj) == map(upper, o[:len(obj)]):
                return o
    return None


def delete(idf, *obj):
    """
    delete all objects matching *obj
    """
    key = obj[0].upper()
    if key in idf:
        objects = idf[key]
        new_objects = []
        for i in range(len(objects)):
            if map(upper, obj) != map(upper, objects[i][:len(obj)]):
                new_objects.append(objects[i])
        idf[key] = new_objects


def contains(idf, *obj):
    """find an idf object that matches the elements in obj,
    obj may be shorter than the element being searched for.
    return True if such an object was found, otherwise False"""
    key = obj[0].upper()
    if key in idf:
        for o in idf[key]:
            if map(upper, obj) == map(upper, o[:len(obj)]):
                # already contained in idf
                return True
    return False


def upper(s):
    """handle unicode and str in maps"""
    return s.upper()


def ensure_contains(idf, *obj):
    '''make sure obj is in the idf, if not - add it.
    '''
    if contains(idf, *obj):
        return idf
    else:
        # add to idf
        key = obj[0].upper()
        values = idf.get(key, [])
        values.append(obj)
        idf[key] = values
        return idf


def add_fmu_to_idf(idf):
    '''set up the file for FMU export'''
    return ensure_contains(idf,
                           'ExternalInterface',
                           'FunctionalMockupUnitExport')


def produce_edd(idf):
    '''make sure the .edd file is written'''
    return ensure_contains(idf,
                           'Output:EnergyManagementSystem',
                           'Verbose',
                           'Verbose',
                           'ErrorsOnly')


def exterior_walls(idf):
    '''return a list of idf objects representing the
    exterior walls, these are WALL:DETAILED objects
    that have an outside boundary condition of "outdoors"
    '''
    def is_exterior_wall(w):
        return w[4].strip().lower() == 'outdoors'
    return [w for w in idf['WALL:DETAILED'] if is_exterior_wall(w)]


def windows(idf):
    '''return a list of window idf objects, these are the
    FENESTRATIONSURFACE:DETAILED objects.'''
    try:
        return idf['FENESTRATIONSURFACE:DETAILED']
    except KeyError:
        return []


def roofs(idf):
    '''return a list of window objects, these are the
    ROOFCEILING:DETAILED objects that have an outside boundary
    condition of "outdoors"
    '''
    def is_exterior_roof(r):
        return r[4].strip().lower() == 'outdoors'
    return [r for r in idf['ROOFCEILING:DETAILED'] if is_exterior_roof(r)]


def windows_on_wall(idf, wall):
    '''return a list of windows that are hosted on a specific
    wall.'''
    BUILDING_SURFACE_NAME_IDX = 4
    return [window for window in windows(idf)
            if window[BUILDING_SURFACE_NAME_IDX].strip().upper()
            == id(wall).strip().upper()]


def zones(idf):
    '''return a list of zone idf objects, these are the
    ZONE objects.'''
    return idf['ZONE']


def id(obj):
    return obj[1]


def sane(id):
    """EnergyPlus variable names my not contain periods."""
    return id.replace('.', '_')


def area(obj):
    '''returns the area of a wall:detailed or a
    fenestrationsurface:detailed idf object'''
    if obj[0].upper() == 'WALL:DETAILED':
        start_index = 10
    elif obj[0].upper() == 'FENESTRATIONSURFACE:DETAILED':
        start_index = 11
    points = []
    i = start_index
    while i + 2 < len(obj):
        x, y, z = map(float, obj[i:i + 3])
        points.append((x, y, z))
        i += 3
    return polygons.area(points)


def add_outside_surface_temperature(idf):
    '''
    add the necessary objects to output the surface temperatures
    as an fmu. Also, output them as normal variables.
    '''
    idf = ensure_contains(idf,
                          'Output:Variable', '*',
                          'Surface Outside Face Temperature',
                          'timestep')
    idf = ensure_contains(idf,
                          'Output:Variable', '*',
                          'Surface Inside Face Temperature',
                          'timestep')
    for wall in exterior_walls(idf):
        idf = ensure_contains(
            idf,
            'ExternalInterface:FunctionalMockupUnitExport:From:Variable',
            '%s' % id(wall),
            'Surface Outside Face Temperature',
            '%s::Outside Surface Temperature' % id(wall))
    for roof in roofs(idf):
        idf = ensure_contains(
            idf,
            'ExternalInterface:FunctionalMockupUnitExport:From:Variable',
            '%s' % id(roof),
            'Surface Outside Face Temperature',
            '%s::Outside Surface Temperature' % id(roof))
    return idf


def add_average_outside_surface_temperature(idf):
    """
    adds the necessary objects to output the average surface
    temperatures of walls (including windows).
    this includes:
        - ems sensors for walls and windows
        - a global variable (awtX) per wall
        - output variables (for debugging?)
        - FMU output variables for the global variables
        - a program calling manager
        - a program
        - a routine for each wall to update the value
    """
    # ems sensors for walls
    for wall in exterior_walls(idf):
        idf = ensure_contains(
            idf,
            'EnergyManagementSystem:Sensor',
            'w%i' % id_map(id(wall)),
            id(wall),
            'Surface Outside Face Temperature')
    # ems sensors for windows
    for window in windows(idf):
        idf = ensure_contains(
            idf,
            'EnergyManagementSystem:Sensor',
            'f%i' % id_map(id(window)),
            id(window),
            'Surface Outside Face Temperature')
    # a global variable (awtX) per wall
    for wall in exterior_walls(idf):
        idf = ensure_contains(
            idf,
            'EnergyManagementSystem:GlobalVariable',
            'awt%i' % id_map(id(wall)))
        idf = ensure_contains(
            idf,
            'EnergyManagementSystem:OutputVariable',
            'Average Wall Outside Temperature ' + id(wall),
            'awt%i' % id_map(id(wall)),
            'Averaged',
            'ZoneTimestep',
            '',
            'C')
        idf = ensure_contains(
            idf,
            'Output:Variable',
            '*',
            'Average Wall outside Temperature ' + id(wall),
            'timestep')
    # fmu output variables for the global variables
    for wall in exterior_walls(idf):
        idf = ensure_contains(
            idf,
            'ExternalInterface:FunctionalMockupUnitExport:From:Variable',
            'EMS',
            'Average Wall Outside Temperature ' + id(wall),
            '%s::Average Outside Surface Temperature' % id(wall))
    # program calling manager, program, update routines for the awtX variables
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:ProgramCallingManager',
        'update_awt_every_timestep',
        'BeginTimestepBeforePredictor',
        'update_awt_variables')
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:Program',
        'update_awt_variables',
        *['RUN update_awt_w%i' % id_map(id(wall))
          for wall in exterior_walls(idf)])
    for wall in exterior_walls(idf):
        wid = id_map(id(wall))
        warea = area(wall)
        tarea = warea + sum(area(window)
                            for window in windows_on_wall(idf, wall))
        idf = ensure_contains(
            idf,
            'EnergyManagementSystem:Subroutine',
            'update_awt_w%(wid)i' % locals(),
            'SET awt%(wid)i = %(warea).6f * w%(wid)i / %(tarea).6f' % locals(),
            *['SET awt%i = awt%i + (%.6f * f%i / %.6f)'
              % (wid, wid, area(window),
                 id_map(id(window)), tarea)
              for window in windows_on_wall(idf, wall)])
    return idf


def add_zone_ideal_loads_energy(idf):
    """add fmu output of
       -   Zone Ideal Loads Zone Total Heating Energy
       -   Zone Ideal Loads Zone Total Cooling Energy
    """
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:GlobalVariable',
        'gv_the')
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:OutputVariable',
        'GV Total Heating Energy',
        'gv_the',
        'Averaged',
        'ZoneTimestep',
        '',
        'C')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'GV Total Heating Energy',
        'timestep')
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:From:Variable',
        'EMS',
        'GV Total Heating Energy',
        'SINGLE_ZONE::Total Heating Energy')

    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:GlobalVariable',
        'gv_tce')
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:OutputVariable',
        'GV Total Cooling Energy',
        'gv_tce',
        'Averaged',
        'ZoneTimestep',
        '',
        'C')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'GV Total Cooling Energy',
        'timestep')
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:From:Variable',
        'EMS',
        'GV Total Cooling Energy',
        'SINGLE_ZONE::Total Cooling Energy')

    for zone in zones(idf):
        zid = id(zone)
        if is_lowex(idf):
            idf = lowex_total_heating_energy(idf, zid)
        else:
            idf = hvac_template_total_heating_energy(idf, zid)
            idf = ensure_contains(
                idf,
                'Output:Variable',
                '*',
                'Zone Ideal Loads Zone Total Heating Energy',
                'timestep')
            idf = ensure_contains(
                idf,
                'Output:Variable',
                '*',
                'Zone Ideal Loads Zone Total Cooling Energy',
                'timestep')

    # program calling manager, program, update routines for the zhe, zce vars
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:ProgramCallingManager',
        'update_zhe_every_timestep',
        'BeginTimestepBeforePredictor',
        'update_zhe_variables',
        'update_zce_variables')
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:Program',
        'update_zhe_variables',
        'SET gv_the = 0',
        *['SET gv_the = gv_the + zhe%i' % id_map(id(zone))
          for zone in zones(idf)])
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:Program',
        'update_zce_variables',
        'SET gv_tce = 0',
        *['SET gv_tce = gv_tce + zce%i' % id_map(id(zone))
          for zone in zones(idf)])
    return idf


def is_lowex(idf):
    """True, if the model uses the HVAC template for Ideal Loads"""
    return contains(idf, 'EnergyManagementSystem:OutputVariable',
                    '%s Total Heating Energy {J}' % id(zones(idf)[0]))


def hvac_template_total_heating_energy(idf, zid):
    """Use the variables from the HVAC Template to create the fmu
    export variable for Total Heating/Cooling Energy.
    zhe stands for Zone Heating Energy
    zce stands for Zone Cooling Energy"""
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:Sensor',
        'zhe%i' % id_map(zid),
        zid + 'ZONEHVAC:IDEALLOADSAIRSYSTEM',
        'Zone Ideal Loads Zone Total Heating Energy')
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:Sensor',
        'zce%i' % id_map(zid),
        zid + 'ZONEHVAC:IDEALLOADSAIRSYSTEM',
        'Zone Ideal Loads Zone Total Cooling Energy')
    return idf


def lowex_total_heating_energy(idf, zid):
    """Use the ems variables from the LowEx Template to create the fmu
    export variable for Total Heating/Cooling Energy"""
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:From:Variable',
        'EMS',
        '%s Total Heating Energy' % zid,
        '%s::Total Heating Energy' % zid)
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:From:Variable',
        'EMS',
        '%s Total Cooling Energy' % zid,
        '%s::Total Cooling Energy' % zid)
    return idf


def add_zone_mean_air_temperature(idf):
    """add fmu output of
       - Mean Air Temperature
    for each zone.
    """
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Zone Mean Air Temperature',
        'timestep')
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:GlobalVariable',
        'gv_mat')
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:OutputVariable',
        'GV Mean Air Temperature',
        'gv_mat',
        'Averaged',
        'ZoneTimestep',
        '',
        'C')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'GV Mean Air Temperature',
        'timestep')
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:From:Variable',
        'EMS',
        'GV Mean Air Temperature',
        'SINGLE_ZONE::Mean Air Temperature')

    for zone in zones(idf):
        zid = id(zone)
        idf = ensure_contains(
            idf,
            'EnergyManagementSystem:Sensor',
            'zmat%i' % id_map(zid),
            zid,
            'Zone Mean Air Temperature')

    # program calling manager, program, update routines for the zmat vars
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:ProgramCallingManager',
        'update_zmat_every_timestep',
        'BeginTimestepBeforePredictor',
        'update_zmat_variables')
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:Program',
        'update_zmat_variables',
        'SET gv_mat = 0',
        *['SET gv_mat = gv_mat + zmat%i' % id_map(id(zone))
          for zone in zones(idf)])
    return idf


def add_ventilation_volume_flow_rate(idf):
    """add fmu output of 'Zone Ventilation Standard Density Volume Flow Rate'
    for each zone."""
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Zone Ventilation Standard Density Volume Flow Rate',
        'timestep')
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:GlobalVariable',
        'gv_vvfr')
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:OutputVariable',
        'GV Ventilation Volume Flow Rate',
        'gv_vvfr',
        'Averaged',
        'ZoneTimestep',
        '',
        'C')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'GV Ventilation Volume Flow Rate',
        'timestep')
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:From:Variable',
        'EMS',
        'GV Ventilation Volume Flow Rate',
        'SINGLE_ZONE::Ventilation Volume Flow Rate')

    for zone in zones(idf):
        zid = id(zone)
        idf = ensure_contains(
            idf,
            'EnergyManagementSystem:Sensor',
            'zvvfr%i' % id_map(zid),
            zid,
            'Zone Ventilation Standard Density Volume Flow Rate')

    # program calling manager, program, update routines for the zmat vars
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:ProgramCallingManager',
        'update_vvfr_every_timestep',
        'BeginTimestepBeforePredictor',
        'update_vvfr_variables')
    idf = ensure_contains(
        idf,
        'EnergyManagementSystem:Program',
        'update_vvfr_variables',
        'SET gv_vvfr = 0',
        *['SET gv_vvfr = gv_vvfr + zvvfr%i' % id_map(id(zone))
          for zone in zones(idf)])
    return idf


def add_occupation_actuator(idf):
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:To:Actuator',
        'Occupation::Actuator',  # EnergyPlus Variable Name
        'OCCUPATIONSCHEDULE',  # Actuated Component Unique Name
        'Schedule:Compact',  # Actuated Component Type
        'Schedule Value',  # Actuated Component Control Type
        'SINGLE_ZONE::Occupation',  # FMU Variable Name
        '0')  # Initial Value
    return idf


def add_weather_actuators(idf):
    """add the actuators for the weather interface to CitySim"""
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:To:Actuator',
        'CitySimOutdoorDryBulb',  # EnergyPlus Variable Name
        'Environment',  # Actuated Component Unique Name
        'Weather Data',  # Actuated Component Type
        'Outdoor Dry Bulb',  # Actuated Component Control Type
        'Outdoor Drybulb',  # FMU Variable Name
        '0')  # Initial Value
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:To:Actuator',
        'CitySimOutdoorDewPoint',  # EnergyPlus Variable Name
        'Environment',  # Actuated Component Unique Name
        'Weather Data',  # Actuated Component Type
        'Outdoor Dew Point',  # Actuated Component Control Type
        'Outdoor Dewpoint',  # FMU Variable Name
        '0')  # Initial Value
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:To:Actuator',
        'CitySimOutdoorRelativeHumidity',  # EnergyPlus Variable Name
        'Environment',  # Actuated Component Unique Name
        'Weather Data',  # Actuated Component Type
        'Outdoor Relative Humidity',  # Actuated Component Control Type
        'Outdoor Relative Humidity',  # FMU Variable Name
        '0')  # Initial Value
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:To:Actuator',
        'CitySimDiffuseSolar',  # EnergyPlus Variable Name
        'Environment',  # Actuated Component Unique Name
        'Weather Data',  # Actuated Component Type
        'Diffuse Solar',  # Actuated Component Control Type
        'Diffuse Solar',  # FMU Variable Name
        '0')  # Initial Value
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:To:Actuator',
        'CitySimDirectSolar',  # EnergyPlus Variable Name
        'Environment',  # Actuated Component Unique Name
        'Weather Data',  # Actuated Component Type
        'Direct Solar',  # Actuated Component Control Type
        'Direct Solar',  # FMU Variable Name
        '0')  # Initial Value
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:To:Actuator',
        'CitySimWindSpeed',  # EnergyPlus Variable Name
        'Environment',  # Actuated Component Unique Name
        'Weather Data',  # Actuated Component Type
        'Wind Speed',  # Actuated Component Control Type
        'Wind Speed',  # FMU Variable Name
        '0')  # Initial Value
    idf = ensure_contains(
        idf,
        'ExternalInterface:FunctionalMockupUnitExport:To:Actuator',
        'CitySimWindDirection',  # EnergyPlus Variable Name
        'Environment',  # Actuated Component Unique Name
        'Weather Data',  # Actuated Component Type
        'Wind Direction',  # Actuated Component Control Type
        'Wind Direction',  # FMU Variable Name
        '0')  # Initial Value
    return idf


def add_output_variable(idf_as_string, key, variable, frequency):
    '''
    add an output variable to an idf by parsing it, adding the
    object and writing it out to a string again...
    '''
    idf = parseidf.parse(idf_as_string)
    idf = ensure_contains(
        idf,
        'Output:Variable',
        key,
        variable,
        frequency)
    return writeidf(idf)


def add_output_variables(idf):
    '''
    Add some default output variables that we want to see in all simulations.
    FIXME: this is a quick hack because I have no time to debug why the
    Settings.xml in the %APPDATA% folder is not being honoured...
    '''
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'People Total Heating Energy',
        'RunPeriod')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Lights Total Heating Energy',
        'RunPeriod')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Electric Equipment Total Heating Energy',
        'RunPeriod')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Facility Total Produced Electric Energy',
        'RunPeriod')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Zone Infiltration Total Heat Loss Energy',
        'RunPeriod')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Zone Ventilation Total Heat Loss Energy',
        'RunPeriod')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Surface Inside Face Conduction Heat Loss Rate',
        'RunPeriod')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Surface Inside Face Conduction Heat Gain Rate',
        'RunPeriod')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Surface Inside Face Temperature',
        'hourly')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Zone Windows Total Heat Gain Energy',
        'RunPeriod')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Zone Windows Total Heat Loss Energy',
        'RunPeriod')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Surface Outside Face Outdoor Air Wind Speed',
        'timestep')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Site Direct Solar Radiation Rate per Area',
        'RunPeriod')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Zone Ideal Loads Zone Total Heating Energy',
        'timestep')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Zone Ideal Loads Zone Total Cooling Energy',
        'timestep')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Site Outdoor Air Drybulb Temperature',
        'timestep')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Site Outdoor Air Dewpoint Temperature',
        'timestep')
    idf = ensure_contains(
        idf,
        'Output:Variable',
        '*',
        'Site Diffuse Solar Radiation Rate per Area',
        'timestep')
    return idf


def add_lwr_fmi(idf):
    """
    add fmi variables per surface to accept TEnv and HEnv.
    add a program to pass those variables on to the LWR actuators.
    """
    for surface in itertools.chain(exterior_walls(idf), roofs(idf)):
        sid = id(surface)
        vid = id_map(sid)
        idf = ensure_contains(
            idf,
            'ExternalInterface:FunctionalMockupUnitExport:To:Actuator',
            'henv%i' % vid,  # EnergyPlus Variable Name
            sid,  # Actuated Component Unique Name
            'Surface',  # Actuated Component Type
            'Exterior Surface Environment Radiation Coefficient',  # noqa Actuated Component Control Type
            '%s::Henv' % sid,  # FMU Variable Name
            '0.0')  # Initial Value
        idf = ensure_contains(
            idf,
            'ExternalInterface:FunctionalMockupUnitExport:To:Actuator',
            'tenv%i' % vid,  # EnergyPlus Variable Name
            sid,  # Actuated Component Unique Name
            'Surface',  # Actuated Component Type
            'Exterior Surface Environment Temperature For Radiation Exchange',  # noqa Actuated Component Control Type
            '%s::Tenv' % sid,  # FMU Variable Name
            '0.0')  # Initial Value
    return idf


def process_idf(idf_as_string):
    '''parse an idf file (encoded in a string) and
    return a string with the idf file augmented with
    the information necessary to produce an FMU.
    '''
    idf = parseidf.parse(idf_as_string)
    idf = add_fmu_to_idf(idf)
    idf = produce_edd(idf)
    idf = add_outside_surface_temperature(idf)
    idf = add_average_outside_surface_temperature(idf)
    idf = add_zone_ideal_loads_energy(idf)
    idf = add_zone_mean_air_temperature(idf)
    idf = add_ventilation_volume_flow_rate(idf)
    idf = add_weather_actuators(idf)
    idf = add_occupation_actuator(idf)
    idf = add_output_variables(idf)
    return idf


def process_idf_lwr(idf_as_string):
    """
    parse an idf file (encoded in a string) and return a string
    with the idf file augmented with the information necessary to produce
    an FMU.
    """
    idf = process_idf(idf_as_string)
    idf = add_lwr_fmi(idf)
    return idf


def writeidf(data):
    """ formats the output format of parseidf.parse() to the IDF format.
    Example input: { 'A': [['A', '0'], ['A', '1']] }
    Example output:

    A, 0;
    A, 1;
    """
    lines = []
    for objecttype in sorted(data.values()):
        for idfobject in objecttype:
            line = ',\n\t'.join(idfobject) + ';'
            lines.append(line)
    return '\n'.join(lines)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print 'usage: python addfmutoidf.py IDF_FILE'
        sys.exit(1)
    infile = sys.argv[1]
    with open(infile, 'r') as f:
        print writeidf(process_idf(f.read()))
