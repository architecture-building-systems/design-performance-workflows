import citysimtoenergyplus


def test_idf_from_template():
    import eppy.modeleditor
    reload(eppy.modeleditor)
    import os
    idd_path = os.path.join('testing', 'Energy+.idd')
    template_path = os.path.join('testing', 'test_template.idf')
    eppy.modeleditor.IDF.setiddname(idd_path)
    template = eppy.modeleditor.IDF(template_path)
    idf = citysimtoenergyplus.idf_from_template(template)
    assert idf.idfstr() == template.idfstr()
    building = idf.idfobjects['BUILDING'][0]
    building.Name = 'Some other name'
    assert idf.idfstr() != template.idfstr()
