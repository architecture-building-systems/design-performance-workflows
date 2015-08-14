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

as a side effect, the epid tag is entered to all surfaces matched,
this is a prerequisite for co-simulation.
'''
