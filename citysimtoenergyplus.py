'''
citysimtoenergyplus.py

Extract an EnergyPlus model (IDF) from a CitySim scene.
A template for the HVAC is provided, so this module is just
concerned with geometry, materials and construction.
'''
import numpy as np
from . import polygons
reload(polygons)


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
    constructions = add_constructions(citysim, building_xml, idf)
    add_zones(building_xml, idf)
    add_floors(building_xml, idf, constructions)
    add_walls(building_xml, idf, constructions)
    add_roofs(building_xml, idf, constructions)
    add_windows(building_xml, idf)
    add_shading(citysim, building_xml, idf)
    return idf


def add_zones(building_xml, idf):
    '''currently only single-zone models are allowed. the zone name from
    the idf is used. if any zones are defined in the template,
    an error is raised.'''
    zones = building_xml.findall('Zone')
    assert len(zones) == 1, 'Exactly one zone required'
    assert len(idf.idfobjects['ZONE']) == 0, \
        'No zone definitions in template allowed'
    zone = idf.newidfobject('ZONE')
    zone_xml = building_xml.find('Zone')
    zone.Name = 'Zone%s' % zone_xml.get('id')
    zone.Direction_of_Relative_North = 0
    zone.X_Origin = 0
    zone.Y_Origin = 0
    zone.Z_Origin = 0


def add_shading(citysim, building_xml, idf):
    shading_buildings = [s for s in citysim.findall('/*/Building')
                         if not s.get('id') == building_xml.get('id')]
    for building in shading_buildings:
        for surface_xml in building.findall('Zone/Wall'):
            vertices = [v for v in surface_xml.getchildren()
                        if v.tag.startswith('V')]
            npvertices = [np.array((float(v.get('x')),
                                    float(v.get('y')),
                                    float(v.get('z'))))
                          for v in vertices]
            if np.isnan(polygons.np_poly_area(npvertices)):
                print 'not exporting', surface_xml.get('id')
                continue  # don't export bad shading...

            shading = idf.newidfobject('SHADING:BUILDING:DETAILED')
            shading.Name = 'ShadingB%sW%s' % (building.get('id'),
                                              surface_xml.get('id'))
            shading.Number_of_Vertices = len(vertices)
            for v in vertices:
                shading.obj.append(v.get('x'))
                shading.obj.append(v.get('y'))
                shading.obj.append(v.get('z'))
	# JK - adds the Roofs as shading for all buildings including the co-simulated one
    shading_buildings = [s for s in citysim.findall('/*/Building')]
    for building in shading_buildings:
        for surface_xml in building.findall('Zone/Roof'):
            vertices = [v for v in surface_xml.getchildren()
                        if v.tag.startswith('V')]
            npvertices = [np.array((float(v.get('x')),
                                    float(v.get('y')),
                                    float(v.get('z'))))
                          for v in vertices]
            if np.isnan(polygons.np_poly_area(npvertices)):
                print 'not exporting', surface_xml.get('id')
                continue  # don't export bad shading...

            shading = idf.newidfobject('SHADING:BUILDING:DETAILED')
            shading.Name = 'ShadingB%sR%s' % (building.get('id'),
                                              surface_xml.get('id'))
            shading.Number_of_Vertices = len(vertices)
            for v in vertices:
                shading.obj.append(v.get('x'))
                shading.obj.append(v.get('y'))
                shading.obj.append(v.get('z'))


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
        vertices = [v for v in floor_xml.getchildren()
                    if v.tag.startswith('V')]
        floor_idf.Number_of_Vertices = len(vertices)
        for v in vertices:
            floor_idf.obj.append(v.get('x'))
            floor_idf.obj.append(v.get('y'))
            floor_idf.obj.append(v.get('z'))


def add_roofs(building_xml, idf, constructions):
    for roof_xml in building_xml.findall('Zone/Roof'):
        roof_idf = idf.newidfobject('ROOFCEILING:DETAILED')
        roof_idf.Name = 'Roof%s' % roof_xml.get('id')
        roof_idf.Construction_Name = constructions[roof_xml.get('type')]
        roof_idf.Zone_Name = 'Zone%s' % roof_xml.getparent().get('id')
        roof_idf.Outside_Boundary_Condition = 'Outdoors'
        roof_idf.Outside_Boundary_Condition_Object = ''
        roof_idf.Sun_Exposure = 'SunExposed'
        roof_idf.Wind_Exposure = 'WindExposed'
        roof_idf.View_Factor_to_Ground = 'autocalculate'
        vertices = [v for v in roof_xml.getchildren() if v.tag.startswith('V')]
        roof_idf.Number_of_Vertices = len(vertices)
        for v in vertices:
            roof_idf.obj.append(v.get('x'))
            roof_idf.obj.append(v.get('y'))
            roof_idf.obj.append(v.get('z'))


def add_walls(building_xml, idf, constructions):
    for wall_xml in building_xml.findall('Zone/Wall'):
        wall_idf = idf.newidfobject('WALL:DETAILED')
        wall_idf.Name = 'Wall%s' % wall_xml.get('id')
        wall_idf.Construction_Name = constructions[wall_xml.get('type')]
        wall_idf.Zone_Name = 'Zone%s' % wall_xml.getparent().get('id')
        wall_idf.Outside_Boundary_Condition = 'Outdoors'
        wall_idf.Outside_Boundary_Condition_Object = ''
        wall_idf.Sun_Exposure = 'SunExposed'
        wall_idf.Wind_Exposure = 'WindExposed'
        wall_idf.View_Factor_to_Ground = 'autocalculate'
        vertices = [v for v in wall_xml.getchildren() if v.tag.startswith('V')]
        wall_idf.Number_of_Vertices = len(vertices)
        for v in vertices:
            wall_idf.obj.append(v.get('x'))
            wall_idf.obj.append(v.get('y'))
            wall_idf.obj.append(v.get('z'))


def add_windows(building_xml, idf):
    for wall_xml in building_xml.findall('Zone/Wall'):
        uvalue = float(wall_xml.get('GlazingUValue', default=0))
        gvalue = float(wall_xml.get('GlazingGValue', default=0))
        ratio = float(wall_xml.get('GlazingRatio', default=0))
        wallid = 'Wall%s' % wall_xml.get('id')
        windowid = 'Window%s' % wall_xml.get('id')
        if ratio > 0:
            construction_name = 'WindowConstructionU%.2fG%.2f' % (
                uvalue, gvalue)
            material_name = 'WindowMaterialU%.2fG%.2f' % (uvalue, gvalue)
            construction = idf.getobject('CONSTRUCTION', construction_name)
            if not construction:
                construction = idf.newidfobject('CONSTRUCTION')
                construction.Name = construction_name
                construction.obj.append(material_name)
            material = idf.getobject('WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
                                     material_name)
            if not material:
                material = idf.newidfobject(
                    'WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM')
                material.Name = material_name
                material.UFactor = uvalue
                material.Solar_Heat_Gain_Coefficient = gvalue
            wall = idf.getobject('WALL:DETAILED', wallid)
            wall_vertices = [float(w)
                             for w in wall.obj[wall.Number_of_Vertices * -3:]]
            wall_polygon = [np.array(p) for p in zip(
                wall_vertices[::3],
                wall_vertices[1::3],
                wall_vertices[2::3])]
            if len(wall_polygon) > 4:
                raise Exception(
                    "Can't add windows to wall (too many vertices): %s"
                    % wall.Name)
            window_polygon = polygons.get_vertices_by_area_ratio(
                wall_polygon, ratio)
            assert window_polygon, 'Could not calculate window vertices'
            for i,vertex in enumerate(window_polygon):
				print 'i: ', i, '\tvertex: ', vertex
			
            window = idf.newidfobject('FENESTRATIONSURFACE:DETAILED', windowid + "_1")
            window.Surface_Type = 'Window'
            window.Construction_Name = construction.Name
            window.Building_Surface_Name = wallid
            window.Number_of_Vertices = 3
			
            for i,vertex in enumerate(window_polygon):
				if i < 3:
					window.obj.extend(vertex)

            window = idf.newidfobject('FENESTRATIONSURFACE:DETAILED', windowid + "_2")
            window.Surface_Type = 'Window'
            window.Construction_Name = construction.Name
            window.Building_Surface_Name = wallid
            window.Number_of_Vertices = 3		
            for i,vertex in enumerate(window_polygon):			
				if i == 0:
					window.obj.extend(vertex)
				if i > 1:
					window.obj.extend(vertex)					
				
            print 'add_windows', len(window_polygon), len(wall_polygon)


def add_constructions(citysim, building_xml, idf):
    '''
    go through each wall, floor and roof in the building and create
    a CONSTRUCTION object for each WallType referenced.
    '''
    surfaces = [e for e in building_xml.findall('Zone/*')
                if e.tag in ('Wall', 'Roof', 'Floor')]
    constructions = {}
    for surface in surfaces:
        id = surface.get('type')
        if id not in constructions:
            construction_xml = citysim.find('//WallType[@id="%s"]' % id)
            if construction_xml is None:
                raise Exception('could not find //WallType[@id="%s"]' % id)
            construction_idf = idf.newidfobject(
                'CONSTRUCTION',
                construction_xml.get(
                    'name',
                    default='WallType%s' %
                    id))
            for mnr, layer in enumerate(construction_xml.findall('Layer')):
                material_idf = idf.newidfobject(
                    'MATERIAL', '%s_M%i' %
                    (construction_idf.Name, mnr))
                material_idf.Thickness = float(layer.get('Thickness'))
                material_idf.Roughness = 'MediumSmooth'
                material_idf.Conductivity = float(layer.get('Conductivity'))
                material_idf.Density = float(layer.get('Density'))
                material_idf.Specific_Heat = float(layer.get('Cp'))
                construction_idf.obj.append(material_idf.Name)
                constructions[id] = construction_idf.Name
    return constructions


def find_building(building, citysim):
    building_xml = find_building_by_name(building, citysim)
    if building_xml is not None:
        return building_xml
    else:
        return find_building_by_id(building, citysim)


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
