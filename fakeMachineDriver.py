from fakeMachine import *
from driverBase import *

fakeHeatVariable = FakeMachineVariable("Heat", 25, 25, 0.9)
fakeHeatMeasurer = FakeMachineMeasurer(fakeHeatVariable)
fakeHeatEffector = FakeMachineEffector(fakeHeatVariable, 0.1)

machineHeatVariable = MachineVariable("Heat", "Temperature in machine", True, 100, 0, 25)
machineHeatMeasurer = MachineMeasurer("T1 Thermometer", "Thermometer in machine", 10, fakeHeatMeasurer.measureValue)
machineHeatEffector = MachineEffector("Heater", "Heater in machine", 10, fakeHeatEffector.setEffector, "Binary", None)

machineVariables = [machineHeatVariable]
machineMeasurers = [machineHeatMeasurer]
machineEffectors = [machineHeatEffector]
