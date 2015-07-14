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
    constructions = add_constructions(building_xml, idf)
    add_zones(building_xml, idf)
    add_window_materials(idf)
    add_window_constructions(idf)
    add_floors(building_xml, idf, constructions)
    add_walls(building_xml, idf, constructions)
    add_roofs(building_xml, idf, constructions)
    add_windows(building_xml, idf)
    add_shading(citysim, building, idf)
    return idf


def add_floors(building_xml, idf, constructions):
    for floor_xml in building_xml.findall('Zone/Floor'):
        floor_idf = idf.newidfobject('FLOOR:DETAILED')
        floor_idf.Name = 'Floor%s' % floor_xml.get('id')
        floor_idf.Construction_Name = constructions[floor_xml.get('type')]
        floor_idf.Zone_Name = 'Zone%s' % floor_xml.getparent().get('id')
        floor_idf.Outside_Boundary_Condition = 'Ground'
        floor_idf.Outside_Boundary_Condition_Object = ''
        floor_idf.Sun_Exposure = 'NoSun'
        floor_idf.Wind_Exposure = 'NoWind'
        floor_idf.View_Factor_to_Ground = 'autocalculate'
        vertices = [v for v in floor_xml.getchildren() if v.tag.startswith('V')]
        floor_idf.Number_of_Vertices = len(vertices)
        for v in vertices:
            floor_idf.obj.append(v.get('x'))
            floor_idf.obj.append(v.get('y'))
            floor_idf.obj.append(v.get('z'))



def add_constructions(citysim, building_xml, idf):
    '''
    go through each wall, floor and roof in the building and create
    a CONSTRUCTION object for each WallType referenced.
    '''
    surfaces = [e for e in building_xml.findall('Zone/*') if e.tag in ('Wall', 'Roof', 'Floor')]
    constructions = {}
    for surface in surfaces:
        id = surface.get('type')
        if not id in constructions:
            construction_xml = citysim.find('//WallType[@id="%s"]' % id)
            construction_idf = idf.newidfobject('CONSTRUCTION', construction_xml.get('name', default='WallType%s' % id))
            for mnr, layer in enumerate(construction_xml.findall('Layer')):
                material_idf = idf.newidfobject('MATERIAL', '%s_M%i' % (construction_idf.Name, mnr))
                material_idf.Thickness = float(layer.get('Thickness'))
                material_idf.Roughness = 'MediumSmooth'
                material_idf.Conductivity = float(layer.get('Conductivity'))
                material_idf.Density = float(layer.get('Density'))
                material_idf.Specific_Heat = float(layer.get('Cp'))
                construction_idf.obj.append(material_idf.Name)
                constructions[id] = construction_idf.Name
    return constructions


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
