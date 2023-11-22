class MachineVariable:
    def __init__(self, name, description, visible, safeMax, safeMin, default):
        self.name = name
        self.description = description
        self.visible = visible
        self.safeMax = safeMax
        self.safeMin = safeMin
        self.value = default


class MachineMeasurer:
    def __init__(self, name, description, loopTimeMS, measureFunction):
        self.name = name
        self.description = description
        self.loopTimeNS = loopTimeMS
        self.measureFunction = measureFunction

    def measureValue(self):
        return self.measureFunction()


class MachineEffector:
    def __init__(self, name, description, loopTimeMS, effectorFunction, controlType, contolData):
        self.name = name
        self.description = description
        self.loopTimeNS = loopTimeMS
        self.effectorFunction = effectorFunction
        self.controlType = controlType
        self.controlData = contolData

    def setEffector(self, value):
        self.effectorFunction(value)
