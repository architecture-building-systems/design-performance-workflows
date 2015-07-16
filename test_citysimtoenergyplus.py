import citysimtoenergyplus
from eppy import modeleditor
from lxml import etree
import os
import polygons
from decimal import Decimal


idd_path = os.path.join('testing', 'Energy+.idd')
modeleditor.IDF.setiddname(idd_path)


def construct_empty_idf():
    from StringIO import StringIO
    idf = modeleditor.IDF(StringIO(''))
    return idf


def test_construct_empty_idf():
    assert construct_empty_idf().idfstr() == ''


def test_idf_from_template():
    template_path = os.path.join('testing', 'test_template.idf')
    template = modeleditor.IDF(template_path)
    idf = citysimtoenergyplus.idf_from_template(template)
    assert idf.idfstr() == template.idfstr()
    building = idf.idfobjects['BUILDING'][0]
    building.Name = 'Some other name'
    assert idf.idfstr() != template.idfstr()


def test_add_constructions():
    # FIXME: add test for WallTypes have same name!
    citysim = etree.ElementTree(etree.XML('''
        <CitySim><District>
        <WallType id="0" name="DEFAULT_WALL_TYPE_0">
        <Layer Conductivity="0.47" Cp="900" Density="1600" Thickness="0.5" />
        </WallType>
        <WallType id="1" name="DEFAULT_WALL_TYPE_1">
        <Layer Conductivity="0.1" Cp="100" Density="1000" Thickness="0.1" />
        <Layer Conductivity="0.2" Cp="200" Density="2000" Thickness="0.2" />
        </WallType>
        <WallType id="2" name="DEFAULT_WALL_TYPE_2">
        <Layer Conductivity="0.1" Cp="100" Density="1000" Thickness="0.1" />
        <Layer Conductivity="0.2" Cp="200" Density="2000" Thickness="0.2" />
        <Layer Conductivity="0.3" Cp="300" Density="3000" Thickness="0.3" />
        </WallType>
        <WallType id="3" name="DEFAULT_WALL_TYPE_3">
        <Layer Conductivity="0.47" Cp="900" Density="1600" Thickness="0.5" />
        </WallType>
        <WallType id="4" name="DEFAULT_WALL_TYPE_4">
        <Layer Conductivity="0.47" Cp="900" Density="1600" Thickness="0.5" />
        </WallType>
        <WallType id="5" name="DEFAULT_WALL_TYPE_5">
        <Layer Conductivity="0.47" Cp="900" Density="1600" Thickness="0.5" />
        </WallType>
        <WallType id="6" name="DEFAULT_WALL_TYPE_6">
        <Layer Conductivity="0.47" Cp="900" Density="1600" Thickness="0.5" />
        </WallType>
        </District></CitySim>
    '''))
    building_xml = etree.XML('''
        <Building>
        <Zone>
            <Wall type="1"></Wall>
            <Wall type="2"></Wall>
            <Roof type="3"></Roof>
            <Roof type="4"></Roof>
            <Floor type="5"></Floor>
            <Floor type="6"></Floor>
        </Zone>
        </Building>
    ''')
    idf = construct_empty_idf()
    citysimtoenergyplus.add_constructions(citysim, building_xml, idf)
    assert len(idf.idfobjects['CONSTRUCTION']) == 6
    assert not idf.getobject('CONSTRUCTION', 'DEFAULT_WALL_TYPE_0'), \
        'should not be exported, not referenced'
    for i in range(1, 7):
        construction_name = 'DEFAULT_WALL_TYPE_%i' % i
        assert idf.getobject('CONSTRUCTION', construction_name), \
            'construction not found: %s in %s' % (construction_name, [c.Name for c in idf.idfobjects['CONSTRUCTION']])  # noqa
    assert idf.getobject('MATERIAL', 'DEFAULT_WALL_TYPE_1_M0')
    assert idf.getobject('MATERIAL', 'DEFAULT_WALL_TYPE_1_M1')
    assert not idf.getobject('MATERIAL', 'DEFAULT_WALL_TYPE_1_M2')
    m0 = idf.getobject('MATERIAL', 'DEFAULT_WALL_TYPE_1_M0')
    assert m0.Roughness == 'MediumSmooth'
    assert dequals(m0.Thickness, 0.1)
    assert dequals(m0.Conductivity, 0.1)
    assert dequals(m0.Density, 1000)
    assert dequals(m0.Specific_Heat, 100)
    assert dequals(m0.Thermal_Absorptance, 0.9)
    assert dequals(m0.Solar_Absorptance, 0.7)
    assert dequals(m0.Visible_Absorptance, 0.7)
    m1 = idf.getobject('MATERIAL', 'DEFAULT_WALL_TYPE_1_M1')
    assert m1.Roughness == 'MediumSmooth'
    assert dequals(m1.Thickness, 0.2)
    assert dequals(m1.Conductivity, 0.2)
    assert dequals(m1.Density, 2000)
    assert dequals(m1.Specific_Heat, 200)
    assert dequals(m1.Thermal_Absorptance, 0.9)
    assert dequals(m1.Solar_Absorptance, 0.7)
    assert dequals(m1.Visible_Absorptance, 0.7)
    cnames = [c.Name for c in idf.idfobjects['CONSTRUCTION']]
    assert len(set(cnames)) == len(cnames)


def test_add_floors():
    '''note: this code is highly dependent on the
    RevitModel_nowindows.xml contents!'''
    building_xml = get_building()
    idf = construct_empty_idf()
    citysimtoenergyplus.add_floors(building_xml, idf,
                                   {'5': 'TEST_CONSTRUCTION'})
    assert len(idf.idfobjects['FLOOR:DETAILED']), 'no floors exported!'
    assert len(idf.idfobjects['FLOOR:DETAILED']) == 1, \
        'too many floors exported!'
    assert idf.getobject('FLOOR:DETAILED', 'Floor19'), \
        'floor not exported or wrong name'
    f0 = idf.getobject('FLOOR:DETAILED', 'Floor19')
    assert f0.Name == 'Floor19'
    assert f0.Construction_Name == 'TEST_CONSTRUCTION'
    assert f0.Zone_Name == 'Zone10'
    assert f0.Outside_Boundary_Condition == 'Ground'
    assert f0.Number_of_Vertices == 4
    # FIXME: the below numbers might not be correct?
    r2 = lambda x: round(float(x), 2)
    assert map(r2, f0.obj[-4*3:]) == map(r2,
                                         [-25.55, 13.4348, 0.0,
                                          4.55, 13.4348, 0.0,
                                          4.55, -7.6602, 0.0,
                                          -25.55, -7.6602, 0.0])


def test_add_roofs():
    building_xml = get_building()
    idf = construct_empty_idf()
    citysimtoenergyplus.add_roofs(building_xml, idf,
                                  {'4': 'TEST_CONSTRUCTION'})
    assert len(idf.idfobjects['ROOFCEILING:DETAILED']), 'no roofs exported!'
    assert len(idf.idfobjects['ROOFCEILING:DETAILED']) == 4, \
        'too many roofs exported!'
    assert idf.getobject('ROOFCEILING:DETAILED', 'Roof15'), \
        'roof not exported or wrong name'
    r0 = idf.getobject('ROOFCEILING:DETAILED', 'Roof15')
    assert r0.Name == 'Roof15'
    assert r0.Construction_Name == 'TEST_CONSTRUCTION'
    assert r0.Zone_Name == 'Zone10'
    assert r0.Outside_Boundary_Condition == 'Outdoors'
    assert r0.Number_of_Vertices == 3
    # FIXME: the below numbers might not be correct?
    round2 = lambda x: round(float(x), 2)
    assert map(round2, r0.obj[-3*3:]) == map(round2,
                                             [4.29, -7.41, 4.0,
                                              4.29, 13.18, 4.0,
                                              -6.0, 2.89, 9.94])


def test_add_walls():
    building_xml = get_building()
    idf = construct_empty_idf()
    citysimtoenergyplus.add_walls(building_xml, idf,
                                  {'3': 'TEST_CONSTRUCTION'})
    assert len(idf.idfobjects['WALL:DETAILED']), 'no walls exported!'
    assert len(idf.idfobjects['WALL:DETAILED']) == 4, \
        'too many walls exported!'
    assert idf.getobject('WALL:DETAILED', 'Wall11'), \
        'wall not exported or wrong name'
    w0 = idf.getobject('WALL:DETAILED', 'Wall11')
    assert w0.Name == 'Wall11'
    assert w0.Construction_Name == 'TEST_CONSTRUCTION'
    assert w0.Zone_Name == 'Zone10'
    assert w0.Outside_Boundary_Condition == 'Outdoors'
    assert w0.Number_of_Vertices == 4
    # FIXME: the below numbers might not be correct?
    round2 = lambda x: round(float(x), 2)
    assert map(round2, w0.obj[-4*3:]) == map(round2,
                                             [-25.5025, 13.3873, 0.0,
                                              -25.5025, 13.3873, 4.0,
                                              4.4975, 13.3873, 4.0,
                                              4.4975, 13.3873, 0.0])


def test_open_questions():
    assert False, 'implement the zone (instead of template?)'
    assert False, 'what to do about roofs?'
    assert False, 'how about testing the template for multiple zones?'


def test_add_windows():
    building_xml = get_building()
    idf = construct_empty_idf()
    citysimtoenergyplus.add_windows(building_xml, idf)
    for wall_xml in building_xml.findall('Zone/Wall'):
        uvalue = Decimal(wall_xml.get('GlazingUValue'), default=0)
        gvalue = Decimal(wall_xml.get('GlazingGValue'), default=0)
        ratio = Decimal(wall_xml.get('GlazingRatio'), default=0)
        wallid = 'Wall%s' % wall_xml.get('id')
        windowid = 'Window%s' % wall_xml.get('id')
        if ratio > 0:
            construction = idf.getobject('CONSTRUCTION',
                                         'WindowConstructionU%.2fG%.2f' % (
                                             uvalue, gvalue))
            assert construction, 'no construction defined for this window!'
            assert len(construction.obj) == 3
            material = idf.getobject('WINDOWMATERIAL:SIMPLEGLAZINGSYSTEM',
                                     'WindowMaterialU%.2fG%.2f' % (
                                         uvalue, gvalue))
            assert material, 'no material defined for this window!'
            assert construction.obj[-1] == material.Name
            assert Decimal(material.UFactor) == uvalue
            assert Decimal(material.Solar_Heat_Gain_Coefficient) == gvalue
            window = idf.getobject('FENESTRATIONSURFACE:DETAILED', windowid)
            wall = idf.getobject('WALL:DETAILED', wallid)
            assert window, 'window was not exported!'
            assert window.Surface_Type == 'Window'
            assert window.Construction_Name == construction.Name
            assert window.Building_Surface_Name == wallid
            assert window.Frame_and_Divider_Name == ''
            assert window.Number_of_Vertices == wall.Number_of_Vertices
            window_vertices = window.obj[window.Number_of_Vertices * -3:]
            wall_vertices = wall.obj[wall.Number_of_Vertices * -3:]
            window_polygon = zip(window_vertices[::3],
                                 window_vertices[1::3],
                                 window_vertices[2::3])
            wall_polygon = zip(wall_vertices[::3],
                               wall_vertices[1::3],
                               wall_vertices[2::3])
            assert close_enough(
                polygons.area(window_polygon),
                polygons.area(wall_polygon) *
                ratio)


def close_enough(f1, f2):
    return abs(f1 - f2) < 0.01


def dequals(f1, f2):
    return Decimal(f1) == Decimal(f2)


def get_building():
    citysim = get_model()
    return citysimtoenergyplus.find_building('6', citysim)


def get_model():
    with open(os.path.join('testing', 'RevitModel.xml'), 'r') as f:
        citysim = etree.parse(f)
    return citysim
