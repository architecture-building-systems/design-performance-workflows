'''
addidealloads.py

contains the code for the VisTrails module 'AddIdealLoadsAirSystem'.

goes through an eppy IDF object and adds an EnergyPlus IdealLoadsAirSystem
HVAC system to each zone.

This code is based on DPV code, some assumptions are made.
'''


def add_ideal_loads_air_system(idf, cooling_system=True,
                               air_changes_per_hour=0.7,
                               sensible_heat_recovery_effectiveness=0.2):
    _add_schedule_type_limits(idf)
    _add_schedules(idf)

    for zone in idf.idfobjects['ZONE']:
        _add_thermostatsetpoint_dualsetpoint(idf, cooling_system, zone)
        _add_zonecontrol_thermostat(idf, zone)
        _add_zonehvac_equipmentconnections(idf, zone)
        _add_zonehvac_equipmentlist(idf, zone)
        _add_designspecification_outdoorair(idf, zone, air_changes_per_hour)
        _add_zonehvac_idealloadsairsystem(
            idf, zone, sensible_heat_recovery_effectiveness)
    return idf


def _add_zonehvac_idealloadsairsystem(
        idf, zone, sensible_heat_recovery_effectiveness):
    obj = idf.newidfobject("ZONEHVAC:IDEALLOADSAIRSYSTEM")
    obj.Name = zone.Name + "ZoneHVAC:IdealLoadsAirSystem"
    obj.Availability_Schedule_Name = ""
    obj.Zone_Supply_Air_Node_Name = zone.Name + "_Supply_Inlet"
    obj.Zone_Exhaust_Air_Node_Name = ""
    obj.Maximum_Heating_Supply_Air_Temperature = "50"
    obj.Minimum_Cooling_Supply_Air_Temperature = "13"
    obj.Maximum_Heating_Supply_Air_Humidity_Ratio = "0.008"
    obj.Minimum_Cooling_Supply_Air_Humidity_Ratio = "0.009"
    obj.Heating_Limit = "NoLimit"
    obj.Maximum_Heating_Air_Flow_Rate = ""
    obj.Maximum_Sensible_Heating_Capacity = ""
    obj.Cooling_Limit = "NoLimit"
    obj.Maximum_Cooling_Air_Flow_Rate = ""
    obj.Maximum_Total_Cooling_Capacity = ""
    obj.Heating_Availability_Schedule_Name = ""
    obj.Cooling_Availability_Schedule_Name = ""
    obj.Dehumidification_Control_Type = "None"
    obj.Cooling_Sensible_Heat_Ratio = ".7"
    obj.Humidification_Control_Type = "None"
    obj.Design_Specification_Outdoor_Air_Object_Name = (
        zone.Name + "_DesignSpecification_OutdoorAir")
    obj.Outdoor_Air_Inlet_Node_Name = ""
    obj.Demand_Controlled_Ventilation_Type = "None"
    obj.Outdoor_Air_Economizer_Type = "NoEconomizer"
    obj.Heat_Recovery_Type = "Sensible"
    obj.Sensible_Heat_Recovery_Effectiveness = (
        sensible_heat_recovery_effectiveness)


def _add_designspecification_outdoorair(idf, zone,
                                        air_changes_per_hour):
    obj = idf.newidfobject("DESIGNSPECIFICATION:OUTDOORAIR")
    obj.Name = zone.Name + "_DesignSpecification_OutdoorAir"
    obj.Outdoor_Air_Method = "AirChanges/Hour"
    obj.Outdoor_Air_Flow_per_Person = ""
    obj.Outdoor_Air_Flow_per_Zone_Floor_Area = ""
    obj.Outdoor_Air_Flow_per_Zone = ""
    obj.Outdoor_Air_Flow_Air_Changes_per_Hour = air_changes_per_hour
    obj.Outdoor_Air_Flow_Rate_Fraction_Schedule_Name = (
        "VentilationSchedule")


def _add_zonehvac_equipmentlist(idf, zone):
    obj = idf.newidfobject("ZONEHVAC:EQUIPMENTLIST")
    obj.Name = zone.Name + "_Equipment"
    obj.Zone_Equipment_1_Object_Type = "ZoneHVAC:IdealLoadsAirSystem"
    obj.Zone_Equipment_1_Name = zone.Name + "ZoneHVAC:IdealLoadsAirSystem"
    obj.Zone_Equipment_1_Cooling_Sequence = "1"
    obj.Zone_Equipment_1_Heating_or_NoLoad_Sequence = "1"


def _add_zonehvac_equipmentconnections(idf, zone):
    obj = idf.newidfobject("ZONEHVAC:EQUIPMENTCONNECTIONS")
    obj.Zone_Name = zone.Name + ""
    obj.Zone_Conditioning_Equipment_List_Name = zone.Name + "_Equipment"
    obj.Zone_Air_Inlet_Node_or_NodeList_Name = zone.Name + "_Supply_Inlet"
    obj.Zone_Air_Exhaust_Node_or_NodeList_Name = ""
    obj.Zone_Air_Node_Name = zone.Name + "_Zone_Air_Node"
    obj.Zone_Return_Air_Node_Name = zone.Name + "_Return_Outlet"


def _add_zonecontrol_thermostat(idf, zone):
    obj = idf.newidfobject("ZONECONTROL:THERMOSTAT")
    obj.Name = zone.Name + "_Thermostat"
    obj.Zone_or_ZoneList_Name = zone.Name
    obj.Control_Type_Schedule_Name = "HVACTemplate_Always_4"
    obj.Control_1_Object_Type = "ThermostatSetpoint:DualSetpoint"
    obj.Control_1_Name = "Thermostat_" + zone.Name + "_Dual_SP_Control"


def _add_thermostatsetpoint_dualsetpoint(idf, cooling_system, zone):
    obj = idf.newidfobject("THERMOSTATSETPOINT:DUALSETPOINT")
    obj.Name = "Thermostat_" + zone.Name + "_Dual_SP_Control"
    obj.Heating_Setpoint_Temperature_Schedule_Name = (
        "HVACTemplate_Always_20")
    if cooling_system:
        obj.Cooling_Setpoint_Temperature_Schedule_Name = (
            "HVACTemplate_Always_26")
    else:
        obj.Cooling_Setpoint_Temperature_Schedule_Name = (
            "HVACTemplate_Always_100")


def _add_schedules(idf):
    obj = idf.newidfobject("SCHEDULE:COMPACT")
    obj.Name = "HVACTemplate_Always_20"
    obj.Schedule_Type_Limits_Name = "HVACTemplate_Any_Number"
    obj.Field_1 = "Through: 12/31"
    obj.Field_2 = "For: AllDays"
    obj.Field_3 = "Until: 24:00"
    obj.Field_4 = "20"

    obj = idf.newidfobject("SCHEDULE:COMPACT")
    obj.Name = "HVACTemplate_Always_100"
    obj.Schedule_Type_Limits_Name = "HVACTemplate_Any_Number"
    obj.Field_1 = "Through: 12/31"
    obj.Field_2 = "For: AllDays"
    obj.Field_3 = "Until: 24:00"
    obj.Field_4 = "100"

    obj = idf.newidfobject("SCHEDULE:COMPACT")
    obj.Name = "HVACTemplate_Always_26"
    obj.Schedule_Type_Limits_Name = "HVACTemplate_Any_Number"
    obj.Field_1 = "Through: 12/31"
    obj.Field_2 = "For: AllDays"
    obj.Field_3 = "Until: 24:00"
    obj.Field_4 = "26"

    obj = idf.newidfobject("SCHEDULE:COMPACT")
    obj.Name = "HVACTemplate_Always_4"
    obj.Schedule_Type_Limits_Name = "HVACTemplate_Any_Number"
    obj.Field_1 = "Through: 12/31"
    obj.Field_2 = "For: AllDays"
    obj.Field_3 = "Until: 24:00"
    obj.Field_4 = "4"


def _add_schedule_type_limits(idf):
    obj = idf.newidfobject('SCHEDULETYPELIMITS')
    obj.Name = 'HVACTemplate_Any_Number'
