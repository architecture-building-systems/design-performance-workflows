# vim: set fileencoding=utf-8 :
# This file is licensed under the terms of the MIT license. See the file
# "LICENSE.txt" in the project root for more information.
#
# This module was developed by Daren Thomas at the assistant chair for
# Sustainable Architecture and Building Technologies (Suat) at the Institute of
# Technology in Architecture, ETH Zürich. See http://suat.arch.ethz.ch for
# more information.

'''
revittocitysim.py

Export a DPV ModelSnapshot to CitySim for simulation.
'''
from xml.etree import ElementTree
import magictree as mt
import clr

clr.AddReference('System.Xml.Linq')

# Default values used for exporting...
#DEFAULT_INFILTRATION = 0.4
DEFAULT_INFILTRATION = 0.2  # will this be used from now on?
DEFAULT_TMAX = 26.0
DEFAULT_TMIN = 20.0
DEFAULT_GLAZING_G_VALUE = 0.5
DEFAULT_GLAZING_RATIO = 0.5
DEFAULT_GLAZING_U_VALUE = 1.3
DEFAULT_SHORT_WAVE_REFLECTANCE = 0.2
DEFAULT_OPENABLE_RATIO = 0.5
DEFAULT_ZONE_PSI = 0.3


def next_id():
    """create unique ids
    """
    if not hasattr(next_id, '__id'):
        next_id.__id = 0
    id = next_id.__id
    next_id.__id += 1
    return id


def id_map(key):
    """map a key to an id, so that each new
    key gets a new id (next_id()), and each invocation
    with the same key get's the same id.
    """
    if not hasattr(id_map, '__map'):
        id_map.__map = {}
    if not key in id_map.__map:
        id_map.__map[key] = next_id()
    return id_map.__map[key]


def build_citysim_xml(snapshot):
    """Builds a CitySim XML file based on the ModelSnapshot.
    The structure follows the "XML guide for the CitySim Solver"
    document.
    """
    # FIXME: this is the place to enable the multi-zone export!
    # (just comment out the following line...)
    snapshot = merge_zones(snapshot)
    citysim = mt.CitySim(
        mt.Simulation(beginMonth='1', endMonth='12',
                      beginDay='1', endDay='31'),
        mt.Climate(location='test.cli'))
    # The district
    district = mt.District()
    citysim.append(district)
    district.append(export_far_field_obstructions())
    district.append(export_default_wall_type(snapshot))
    district.append(export_default_roof_type(snapshot))
    district.append(export_default_floor_type(snapshot))
    append_range(district, export_wall_types(snapshot))
    append_range(district, export_roof_types(snapshot))
    append_range(district, export_floor_types(snapshot))
    # FIXME: append a dummy walltype for shading objects (the other buildings)
    district.append(export_building(snapshot))
    for building in export_shading_surfaces(snapshot):
        district.append(building)
    return prettify(citysim)


def append_range(element, seq):
    for e in seq:
        element.append(e)


def export_shading_surfaces(snapshot):
    """collect the shading surfaces back into buildings by their
    mass object id and export them as buildings with default values.
    Each shading surface in the snapshot has an id like
    "DpvShadingSurface:1158832:0" - the middle id ("1158832") here is the
    name of the building.
    """
    from itertools import groupby

    def gbkey(value):
        """use this as the key to group the shading surfaces by building.

        The value will be something like: "DpvShadingSurface:1158832:0"
        with "1158832" being the id of the mass object - all such surfaces
        will belong to the same mass object / building.
        """
        return value.Id.split(':')[1]
    for id, shading_building in groupby(snapshot.ShadingSurfaces, gbkey):
        yield export_shading_building(list(shading_building))


def export_shading_building(shading_building):
    """use a list of DpvShadingSurface objects to build a dummy building
    in CitySim xml format.
    """
    walls = [w for w in shading_building
             if abs(w.Orientation.Z) < 0.001]
    roof = max((r for r in shading_building
                if abs(r.Orientation.Z) > 0.001),
               key=lambda s: s.Points[0].Z)
    floor = min((f for f in shading_building
                 if abs(f.Orientation.Z) > 0.001),
                key=lambda s: s.Points[0].Z)
    building_id = int(roof.Id.split(':')[1])
    building = mt.Building(Ninf=str(DEFAULT_INFILTRATION),
                           Tmax=str(DEFAULT_TMAX),
                           Tmin=str(DEFAULT_TMIN),
                           Simulate="true",
                           id=str(building_id))
    building.append(export_heat_tank(building_id))
    building.append(export_cool_tank(building_id))
    building.append(export_heat_source(building_id))
    zone = mt.Zone(GroundFloor="true", Psi=str(DEFAULT_ZONE_PSI),
                   volume=str(calculate_volume(roof, floor)),
                   id=str(building_id))
    building.append(zone)
    for wall in walls:
        zone.append(
            mt.Wall(
                *export_vertices(wall.Points),
                GlazingGValue=str(DEFAULT_GLAZING_G_VALUE),
                GlazingRatio=str(DEFAULT_GLAZING_RATIO),
                GlazingUValue=str(DEFAULT_GLAZING_U_VALUE),
                OpenableRatio=str(DEFAULT_OPENABLE_RATIO),
                ShortWaveReflectance=str(DEFAULT_SHORT_WAVE_REFLECTANCE),
                id=str(next_id()),
                ep_id=wall.Id,
                type=str(id_map("DEFAULT_WALL_TYPE"))))
    zone.append(
        mt.Roof(
            *export_vertices(roof.Points),
            GlazingGValue="0.0",
            GlazingRatio="0.0",
            GlazingUValue="0.0",
            OpenableRatio="0.0",
            ShortWaveReflectance=str(DEFAULT_SHORT_WAVE_REFLECTANCE),
            id=str(next_id()),
            ep_id=roof.Id,
            type=str(id_map("DEFAULT_ROOF_TYPE"))))
    zone.append(
        mt.Floor(
            *export_vertices(floor.Points),
            id=str(next_id()),
            ep_id=floor.Id,
            type=str(id_map("DEFAULT_FLOOR_TYPE"))))
    return building


def export_heat_tank(building_id):
    """Export a heat tank tag.

    The heat tank tag will look like this:

        <HeatTank id="1" name="default Heat Tank 1"
                  brand="Rack" model="RTB-25" Cp="4180.0"
                  V="0.01" phi="20.0" rho="1000.0" Tmin="20.0"
                  Tmax="35.0"/>
    """
    name = 'default Heat Tank for building %d' % building_id
    return mt.HeatTank(
        id=str(id_map(name)),
        name=name,
        brand='Rack',
        model='RTB-25',
        Cp='4180.0',
        V='0.01',
        phi='20.0',
        rho='1000.0',
        Tmin='20.0',
        Tmax='35.0')


def export_cool_tank(building_id):
    """Export a Cooltank, e.g.:
        <CoolTank id="2" name="default Cool Tank 1"
         brand="Unknown" model="Unknown" Cp="4180.0"
         V="0.01" phi="20.0" rho="1000.0" Tmin="5.0"
         Tmax="20.0"/>
    """
    name = 'default Cool Tank for building %d' % building_id
    return mt.CoolTank(
        id=str(id_map(name)),
        name=name,
        brand="Unknown",
        model="Unknown",
        Cp="4180.0",
        V="0.01",
        phi="20.0",
        rho="1000.0",
        Tmin="5.0",
        Tmax="20.0")


def export_heat_source(building_id):
    """Export the HeatSource tag with a fixed content (boiler).

    The result will look like this:


        <HeatSource beginDay="258" endDay="151">
            <Boiler id="1" name="PARKER T300L" brand="PARKER"
                    model="T300L" fuelID="1" eta_th="0.95" Pmax="1.0E12"/>
        </HeatSource>
    """
    return mt.HeatSource(
        mt.Boiler(
            id=str(id_map('Boiler for building %d' % building_id)),
            name='PARKER T300L',
            brand='PARKER',
            model='T300L',
            fuelID='1',
            eta_th='0.95',
            Pmax='1.0E12'),
        beginDay='258',
        endDay='151')


def calculate_volume(roof, floor):
    """Assuming the building is a cube kind of shape,
    return the volume of the shading surface building.
    """
    return (roof.Points[0].Z - floor.Points[0].Z) * calculate_area(floor)


def calculate_area(floor):
    """assume floor has a rectangular shape...
    """
    from DesignPerformanceViewer.Model import Point
    from System.Collections.Generic import List
    return Point.CalculateAreaXY(List[Point](floor.Points))


def export_thermal_zones(snapshot):
    """returns a <Zone/> element for each thermal zone in the building
    """
    for zone in snapshot.Zones:
        xzone = mt.Zone(
            *export_surfaces_for_zone(snapshot, zone),
            id=str(next_id()),
            ep_id=zone.Id,
            volume=str(zone.Volume),
            Psi=str(DEFAULT_ZONE_PSI),  # FIXME: what value should we use here?
            GroundFloor=bool_to_xml(is_zone_ground_floor(snapshot, zone)))
        xzone.append(export_occupants(snapshot))
        yield xzone


def export_surfaces_for_zone(snapshot, zone):
    """create a list of the surfaces in the zone and return that.
    """
    for wall in export_walls(snapshot, zone):
        yield wall
    for roof in export_roofs(snapshot, zone):
        yield roof
    for floor in export_floors(snapshot, zone):
        yield floor


def export_roofs(snapshot, zone):
    """export all the roofs in a zone.
    """
    return (export_single_roof(r)
            for r in snapshot.Roofs
            if zone in snapshot.RoofConnections[r])


def export_floors(snapshot, zone):
    """export all the floors in a zone.
    """
    return (export_single_floor(f)
            for f in snapshot.Floors
            if zone in snapshot.FloorConnections[f])


def export_walls(snapshot, zone):
    """exports the walls for a given zone
    """
    return (export_single_wall(snapshot, w)
            for w in snapshot.Walls
            if zone in snapshot.WallConnections[w])


def export_single_wall(snapshot, wall):
    """exports a single wall
    """
    wt_idx = id_map(wall.Type.Id)
    gr, gv, uv = calculate_glazing_values(wall, snapshot)
    return mt.Wall(
        *export_vertices(wall.Points),
        id=str(next_id()),
        ep_id=wall.Id,
        type=str(wt_idx),
        ShortWaveReflectance="0.2",  # FIXME: how to calculate this value?
        GlazingRatio=str(gr),
        GlazingGValue=str(gv),
        GlazingUValue=str(uv),
        OpenableRatio=str(0.5))  # FIXME: what is the value here?


def export_single_roof(roof):
    """exports a single roof
    """
    return mt.Roof(
        *export_vertices(roof.Points),
        ShortWaveReflectance=str(
            DEFAULT_SHORT_WAVE_REFLECTANCE),  # FIXME: how to calculate this?
        GlazingRatio="0.0",  # FIXME: we don't support glazing in roofs
        GlazingGValue="0.0",
        GlazingUValue="0.0",
        OpenableRatio="0.0",
        id=str(next_id()),
        ep_id=roof.Id,
        type=str(id_map(roof.Type.Id)))


def export_single_floor(floor):
    """exports a single floor
    """
    return mt.Floor(
        *export_vertices(floor.Points),
        id=str(next_id()),
        ep_id=floor.Id,
        type=str(id_map(floor.Type.Id)))


def calculate_glazing_values(wall, snapshot):
    """Returns the tuple (glazing_ratio, glazing_g_value, glazing_u_value) for
    the glazing on a wall. A weighted average is used for the glazing_g_value
    and the glazing_u_value.
    NOTE: the wall area does not include window areas, so those are added for
    the totals!
    """
    windows = [w for w in snapshot.Windows
               if snapshot.WindowConnections[w].Id == wall.Id]
    total_window_area = sum(w.Area for w in windows)
    total_area = wall.Area + total_window_area
    glazing_ratio = total_window_area / total_area
    glazing_u_value = weighted_average(
        windows, get_window_u_value, lambda w: w.Area)
    glazings_g_value = weighted_average(
        windows, get_window_g_value, lambda w: w.Area)
    return glazing_ratio, glazings_g_value, glazing_u_value


def get_window_u_value(window):
    """For windows based on SimpleGlazingSystems, returns the u-value.
    Otherwise, an exception is thrown.
    """
    assert hasattr(window.Type.Layers[0].Material, 'GValue'), \
        "SimpleGlazingSystem required"
    assert len(window.Type.Layers) == 1, "SimpleGlazingSystem required"
    return window.Type.Layers[0].Material.UValue


def get_window_g_value(window):
    """For windows based on SimpleGlazingSystems, returns the g-value.
    Otherwise, an exception is thrown.
    """
    assert hasattr(window.Type.Layers[0].Material, 'GValue'), \
        "SimpleGlazingSystem required"
    assert len(window.Type.Layers) == 1, "SimpleGlazingSystem required"
    return window.Type.Layers[0].Material.GValue


def weighted_average(items, value, weight):
    numerator = sum(value(i) * weight(i) for i in items)
    divisor = sum(weight(i) for i in items)
    return (numerator / divisor) if divisor != 0 else None


def export_vertices(points):
    """export a list of vertices
    """
    for idx, point in enumerate(points):
        yield getattr(mt, "V" + str(idx))(
            x=str(point.X),
            y=str(point.Y),
            z=str(point.Z))


def bool_to_xml(b):
    """returns either "true" or "false" based on a boolean interpretation of b
    """
    if b:
        return "true"
    return "false"


def is_zone_ground_floor(snapshot, zone):
    return any([f.IsExterior for f in snapshot.Floors
                if zone in snapshot.FloorConnections[f]])


def export_building(snapshot):
    """Returns an Element describing the main building in the
    ModelSnapshot (as opposed to the mass objects used for shading)
    in a <Building/> tag.
    """
    building_id = id_map('__BUILDING__')
    building = mt.Building(
        id=str(building_id),
        Ninf=str(DEFAULT_INFILTRATION),
        Tmin="20.0",
        Tmax="26.0",
        Simulate="ep")
    building.append(export_heat_tank(building_id))
    building.append(export_cool_tank(building_id))
    building.append(export_heat_source(building_id))
    append_range(building, export_thermal_zones(snapshot))
    return building


def export_no_occupants(snapshot):
    """Returns an <Occupants/> tag set up for testing CitySim
    with no occupants.
    """
    occupants = mt.Occupants(n=str(0))
    occupants.append(mt.Weekday(
        **dict(('p' + str(idx + 1), str(0))
               for idx in range(24))))
    occupants.append(mt.Saturday(
        **dict(('p' + str(idx + 1), str(0))
               for idx in range(24))))
    occupants.append(mt.Sunday(
        **dict(('p' + str(idx + 1), str(0))
               for idx in range(24))))
    return occupants


def export_occupants(snapshot):
    """Returns an <Occupants/> tag set up for use with CitySim
    based on the schedule of the ModelSnapshot.
    """
    from DesignPerformanceViewer.Util import Settings
    schedule = Settings.Instance.GetSchedule(snapshot.BuildingCategory)
    n_persons = round(
        snapshot.EnergyRelatedFloorArea / schedule.ZoneFloorAreaPerPerson)
    # FIXME: WE'RE EVIL!! UGH THE SHAME!! MY EYES!! I NEED A VACATION!!
    n_persons = round(n_persons / 2.0)
    occupants = mt.Occupants(n=str(n_persons))
    # weekdays
    schedule_data = Settings.Instance.GetScheduleData(
        snapshot.BuildingCategory)
    weekdays = [d for d in schedule_data if 'Weekdays' in d.For]
    weekdays = sorted(weekdays, lambda a, b: cmp(a.Until, b.Until))
    assert len(weekdays) == 24, "Expected occupancy level per hour: weekdays"
    occupants.append(mt.Weekday(
        **dict(("p" + str(idx + 1), str(d.Occupancy))
               for idx, d in enumerate(weekdays))))
    weekends = [d for d in schedule_data if 'Weekends' in d.For]
    weekends = sorted(weekends, lambda a, b: cmp(a.Until, b.Until))
    assert len(weekends) == 24, "Expected occupancy level per hour: weekends"
    occupants.append(mt.Saturday(
        **dict(("p" + str(idx + 1), str(d.Occupancy))
               for idx, d in enumerate(weekends))))
    occupants.append(mt.Sunday(
        **dict(("p" + str(idx + 1), str(d.Occupancy))
               for idx, d in enumerate(weekends))))
    return occupants


def export_far_field_obstructions():
    """Returns a dummy version of the Far Field Obstruction profile
    """
    return mt.FarFieldObstructions(
        *[mt.Point(phi="%d.0" % i, theta="2.0") for i in range(0, 360, 10)])


def export_default_wall_type(snapshot):
    """Returns a wall type for use with the shading buildings.
    """
    return mt.WallType(mt.Layer(Thickness="0.5",
                                Conductivity="0.47",
                                Cp="900",
                                Density="1600"),
                       id=str(id_map("DEFAULT_WALL_TYPE")),
                       name="DEFAULT_WALL_TYPE")


def export_default_roof_type(snapshot):
    """Returns a roof type for use with the shading buildings.
    """
    return mt.WallType(mt.Layer(Thickness="0.5",
                                Conductivity="0.47",
                                Cp="900",
                                Density="1600"),
                       id=str(id_map("DEFAULT_ROOF_TYPE")),
                       name="DEFAULT_ROOF_TYPE")


def export_default_floor_type(snapshot):
    """Returns a floor type for use with the shading buildings.
    """
    return mt.WallType(mt.Layer(Thickness="0.5",
                                Conductivity="0.47",
                                Cp="900",
                                Density="1600"),
                       id=str(id_map("DEFAULT_FLOOR_TYPE")),
                       name="DEFAULT_FLOOR_TYPE")


def export_wall_types(snapshot):
    """Returns a list of <WallType/> tags, one for each
    wall construction in the ModelSnapshot."""
    return [mt.WallType(*export_construction_layers(wt),
                        id=str(id_map(wt.Id)),
                        name=wt.Id)
            for wt in snapshot.WallTypes.Values]


def export_roof_types(snapshot):
    """Returns a list of <WallType/> tags, one for each roof
    construction in the ModelSnaphsot."""
    return [mt.WallType(*export_construction_layers(rt),
                        id=str(id_map(rt.Id)),
                        name=rt.Id)
            for rt in snapshot.RoofTypes.Values]


def export_floor_types(snapshot):
    """Returns a list of <WallType/> tags, one for each floor
    construction in the ModelSnaphsot."""
    return [mt.WallType(*export_construction_layers(ft),
                        id=str(id_map(ft.Id)),
                        name=ft.Id)
            for ft in snapshot.FloorTypes.Values]


def export_construction_layers(construction):
    """Returns a list of <Layer/> tags, for the layers in
    a construction, starting from the outside layer."""
    return [mt.Layer(
            Thickness=str(layer.Thickness),
            Conductivity=str(layer.Material.Conductivity),
            Cp=str(layer.Material.SpecificHeat),
            Density=str(layer.Material.Density))
            for layer in construction.Layers]


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    from System.Xml.Linq import XDocument
    doc = XDocument.Parse(ElementTree.tostring(elem, 'utf-8'))
    return doc.ToString()


def get_revit():
    """be nice to pyflakes, it's only a machine!
    """
    import __builtin__
    return __builtin__.__revit__


def take_snapshot():
    """Use the DesignPerformanceViewer libraries to create a
    ModelSnapshot object
    """
    clr.AddReferenceToFile('DpvApplication.dll')
    clr.AddReferenceToFile('DesignPerformanceViewer.dll')
    from DesignPerformanceViewer import DpvApplication
    dpv = DpvApplication.DpvApplication()
    doc = get_revit().ActiveUIDocument.Document
    return dpv.TakeSnapshot(doc)


def merge_zones(snapshot):
    """take a multi-zone snapshot and merge it into
    a single-zone snapshot.
    """
    from DesignPerformanceViewer.Model import DpvZone
    single_zone = DpvZone()
    single_zone.Id = "SINGLE_ZONE"
    single_zone.BuildingCategory = list(snapshot.Zones)[0].BuildingCategory
    single_zone.Volume = sum([z.Volume for z in snapshot.Zones])
    connections = list(snapshot.WallConnections.Values)
    connections += list(snapshot.FloorConnections.Values)
    connections += list(snapshot.CeilingConnections.Values)
    connections += list(snapshot.RoofConnections.Values)
    for c in connections:
        for zone in snapshot.Zones:
            if c.Contains(zone):
                c.Remove(zone)
        c.Add(single_zone)
    zones_to_delete = list(snapshot.Zones)
    while zones_to_delete:
        zone = zones_to_delete.pop()
        snapshot.DeleteZone(zone)
    snapshot.AddZone(single_zone)
    return snapshot


if __name__ == '__main__':
    try:
        snapshot = take_snapshot()
        print build_citysim_xml(snapshot)
    except:
        import traceback
        traceback.print_exc()
