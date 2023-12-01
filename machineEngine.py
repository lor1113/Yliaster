import time
import json
import queue
import copy

from fakeMachineDriver import deviceDrivers
from configValidator import validateFullConfig, applyOverride


class ProcessException(Exception):
    pass


def runMachineProcess(machineConfig, processConfig, deviceDrivers, queue):
    queue.put("START")
    try:
        valid, message = validateFullConfig(machineConfig, processConfig, deviceDrivers)
        if not valid:
            queue.put(["SHUTDOWN", "VALIDATION ERROR", message])
            return
        queue.put("VALIDATION OK")
        stageCounter = 0
        if "overrides" in processConfig:
            applyOverride(machineConfig, processConfig["overrides"])
        timers = {}
        variableData = {x: {"value": None, "measurers": []} for x in machineConfig["variables"].keys()}
        measurerData = {x: {"value": None} for x in machineConfig["measurers"].keys()}
        startTime = time.perf_counter_ns() // 1000000
        stepTime = startTime
        processData = {"startTime": startTime, "stepTime": stepTime, "timers": timers, "variableData": variableData,
                       "measurerData": measurerData}
        while str(stageCounter) in processConfig["stages"]:
            queue.put(["STAGE INIT", stageCounter])
            stageData = processConfig["stages"][str(stageCounter)]
            stageConfig = copy.deepcopy(machineConfig)
            if "overrides" in stageData:
                applyOverride(stageConfig, stageData["overrides"])
            if "variableTargets" in stageData:
                for variableName, variableTarget in stageData["variableTargets"].items():
                    variableData[variableName]["target"] = variableTarget
            processData = stageSetup(processData, stageConfig, stageData, deviceDrivers)
            stageEnd = False
            loopCounter = 0
            while not stageEnd:
                stageEnd, processData = processStep(processData, stageConfig, stageData, deviceDrivers)
                loopCounter += 1
                if loopCounter > 9:
                    raise ProcessException("Loop counter exceeded")
            stageCounter += 1
    except ProcessException as e:
        queue.put(["SHUTDOWN", "PROCESS ERROR", str(e)])
        return


def processStep(processData, stageConfig, stageData, deviceDrivers):
    timers = processData["timers"]
    variableData = processData["variableData"]
    measurerData = processData["measurerData"]
    nextTime = min(timers.keys())
    currentTime = time.perf_counter_ns() // 1000000
    if nextTime > currentTime:
        time.sleep((nextTime - currentTime) / 1000)
    nextStep = timers.pop(nextTime)
    measurersToProcess = []
    variablesToProcess = []
    effectorsToProcess = []
    endAfter = False
    for item in nextStep:
        if item[0] == "measurers":
            measurersToProcess.append(item[1])
        elif item[0] == "effectors":
            effectorsToProcess.append(item[1])
        elif item[0] == "end":
            endAfter = True
    for measurer in measurersToProcess:
        measurerData[measurer]["value"] = deviceDrivers[stageConfig["measurers"][measurer]["driverKey"]]()
        variablesToProcess.append(stageConfig["measurers"][measurer]["variable"])
        newMeasurerTime = nextTime + stageConfig["measurers"][measurer]["remeasureMS"]
        if newMeasurerTime not in timers:
            timers[newMeasurerTime] = []
        timers[newMeasurerTime].append(["measurers", measurer])
    variablesToProcess = list(set(variablesToProcess))
    for variable in variablesToProcess:
        variableValues = []
        for measurer in variableData[variable]["measurers"]:
            if measurerData[measurer]["value"] is not None:
                variableValues.append(measurerData[measurer]["value"])
        if len(variableValues) == 1:
            variableData[variable]["value"] = variableValues[0]
        else:
            if stageConfig["variables"][variable]["sensorMixing"] == "min":
                variableData[variable]["value"] = min(variableValues)
            elif stageConfig["variables"][variable]["sensorMixing"] == "max":
                variableData[variable]["value"] = max(variableValues)
            elif stageConfig["variables"][variable]["sensorMixing"] == "avg":
                variableData[variable]["value"] = sum(variableValues) / len(variableValues)
    for effector in effectorsToProcess:
        effectorData = stageConfig["effectors"][effector]
        effectorVariableValue = variableData[effectorData["controlVariable"]]["value"]
        effectorOut = 0
        if effectorData["controlType"] == "binary":
            if effectorVariableValue > effectorData["controlData"]:
                effectorOut = 1
            else:
                effectorOut = 0
        elif effectorData["controlType"] == "binaryInverted":
            if effectorVariableValue > effectorData["controlData"]:
                effectorOut = 0
            else:
                effectorOut = 1
        deviceDrivers[effectorData["driverKey"]](effectorOut)
        newEffectorTime = nextTime + effectorData["readjustMS"]
        if newEffectorTime not in timers:
            timers[newEffectorTime] = []
        timers[newEffectorTime].append(["effectors", effector])
    if stageData["stageControl"] == "target":
        targetPassed = True
        for variable, target in stageData["controlData"].items():
            variableValue = variableData[variable]["value"]
            if target[0] == "above":
                if variableValue < target[1]:
                    targetPassed = False
            elif target[0] == "below":
                if variableValue > target[1]:
                    targetPassed = False
        if targetPassed:
            endAfter = True
    return endAfter, processData


def stageSetup(processData, stageConfig, stageData, deviceDrivers):
    newTimers = {}
    processedMeasurers = []
    processedEffectors = []
    stepTime = processData["stepTime"]
    timers = processData["timers"]
    variableData = processData["variableData"]
    measurerData = processData["measurerData"]
    if "recalculateTimers" in stageData:
        if stageData["recalculateTimers"]:
            timers = {}
    for scheduledTime, scheduledEvents in timers.items():
        for scheduledEvent in scheduledEvents:
            if stageConfig[scheduledEvent[0]][scheduledEvent[1]]["active"]:
                if scheduledTime not in newTimers:
                    newTimers[scheduledTime] = []
                newTimers[scheduledTime].append(scheduledEvent)
                if scheduledEvent[0] == "measurers":
                    processedMeasurers.append(scheduledEvent[1])
                elif scheduledEvent[0] == "effectors":
                    processedEffectors.append(scheduledEvent[1])

    for measurerName, measurerData in stageConfig["measurers"].items():
        startingTime = stepTime
        if "offsetMS" in measurerData:
            startingTime += measurerData["offsetMS"]
        if measurerData["active"]:
            variableData[measurerData["variable"]]["measurers"].append(measurerName)
            if measurerName not in processedMeasurers:
                if startingTime not in newTimers:
                    newTimers[startingTime] = []
                newTimers[startingTime].append(["measurers", measurerName])
    for effectorName, effectorData in stageConfig["effectors"].items():
        startingTime = stepTime
        if "offsetMS" in effectorData:
            startingTime += effectorData["offsetMS"]
        if effectorData["controlType"] == "static":
            try:
                staticValue = stageData["effectorSettings"][effectorName]
            except KeyError:
                staticValue = effectorData["shutdownSetting"]
            deviceDrivers[effectorData["driverKey"]](staticValue)
        elif effectorData["active"]:
            if effectorName not in processedEffectors:
                if startingTime not in newTimers:
                    newTimers[startingTime] = []
                newTimers[startingTime].append(["effectors", effectorName])
        else:
            deviceDrivers[effectorData["driverKey"]](effectorData["shutdownSetting"])

    if stageData["stageControl"] == "time":
        stageEndTime = stepTime + stageData["controlData"]
        if stageEndTime not in newTimers:
            newTimers[stageEndTime] = []
        newTimers[stageEndTime].append(["end"])
    for variable in variableData.values():
        variable["measurers"] = list(set(variable["measurers"]))
    processData["timers"] = newTimers
    return processData


if __name__ == "__main__":
    fakeMachineConfig = json.loads(open("fakeMachineConfig.json").read())
    fakeProcessConfig = json.loads(open("fakeProcessConfig.json").read())
    newQueue = queue.SimpleQueue()
    runMachineProcess(fakeMachineConfig, fakeProcessConfig, deviceDrivers, newQueue)
    while not newQueue.empty():
        print(newQueue.get())
