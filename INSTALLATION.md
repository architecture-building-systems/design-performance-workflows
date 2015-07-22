# Notes on installing the co-simulation environment

- use the Enthought Canopy python distribution to make installation of numpy and scipy really easy - request an academic license
- install VisTrails (i use the github master branch and run it with `python vistrails/run.py`)
- check out the EnergyPlus version from GitHub: https://github.com/architecture-building-systems/EnergyPlus
- check out the design-performance-workflows to $HOME/.vistrails/userpackages (so VisTrails can find it)
  - you should see a subfolder called "design-performance-workflows" in your userpackages directory.
- dependencies should all be installable via `pip install`: eppy, lxml, parseidf (we should probably move this to eppy)
- (for DPV functionality: Install the DesignPerformanceViewer and Autodesk Revit Architecture 2014)
- (for EnergyPlusToFMU functionality: Install the EnergyPlusToFMU tool)

- open vistrails (you might need to install vtk with canopy to avoid some error messages on startup)
- Menu->Edit->Preferences, tab "Packages", enable the package "design-performance-workflows"

## TODO:

- sample workflow for simulation
- sample workflow for co-simulation

