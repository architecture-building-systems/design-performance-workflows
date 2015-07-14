import citysimtoenergyplus
from eppy import modeleditor
from lxml import etree
import os


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
    '''note: this code is highly dependent on the RevitModel_nowindows.xml contents!'''
    building_xml = get_building_RevitModel_nowindows()
    idf = construct_empty_idf()
    citysimtoenergyplus.add_floors(building_xml, idf,
                                   {'5': 'TEST_CONSTRUCTION'})
    assert len(idf.idfobjects['FLOOR:DETAILED']), 'no floors exported!'
    assert len(idf.idfobjects['FLOOR:DETAILED']) == 1, 'too many floors exported!'
    assert idf.getobject('FLOOR:DETAILED', 'Floor19'), 'floor not exported or wrong name'
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
    building_xml = get_building_RevitModel_nowindows()
    idf = construct_empty_idf()
    citysimtoenergyplus.add_roofs(building_xml, idf,
                                  {'4': 'TEST_CONSTRUCTION'})
    assert len(idf.idfobjects['ROOFCEILING:DETAILED']), 'no roofs exported!'
    assert len(idf.idfobjects['ROOFCEILING:DETAILED']) == 4, 'too many roofs exported!'
    assert idf.getobject('ROOFCEILING:DETAILED', 'Roof15'), 'roof not exported or wrong name'
    r0 = idf.getobject('ROOFCEILING:DETAILED', 'Roof15')
    assert r0.Name == 'Roof15'
    assert r0.Construction_Name == 'TEST_CONSTRUCTION'
    assert r0.Zone_Name == 'Zone10'
    assert r0.Outside_Boundary_Condition == 'Outdoors'
    assert r0.Number_of_Vertices == 3
    # FIXME: the below numbers might not be correct?
    round2 = lambda x: round(float(x), 2)
    assert map(round2, r0.obj[-3*3:]) == map(round2,
                                             [4.29, -7.3981, 4.0,
                                              4.29, 13.1727, 4.0,
                                              -6.3076, 2.8873, 10.1185])


def dequals(f1, f2):
    from decimal import Decimal
    return Decimal(f1) == Decimal(f2)

def get_building_RevitModel_nowindows():
    citysim = get_RevitModel_nowindows()
    return citysimtoenergyplus.find_building('6', citysim)


def get_RevitModel_nowindows():
    with open(os.path.join('testing', 'RevitModel_nowindows.xml'), 'r') as f:
        citysim = etree.parse(f)
    return citysim
