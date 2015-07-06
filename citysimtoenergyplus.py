'''
citysimtoenergyplus.py

Extract an EnergyPlus model (IDF) from a CitySim scene.
A template for the HVAC is provided, so this module is just
concerned with geometry, materials and construction.
'''


def extractidf(citysim, building, template):
    '''
    this is the main entry point to the module.
    citysim: a lxml.etree.ElementTree containing the CitySim scene.
    building: a string containing the building/@Name|id to extract.
        first, the @Name is checked and if not found, fall back to @id.
    template: a eppy.IDF object representing the template to add the geometry
        to. the template may contain HVAC etc. extractidf only knows a
        single zone called "SINGLE_ZONE".
    '''
    building_xml = find_building(building, citysim)
    idf = idf_from_template(template)
    add_materials(idf)
    add_constructions(idf)
    add_window_materials(idf)
    add_window_constructions(idf)
    add_floors(building_xml, idf)
    add_walls(building_xml, idf)
    add_roofs(building_xml, idf)
    add_windows(building_xml, idf)
    add_shading(citysim, building, idf)
    return idf


def find_building(building, citysim):
    return (find_building_by_name(building, citysim) or
           find_building_by_id(building, citysim))


def find_building_by_name(building, citysim):
    return citysim.find('/*/Building[@Name="%s"]' % building)


def find_building_by_id(building, citysim):
    return citysim.find('/*/Building[@id="%s"]' % building)


def idf_from_template(template):
    '''
    cloning a whole IDF file is not as easy as I thought it
    would be. But we can copy each object...
    '''
    from eppy import modeleditor
    idf = modeleditor.IDF()
    idf.initnew()
    for key in template.idfobjects.keys():
        for value in template.idfobjects[key]:
            idf.copyidfobject(value)
    return idf
