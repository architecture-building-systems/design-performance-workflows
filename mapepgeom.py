'''
mapepgeom.py

Go through each wall, roof, floor and shading surface in the
energyplus geometry and map the vertices of the idf file
back to the citysim file.

Expects naming conventions to be those of CitySimToEnergyPlus:
    - Wall<CitySimID>
    - Roof<CitySimID>
    - Floor<CitySimID>
    - ShadingB<CitySimBuildingID>W<CitySimID>

as a side effect, the ep_id tag is entered to all surfaces matched,
this is a prerequisite for co-simulation.

NOTES:
    - assumes each surface has a unique id in the CitySim model!
'''
import itertools
from lxml import etree


def map_ep_geom(citysim, idf):
    for surface_xml in get_surfaces(citysim):
        print '%s[@id="%s"]' % (surface_xml.tag, surface_xml.get('id'))
        obj = find_surface(surface_xml, idf)
        if obj:
            update_vertices(surface_xml, obj)
            surface_xml.set('ep_id', obj.Name)
    return citysim


def get_surfaces(citysim):
    '''
    return a list of Wall, Roof and Floor elements in the
    CitySimXml file.
    '''
    return list(itertools.chain(
        citysim.findall('//Wall'),
        citysim.findall('//Roof'),
        citysim.findall('//Floor')))


def find_surface(surface, idf):
    '''
    find a surface with the same id the idf.
    due to the naming convention, look through Roofs, Walls,
    Floors - the same as the surface tag! and also the  ShadingSurfaces...
    '''
    ep_id = surface.tag + surface.get('id')
    obj = (idf.getobject('BUILDINGSURFACE:DETAILED', ep_id)
           or idf.getobject('WALL:DETAILED', ep_id)
           or idf.getobject('ROOFCEILING:DETAILED', ep_id)
           or idf.getobject('FLOOR:DETAILED', ep_id))
    if obj:
        return obj
    else:
        # could be a shading surface
        shading_id = 'ShadingB%sW%s' % (
            surface.getparent().getparent().get('id'),
            surface.get('id'))
        return idf.getobject('SHADING:BUILDING:DETAILED', shading_id)


def update_vertices(surface_xml, obj):
    '''
    remove the CitySim vertices and replace them with those
    from the IDF object!
    '''
    obj_vertex_data = obj.obj[obj.objls.index('Number_of_Vertices')+1:]
    obj_vertices = zip(obj_vertex_data[0::3],
                       obj_vertex_data[1::3],
                       obj_vertex_data[2::3])
    # delete old vertices
    for v in surface_xml.getchildren():
        if v.tag.startswith('V'):
            surface_xml.remove(v)
    # add new vertices
    for i, v in enumerate(obj_vertices):
        vertex_xml = etree.Element('V%i' % i)
        vertex_xml.set('x', str(v[0]))
        vertex_xml.set('y', str(v[1]))
        vertex_xml.set('z', str(v[2]))
        surface_xml.append(vertex_xml)
