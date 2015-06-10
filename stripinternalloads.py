"""
Strip the internal loads and ventilation/infiltration from an
IDF file as produced by the DPV.

FIXME: In future, make a module that can "edit" IDF files based on a simple
syntax...
"""
import parseidf


def process_idf(idf_as_string):
    '''parse an idf file (encoded in a string) and
    return a new idf file with following objects removed:

        - Lights
        - LightSchedule
        - ElectricEquipment
        - EquipSchedule
        - ZoneInfiltration:DesignFlowRate
        - InfiltrationSchedule
        - ZoneVentilation:DesignFlowRate
        - VentilationSchedule
    '''
    idf = parseidf.parse(idf_as_string)
    print 'Output:Variables:', idf['OUTPUT:VARIABLE']
    #delete(idf, 'Lights')
    #delete(idf, 'Schedule:Compact', 'LightSchedule')
    #delete(idf, 'ElectricEquipment')
    #delete(idf, 'Schedule:Compact', 'EquipSchedule')
    #delete(idf, 'ZoneInfiltration:DesignFlowRate')
    #delete(idf, 'Schedule:Compact', 'InfiltrationSchedule')
    #delete(idf, 'ZoneVentilation:DesignFlowRate')
    #delete(idf, 'Schedule:Compact', 'VentilationSchedule')
    #delete(idf, 'People')
    #delete(idf, 'Schedule:Compact', 'OccupationSchedule')
    #delete(idf, 'Schedule:Compact', 'ActivityLevelSchedule')
    #occupation_schedule = find(idf, 'Schedule:Compact', 'OccupationSchedule')
    #occupation_schedule[3:] = [
    #    'Through: 12/31', 'For: AllDays', 'Until: 24:00', '1.0']
    ventilation_schedule = find(idf, 'Schedule:Compact', 'VentilationSchedule')
    ventilation_schedule[3:] = [
       'Through: 05/31', 'For: AllDays', 'Until: 24:00', '1.0',
       'Through: 09/01', 'For: AllDays', 'Until: 24:00', '0.0',
       'Through: 12/31', 'For: AllDays', 'Until: 24:00', '1.0']
    lights = find(idf, 'Lights', 'Lights_DEFAULT_ZONE')
    lights[6] = str(10.0)  # Watts per Zone Floor Area
    lights[8] = str(0.0)  # Return Air Fraction

    electric = find(idf, 'ElectricEquipment', 'ElectricEquipment_DEFAULT_ZONE')
    electric[6] = str(10.0)  # Watts per Zone Floor Area
    electric[9] = str(0.0)  # Fraction Radiant

    #ventilation = find(idf, 'ZoneVentilation:DesignFlowRate')
    #ventilation[8] = str(3.0)
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
        'Zone Mean Air Temperature',
        'timestep')
    return writeidf(idf)


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


def upper(s):
    """handle unicode and str in maps"""
    return s.upper()


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
        print 'usage: python stripinternalloads.py IDF_FILE'
        sys.exit(1)
    infile = sys.argv[1]
    with open(infile, 'r') as f:
        print process_idf(f.read())
