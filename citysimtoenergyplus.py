'''
citysimtoenergyplus.py

Extract an EnergyPlus model (IDF) from a CitySim scene.
A template for the HVAC is provided, so this module is just
concerned with geometry, materials and construction.
'''

def extractidf(citysim, building, template):
    '''
    this is the main entry point to the module.
    citysim: a lxml.etree.ElementTree containing the CitySim scene.
    building: a string containing the building/@Name|id to extract.
        first, the @Name is checked and if not found, fall back to @id.
    template: a eppy.IDF object representing the template to add the geometry to.
        the template may contain HVAC etc. extractidf only knows a single zone
        called "SINGLE_ZONE".
    '''
