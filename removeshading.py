import numpy as np


def remove_extra_shading(idf):
    """remove shading from the model that isn't "seen"
    by the building surfaces. This model uses SHADING:BUILDING:DETAILED
    surfaces are tuples (TYPE, NAME, polygon) for the idf objects they
    represent.
    """
    bsurfaces = collect_building_surfaces(idf)
    ssurfaces = collect_shading_surfaces(idf)
    all_surfaces = bsurfaces.union(ssurfaces)
    keep_surfaces = set()
    for bsurf in bsurfaces:
        keep_surfaces.add(bsurf)
        print 'Building surface:', bsurf
        for ssurf in ssurfaces:
            # print '\tShading surface:', ssurf
            ray = create_ray(bsurf, ssurf)
            first = first_intersection(ray, all_surfaces, bsurf)
            if first and is_shading(first):
                # print '\t\tfirst:', first
                keep_surfaces.add(first)
    for ssurf in set(all_surfaces) - keep_surfaces:
        idf.removeidfobject(idf.getobject(*ssurf[:2]))
    return idf


def collect_building_surfaces(idf):
    return set((o.key, o.Name, get_polygon(o))
               for o in idf.idfobjects['WALL:DETAILED']
               if get_polygon(o))


def collect_shading_surfaces(idf):
    return set((o.key, o.Name, get_polygon(o))
               for o in idf.idfobjects['SHADING:BUILDING:DETAILED']
               if get_polygon(o))


def get_polygon(obj):
    obj_vertex_data = obj.obj[obj.objls.index('Number_of_Vertices')+1:]
    obj_vertex_data = map(float, obj_vertex_data)
    obj_vertices = zip(obj_vertex_data[0::3],
                       obj_vertex_data[1::3],
                       obj_vertex_data[2::3])
    obj_vertices = map(np.array, obj_vertices)
    try:
        polygon = Polygon(obj_vertices)
    except AssertionError:
        print 'ERROR with polygon not on plane:', obj.key, obj.Name
        return None
    return polygon


def create_ray(bsurf, ssurf):
    """create a Ray object from the middle of the building surface to the
    middle of the shading surface"""
    bpoly = bsurf[2]
    spoly = ssurf[2]
    bm = sum(bpoly.pts) / len(bpoly.pts)
    sm = sum(spoly.pts) / len(spoly.pts)
    ray = Ray(position=bm, direction=sm-bm)
    return ray


def first_intersection(ray, surfaces, bsurf):
    """Intersect the ray with each surface and then calculate the
    distance between the matches. Return the closest intersecting
    surface.
    """
    intersections = []
    for key, name, polygon in surfaces:
        if (key, name) == bsurf[:2]:
            continue
        point = polygon.intersection(ray)
        if point:
            assert len(point) == 1, 'oops, multiple intersections?'
            point = np.array(point[0])
            intersections.append((key, name, polygon, point))
    if not intersections:
        return None

    def distance(intersection):
        point = intersection[3]
        return np.linalg.norm(ray.position - point)

    return min(intersections, key=distance)[:3]


def is_shading(surface):
    return surface[0] == 'SHADING:BUILDING:DETAILED'


class Ray(object):
    """A ray in the global cartesian frame.
    NOTE: This code came from here: https://github.com/danieljfarrell/pvtrace/blob/master/pvtrace/Geometry.py"""  #noqa
    def __init__(self, position=[0., 0., 0.], direction=[0., 0., 1.]):
        self.position = np.array(position)
        self.direction = np.array(direction) / np.sqrt(
            np.dot(direction, np.array(direction).conj()))


def cmp_floats(a, b):
    """NOTE: This code came from here: https://github.com/danieljfarrell/pvtrace/blob/master/pvtrace/Geometry.py"""  #noqa
    abs_diff = abs(a-b)
    if abs_diff < 1e-12:
        return True
    else:
        return False


def magnitude(vector):
    """NOTE: This code came from here: https://github.com/danieljfarrell/pvtrace/blob/master/pvtrace/Geometry.py"""  #noqa
    return np.sqrt(np.dot(np.array(vector), np.array(vector)))


def norm(vector):
    return np.array(vector)/magnitude(np.array(vector))


class Polygon(object):
    """
    A (2D) Polygon with n (>2) points
    Only konvex polygons are allowed! Order of points is of course important!
    NOTE: This code came from here: https://github.com/danieljfarrell/pvtrace/blob/master/pvtrace/Geometry.py"""  #noqa

    def __init__(self, points):
        super(Polygon, self).__init__()
        self.pts = points
        # check if points are in one plane
        assert len(self.pts) >= 3, "You need at least 3 points to build a Polygon"  #noqa
        if len(self.pts) > 3:
            x_0 = np.array(self.pts[0])
            for i in range(1, len(self.pts)-2):
                # the determinant of the vectors (volume) must always be 0
                x_i = np.array(self.pts[i])
                x_i1 = np.array(self.pts[i+1])
                x_i2 = np.array(self.pts[i+2])
                det = np.linalg.det([x_0-x_i, x_0-x_i1, x_0-x_i2])
                assert cmp_floats(det, 0.0), "Points must be in a plane to create a Polygon"  #noqa

    def on_surface(self, point):
        """Returns True if the point is on the polygon's surface
        and false otherwise."""
        n = len(self.pts)
        anglesum = 0
        p = np.array(point)

        for i in range(n):
            v1 = np.array(self.pts[i]) - p
            v2 = np.array(self.pts[(i+1) % n]) - p

            m1 = magnitude(v1)
            m2 = magnitude(v2)

            if cmp_floats(m1*m2, 0.0):
                return True  # point is one of the nodes
            else:
                # angle(normal, vector)
                costheta = np.dot(v1, v2)/(m1*m2)
            anglesum = anglesum + np.arccos(costheta)
        return cmp_floats(anglesum, 2*np.pi)

    def contains(self, point):
        return False

    def surface_identifier(self, surface_point, assert_on_surface=True):
        return "polygon"

    def surface_normal(self, ray, acute=False):
        vec1 = np.array(self.pts[0])-np.array(self.pts[1])
        vec2 = np.array(self.pts[0])-np.array(self.pts[2])
        normal = norm(np.cross(vec1, vec2))
        return normal

    def intersection(self, ray):
        """Returns a intersection point with a ray and the polygon."""
        n = self.surface_normal(ray)

        # Ray is parallel to the polygon
        if cmp_floats(np.dot(np.array(ray.direction), n), 0.0):
            return None

        t = 1 / (np.dot(np.array(ray.direction), n)) * (
            np.dot(n, np.array(self.pts[0]))
            - np.dot(n, np.array(ray.position)))

        # Intersection point is behind the ray
        if t < 0.0:
            return None

        # Calculate intersection point
        point = np.array(ray.position) + t*np.array(ray.direction)

        # Check if intersection point is really in the polygon or only on the
        # (infinite) plane
        if self.on_surface(point):
            return [list(point)]

        return None


if __name__ == '__main__':
    from eppy.modeleditor import IDF, IDDAlreadySetError
    try:
        IDF.setiddname(r"C:\projects\UMEM-JBPS-Paper\models\Energy+.idd")
    except IDDAlreadySetError:
        pass
    idf = IDF(r"C:\projects\UMEM-JBPS-Paper\results\21-cosim-HPI.vt.idf")
    idf = remove_extra_shading(idf)
    with open(
            r"C:\projects\UMEM-JBPS-Paper\results\removed-shading.idf",
            'w') as f:
        f.write(idf.idfstr())
