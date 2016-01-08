'''
simplifycitysimgeometry.py

Using a similar algorithm to shading.py, simplify rectangles in
the CitySim xml file by combining walls that belong to the same
building and zone and have the same construction information.

Take special care with opacity...
'''
from eppy.geometry.surface import tilt, angle2vecs, area
from lxml import etree
import numpy as np
import itertools


def simplify(citysim_xml):
    to_delete = simplify_one_level(collect_walls(citysim_xml))
    while len(to_delete):
        for wall in to_delete:
            wall.getparent().remove(wall)
        to_delete = simplify_one_level(collect_walls(citysim_xml))
    return citysim_xml


def simplify_one_level(walls):
    '''
    run one pass of simplifications - this needs to be repeated until
    no more simplifications are found
    to_delete is a set of names of shading surfaces that were simplified.
    '''
    to_delete = set()
    print 'simplify_one_level', len(walls)
    for wa, wb in itertools.combinations(walls, 2):
        if not same_zone(wa, wb):
            continue
        if not same_construction(wa, wb):
            continue
        if wa in to_delete or wb in to_delete:
            # one of these has already been merged!
            continue
        pa = get_polygon(wa)
        pb = get_polygon(wb)
        if len(points_in_common(pa, pb)) != 2:
            # ignore these as they can't possibly share an edge
            continue
        pa = canonical_rotation(pa)
        pb = canonical_rotation(pb)
        if np.isclose(pa[0][2], pb[0][2]):
            # not above each other...
            continue
        # swap the two polygons so that pa is the upper and pb the lower
        # polygon - that way we can always index them the same:
        # a1 ----- a2
        # |        |
        # |        |
        # a0 ----- a3 (a0 == b1, a3 == b2)
        # |        |
        # |        |
        # b0 ----- b3
        if pa[0][2] < pb[0][2]:
            wa, wb = wb, wa
            pa, pb = pb, pa
        pnew = [pb[0], pa[1], pa[2], pb[3]]
        set_polygon(wa, pnew)
        wa.set('Area', str(area(pnew)))
        merge_windows(wa, wb)
        to_delete.add(wb)
        print '-', wa.get('id'), wb.get('id')
    return to_delete


def canonical_rotation(polygon):
    '''
    for our algorithm, a canonically rotated polygon
    has polygon = [a, b, c, d] with:
        a.z < b.z
        a.z == d.z
        b.z == c.z
        c.z > d.z
    that is, the first vertex is a lower corner and
    the next vertex an upper corner.
    '''
    assert len(polygon) == 4, 'only for rectangles!'

    def only_two_z_values(polygon):
        zs = set(v[2] for v in polygon)
        for z0, z1 in itertools.combinations(zs, 2):
            if np.isclose(z0, z1) and z0 in zs:
                zs.remove(z0)
        return len(zs) == 2
    assert only_two_z_values(polygon), 'only two z-values allowed! %s' % set(v[2] for v in polygon) # noqa

    def is_canonical(polygon):
        a, b, c, d = polygon
        return all((a[2] < b[2],
                    np.isclose(a[2], d[2]),
                    np.isclose(b[2], c[2]),
                    c[2] > d[2]))
    for i in range(4):  # make sure we don't loop forever on bad data!
        if is_canonical(polygon):
            return polygon
        polygon = rotate(polygon)
    assert False, 'polygon bad: %s' % polygon


def array_contains(array, item):
    return any([is_same_vertex(item, x) for x in array])


def is_same_vertex(v0, v1):
    return np.isclose(v0, v1).all()


def points_in_common(a, b):
    '''
    a: [array(x1, y1, z1), ... array(xn, yn, zn)]
    b: [array(x1, y1, z1), ... array(xn, yn, zn)]
    --> [array(xk, yk, zk), ... array(xl, yl, zl)]
    with k and l being vertices in both polygons.
    '''
    result = []
    for vertex in a:
        if array_contains(b, vertex):
            result.append(vertex)
    return result


def get_number_of_vertices(obj):
    '''
    return the number of vertices - autocalculate,
    since it is not always entered...
    '''
    return len(get_polygon(obj))


def collect_walls(citysim_xml):
    '''return the Wall nodes objects
    that are walls (vertical) and have 4 vertices
    and rectangular'''
    result = []
    for wall in citysim_xml.findall('/District/Building/Zone/Wall'):
        if get_number_of_vertices(wall) != 4:
            # ignore this one
            continue
        polygon = get_polygon(wall)
        try:
            if not np.isclose(90.0, tilt(polygon)):
                # ignore this one too
                continue
        except:
            print 'bad polygon:', 'Wall@id=%s' % wall.get('id'), polygon
            continue
        vectors = [line[0] - line[1]
                   for line in zip(polygon, rotate(polygon))]
        if not all([np.isclose(90.0, angle2vecs(v[0], v[1]))
                    for v in zip(vectors, rotate(vectors))]):
            # not rectangular
            continue
        # meets criteria
        result.append(wall)
    return result


def get_polygon(wall):
    '''
    return a polygon representing the surface.
    each vertices is an np.array.
    '''
    polygon = []
    for v in wall.getchildren():
        if v.tag.startswith('V'):
            polygon.append(np.array((
                float(v.get('x')),
                float(v.get('y')),
                float(v.get('z')))))
    return polygon


def set_polygon(wall, polygon):
    '''
    set the vertices of a polygon.
    '''
    # delete old vertices
    for vertex_xml in wall.getchildren():
        if vertex_xml.tag.startswith('V'):
            wall.remove(vertex_xml)
    # add new vertices
    for i, v in enumerate(polygon):
        vertex_xml = etree.Element('V%i' % i)
        vertex_xml.set('x', str(v[0]))
        vertex_xml.set('y', str(v[1]))
        vertex_xml.set('z', str(v[2]))
        wall.append(vertex_xml)


def rotate(lst):
    '''[a, b, c] --> [b, c, a]'''
    result = lst[1:]
    result.append(lst[0])
    return result


def same_zone(wa, wb):
    '''return True, if wa and wb are both children of the
    same Building/Zone'''
    return wa.getparent() == wb.getparent()


def same_construction(wa, wb):
    '''return True, if wa and wb share construction information'''
    return wa.get('type') == wb.get('type')


def merge_windows(wa, wb):
    '''
    update the attributes for the glazing / windows e.g.:
        GlazingRatio="0.43"
        GlazingGValue="0.7"
        GlazingUValue="1.1"
        ShortWaveReflectance="0.2"
        Uvalue="0.5331238918939453"
    using a weighted average for each value.
    FIXME: is this physically correct?!
    '''
    aa = area(get_polygon(wa))
    ab = area(get_polygon(wb))
    attributes = ['GlazingRatio',
                  'GlazingGValue',
                  'GlazingUValue',
                  'ShortWaveReflectance',
                  'Uvalue']
    for attrib in attributes:
        wa.set(attrib, str(weighted_average(
            get_float(wa, attrib),
            get_float(wb, attrib),
            aa, ab)))


def get_float(element, attribute):
    return float(element.get(attribute, '0.0'))


def weighted_average(va, vb, aa, ab):
    return (aa * va + ab * vb) / (aa + ab)
