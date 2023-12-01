import time


class FakeMachine:
    def __init__(self, name):
        self.name = name
        self.machineTime = time.time_ns()
        self.variables = []
        self.measurers = []
        self.effectors = []

    def addVariable(self, variable):
        variable.valueTime = self.machineTime
        self.variables.append(variable)

    def addMeasurer(self, measurer):
        self.measurers.append(measurer)

    def addEffector(self, effector):
        self.effectors.append(effector)


class FakeMachineVariable:
    def __init__(self, name, value, setPoint, drift):
        self.name = name
        self.value = value
        self.setPoint = setPoint
        self.drift = drift
        self.valueTime = time.time_ns()
        self.effectorDelta = 0

    def updateValue(self):
        timeDelta = time.time_ns() - self.valueTime
        timeDeltaSeconds = timeDelta / 1000000000
        newValue = self.value + (timeDeltaSeconds * self.effectorDelta)
        newSetPointDelta = self.setPoint - newValue
        driftDelta = 1 - (self.drift ** timeDeltaSeconds)
        newDriftDelta = newSetPointDelta * driftDelta
        self.value = round(newValue + newDriftDelta, 3)
        self.valueTime = time.time_ns()


class FakeMachineMeasurer:
    def __init__(self, variable):
        self.variable = variable

    def measureValue(self):
        self.variable.updateValue()
        return self.variable.value


class FakeMachineEffector:
    def __init__(self, variable, effectorDelta):
        self.variable = variable
        self.effectorDelta = effectorDelta
        self.enabled = False

    def setEffector(self, toggle):
        if toggle:
            if not self.enabled:
                self.enabled = True
                self.enableEffector()
        else:
            if self.enabled:
                self.enabled = False
                self.disableEffector()

    def enableEffector(self):
        self.variable.updateValue()
        self.variable.effectorDelta += self.effectorDelta

    def disableEffector(self):
        self.variable.updateValue()
        self.variable.effectorDelta -= self.effectorDelta


testMachine = FakeMachine("testMachine")
testVariable = FakeMachineVariable("Heat", 30, 25, 0.9)
testMachine.addVariable(testVariable)
testMeasurer = FakeMachineMeasurer(testVariable)
testMachine.addMeasurer(testMeasurer)
testEffector = FakeMachineEffector(testVariable, 100)
testMachine.addEffector(testEffector)
