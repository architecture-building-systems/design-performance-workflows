from __future__ import division
'''
polygons.py

A bunch of functions I found here:
    http://stackoverflow.com/questions/12642256/ \
        python-find-area-of-polygon-from-xyz-coordinates

for finding the area of a 3d polygon.
'''
import numpy as np


# determinant of matrix a
def det(a):
    return (a[0][0] * a[1][1] * a[2][2]
            + a[0][1] * a[1][2] * a[2][0]
            + a[0][2] * a[1][0] * a[2][1]
            - a[0][2] * a[1][1] * a[2][0]
            - a[0][1] * a[1][0] * a[2][2]
            - a[0][0] * a[1][2] * a[2][1])


# unit normal vector of plane defined by points a, b, and c
def unit_normal(a, b, c):
    x = det([[1, a[1], a[2]],
             [1, b[1], b[2]],
             [1, c[1], c[2]]])
    y = det([[a[0], 1, a[2]],
             [b[0], 1, b[2]],
             [c[0], 1, c[2]]])
    z = det([[a[0], a[1], 1],
             [b[0], b[1], 1],
             [c[0], c[1], 1]])
    magnitude = (x ** 2 + y ** 2 + z ** 2) ** .5
    return (x / magnitude, y / magnitude, z / magnitude)


# dot product of vectors a and b
def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


# cross product of vectors a and b
def cross(a, b):
    x = a[1] * b[2] - a[2] * b[1]
    y = a[2] * b[0] - a[0] * b[2]
    z = a[0] * b[1] - a[1] * b[0]
    return (x, y, z)


# area of polygon poly
def area(poly):
    if len(poly) < 3:  # not a plane - no area
        return 0.0

    total = [0.0, 0.0, 0.0]
    for i in range(len(poly)):
        vi1 = poly[i]
        if i == len(poly) - 1:
            vi2 = poly[0]
        else:
            vi2 = poly[i + 1]
        prod = cross(vi1, vi2)
        total[0] += prod[0]
        total[1] += prod[1]
        total[2] += prod[2]
    result = dot(total, unit_normal(poly[0], poly[1], poly[2]))
    return abs(result / 2.0)


# here are some numpy equivalents:
def np_poly_area(poly):
    '''area of polygon, poly, copied from here:
    http://oco-carbon.com/coding/python-and-energyplus-polygon-areas-in-3d-space
    '''
    if len(poly) < 3:  # not a polygon - no area
        return 0
    total = [0, 0, 0]
    N = len(poly)
    for i in range(N):
        vi1 = poly[i]
        vi2 = poly[(i+1) % N]
        prod = np.cross(vi1, vi2)
        total[0] += prod[0]
        total[1] += prod[1]
        total[2] += prod[2]
    result = np.dot(total, np_unit_normal(poly[0], poly[1], poly[2]))
    return abs(result/2)


# unit normal vector of plane defined by points a, b, and c
def np_unit_normal(a, b, c):
    x = np.linalg.det([[1, a[1], a[2]],
                       [1, b[1], b[2]],
                       [1, c[1], c[2]]])
    y = np.linalg.det([[a[0], 1, a[2]],
                       [b[0], 1, b[2]],
                       [c[0], 1, c[2]]])
    z = np.linalg.det([[a[0], a[1], 1],
                       [b[0], b[1], 1],
                       [c[0], c[1], 1]])
    magnitude = (x**2 + y**2 + z**2)**.5
    return (x/magnitude, y/magnitude, z/magnitude)


def get_vertices_by_area_ratio(original_vertices, ratio, epsilon=0.001):
    '''return a new set of vertices with a given area ratio to the original
    polygon'''
    new_vertices = [p.copy() for p in original_vertices]
    pm = sum(original_vertices) / len(original_vertices)
    step = 0.5  # valid steps: 0..1

    def calc_ratio(new_poly, old_poly):
        return np_poly_area(new_poly) / np_poly_area(old_poly)

    def do_step(poly, pm, step):
        return [p + step*(pm-p) for p in poly]

    loop_count = 0
    max_loop_count = 1000
    while True:
        new_vertices = do_step(original_vertices, pm, step)
        current_ratio = calc_ratio(new_vertices, original_vertices)
        if abs(current_ratio - ratio) < epsilon:
            return new_vertices
        if loop_count > max_loop_count:
            return None  # didn't converge?
        if current_ratio > ratio:
            step += step/2  # decrease polygon area
        else:
            step -= step/2  # increase polygon area
        loop_count += 1
