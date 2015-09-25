'''
shading.py

Simplify shading surfaces in the EnergyPlus model
by joining rectangular adjacent, coplanar surfaces
'''
from eppy.geometry.surface import tilt, angle2vecs
import numpy as np
import itertools


def simplify(idf):
    to_delete = simplify_one_level(collect_shading_walls(idf))
    while len(to_delete):
        for shading in to_delete:
            idf.removeidfobject(idf.getobject('SHADING:BUILDING:DETAILED',
                                              shading))
        to_delete = simplify_one_level(collect_shading_walls(idf))
    return idf


def simplify_one_level(shading_surfaces):
    '''
    run one pass of simplifications - this needs to be repeated until
    no more simplifications are found
    to_delete is a set of names of shading surfaces that were simplified.
    '''
    to_delete = set()
    print 'simplify_one_level', len(shading_surfaces)
    for sa, sb in itertools.combinations(shading_surfaces, 2):
        if sa.Name in to_delete or sb.Name in to_delete:
            # one of these has already been merged!
            continue
        pa = get_polygon(sa)
        pb = get_polygon(sb)
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
            sa, sb = sb, sa
            pa, pb = pb, pa
        set_polygon(sa, [pb[0], pa[1], pa[2], pb[3]])
        to_delete.add(sb.Name)
        print '-', sa.Name, sb.Name
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


def collect_shading_walls(idf):
    '''return the Shading:Building:Detailed objects
    that are walls (vertical) and have 4 vertices
    and rectangular'''
    result = []
    for shading in idf.idfobjects['SHADING:BUILDING:DETAILED']:
        if get_number_of_vertices(shading) != 4:
            # ignore this one
            continue
        polygon = get_polygon(shading)
        try:
            if not np.isclose(90.0, tilt(polygon)):
                # ignore this one too
                continue
        except:
            print 'bad polygon:', shading.Name, polygon
            continue
        vectors = [line[0] - line[1]
                   for line in zip(polygon, rotate(polygon))]
        if not all([np.isclose(90.0, angle2vecs(v[0], v[1]))
                    for v in zip(vectors, rotate(vectors))]):
            # not rectangular
            continue
        # meets criteria
        result.append(shading)
    return result


def get_polygon(shading):
    '''
    return a polygon representign the shading surface.
    each vertices is an np.array.
    '''
    vertices_index = shading.objls.index('Number_of_Vertices') + 1
    return get_vertices(shading.obj[vertices_index:])


def set_polygon(shading, polygon):
    '''
    set the vertices of a polygon.
    '''
    coordinates = [c for v in polygon for c in v]
    vertices_index = shading.objls.index('Number_of_Vertices') + 1
    shading.obj[vertices_index:] = coordinates


def rotate(lst):
    '''[a, b, c] --> [b, c, a]'''
    result = lst[1:]
    result.append(lst[0])
    return result


def get_vertices(coordinates):
    '''
    input: [x0, y0, z0, x1, y1, z1, ... xn, yn, zn]
    output: [(x0, y0, z0), ..., (xn, yn, zn)]
    '''
    xs = map(float, coordinates[0::3])
    ys = map(float, coordinates[1::3])
    zs = map(float, coordinates[2::3])
    return map(np.array, zip(xs, ys, zs))
