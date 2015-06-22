# Testing design-performance-workflows

This document describes the VisTrails in this folder. They are intended to
demonstrate and test the design-performance-workflows package.


# List of modules (mapping to workflows)

- AcquireModelSnapshot (dpw-02-AcquireModelSnapshot)
- AddFmuToIdf
- AddFmuToIdfLwr
- AddOutputVariable
- AddOutputVariableList
- EnergyPlusToFmu
- FileToList
- GenerateIdf
- Idf
- ModelSnapshot
- RevitToCitySim
- RunCitySim
- RunEnergyPlus (dpw-01-RunEnergyPlus, dpw-02-AcquireModelSnapshot)
- RunCoSimulation
- RunMockCoSimulation
- StripInternalLoads
- SaveEnergyPlusResults
- SaveCoSimResults
- SaveResults
- XmlElementTree
- XPath
- XPathSetAttribute

# dpw-01-RunEnergyPlus

# dpw-02-AcquireModelSnapshot

Modules used:

- AcquireModelSnapshot
- GenerateIdf
- RunEnergyPlus
- SaveEnergyPlusResults

In order to use `AcquireModelSnapshot`, you need to have the Design Performance Viewer (DPV) installed
on your system and a model open in Autodesk Revit. 

In order to use `GenerateIdf` you need to install the RevitPythonShell (RPS) and
set the startup script to `../r2cs_server.py`.

In order to use `RunEnergyPlus` you need an installation of EnergyPlus (any version above 6 should work).

`SaveEnergyPlusResults` is set up to save to the temporary directory in this VisTrails.
