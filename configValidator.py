import json
import copy

from fakeMachineDriver import fakeDeviceDrivers

machineConfigRules = {
    "requiredKeywords": ["name", "variables", "measurers", "effectors"],
    "optionalKeywords": ["description"],
}

variableConfigRules = {
    "requiredKeywords": ["name", "visible"],
    "optionalKeywords": ["description", "safeRange", "shutdownRange", "sensorMixing"],
}

measurerConfigRules = {
    "requiredKeywords": ["name", "variable", "driverKey", "iterateMS", "active"],
    "optionalKeywords": ["description", "offsetMS"],
}

effectorConfigRules = {
    "requiredKeywords": ["name", "driverKey", "controlType", "shutdownSetting", "active"],
    "optionalKeywords": ["description", "controlVariable", "controlBinaryThreshold", "controlLookupTable",
                         "controlPIDConsts", "minChangeDelayMS"]
}

processConfigRules = {
    "requiredKeywords": ["name", "forMachine", "stages"],
    "optionalKeywords": ["description", "overrides"]
}

stageConfigRules = {
    "requiredKeywords": ["name", "stageEndControl"],
    "optionalKeywords": ["description", "overrides", "variableTargets", "effectorSettings",
                         "recalculateTimers", "stageEndTimer", "stageEndTarget"]
}

bannedOverrideKeys = ["name", "description"]

configTypeRules = {
    "name": "str",
    "variables": "dict",
    "measurers": "dict",
    "effectors": "dict",
    "description": "str",
    "visible": "bool",
    "iterateMS": "int",
    "minChangeDelayMS": "int",
    "defaultTarget": "int",
    "safeRange": "list",
    "shutdownRange": "list",
    "sensorMixing": "str",
    "driverKey": "str",
    "controlType": "str",
    "shutdownSetting": "int",
    "controlVariable": "str",
    "stageEndControl": "str",
    "overrides": "dict",
    "recalculateTimers": "bool",
    "active": "bool",
    "controlBinaryThreshold": "int",
    "controlPIDConsts": "list",
    "controlLookupTable": "list",
    "stageEndTimer": "int",
    "stageEndTarget": "dict"
}

configEnumRules = {
    "sensorMixing": ["min", "max", "avg"],
    "controlType": ["static", "lookupMin", "lookupMax", "lookupClosest", "PID", "binary", "binaryInverted"],
    "stageEndControl": ["target", "time", "shutdown"]
}

variableValueRequirements = {
    "controlType": {
        "lookupMin": ["controlLookupTable", "controlVariable"],
        "lookupMax": ["controlLookupTable", "controlVariable"],
        "lookupClosest": ["controlLookupTable", "controlVariable"],
        "PID": ["controlPIDConsts", "controlVariable"],
        "binary": ["controlBinaryThreshold", "controlVariable"],
        "binaryInverted": ["controlBinaryThreshold", "controlVariable"]
    },
    "stageEndControl": {
        "target": ["stageEndTarget"],
        "time": ["stageEndTimer"]
    }
}

variableNames = []
measurerNames = []
effectorNames = []


class ValidationException(Exception):
    pass


def testSafeRange(test):
    if type(test).__name__ != "list":
        return False
    if len(test) != 2:
        return False
    if type(test[0]).__name__ != "int" or type(test[1]).__name__ != "int":
        return False
    if test[0] == test[1]:
        return False
    return True


def testPID(test):
    if type(test).__name__ != "list":
        return False
    if len(test) != 3:
        return False
    if type(test[0]).__name__ != "int" or type(test[1]).__name__ != "int" or type(test[2]).__name__ != "int":
        return False


def testLookupTable(test):
    if type(test).__name__ != "list":
        return False
    if len(test) == 0:
        return False
    for x in test:
        if type(x).__name__ != "list":
            return False
        if len(x) != 2:
            return False
        if type(x[0]).__name__ != "int":
            return False
    return True


def testStages(test):
    counter = 0
    keys = list(test.keys())
    while str(counter) in keys:
        keys.remove(str(counter))
        counter += 1
    if len(keys) != 0:
        return False
    return True


def testVariableTargets(test):
    if type(test).__name__ != "dict":
        return False
    for key, value in test.items():
        if key not in variableNames:
            return False
        if type(value).__name__ != "int":
            return False
    return True


def testEffectorSettings(test):
    if type(test).__name__ != "dict":
        return False
    for key, value in test.items():
        if key not in effectorNames:
            return False
        if type(value).__name__ != "int":
            return False
    return True


def testStageEndTarget(test):
    if type(test).__name__ != "dict":
        return False
    for key, value in test.items():
        if key not in variableNames:
            return False
        if type(value).__name__ != "list":
            return False
        if len(value) != 2:
            return False
        if value[0] not in ["above", "below"]:
            return False
        if type(value[1]).__name__ != "int":
            return False
    return True


variableTestFunctions = {
    "safeRange": testSafeRange,
    "shutdownRange": testSafeRange,
    "controlPIDConsts": testPID,
    "controlLookupTable": testLookupTable,
    "stages": testStages,
    "variableTargets": testVariableTargets,
    "effectorSettings": testEffectorSettings,
    "stageEndTarget": testStageEndTarget
}

variableTestFunctionFailMessages = {
    "safeRange": "Needs to be a list with two non equal integers",
    "shutdownRange": "Needs to be a list with two non equal integers",
    "controlPIDConsts": "Needs to be a list with three integers",
    "controlLookupTable": "Needs to be a list of tuples with each first tuple element being an integer.",
    "stages": "Stage keys must start from 0 and count up by one, with lower numbered stages going first.",
    "variableTargets": "Must be a dictionary where each key is a valid variable and each value is an integer",
    "effectorSettings": "Must be a dictionary where each key is a valid effector and each value is an integer",
    "stageEndTarget": "Must be a dictionary where each key is a valid variable and each value is a tuple where the "
                      "first value is one of 'above' and 'below' and the second value is an integer"
}


def validateSection(sectionKey, sectionData, sectionRules, message):
    requiredKeywords = copy.copy(sectionRules["requiredKeywords"])
    if "name" not in sectionData:
        raise ValidationException(message + sectionKey + " Lacks name variable")
    message = message + sectionData["name"] + ": "
    if sectionKey:
        if sectionKey != sectionData["name"]:
            raise ValidationException(message + sectionKey + " Name variable does not match JSON key")
    for keyword, keyValue in sectionData.items():
        keyValue = sectionData[keyword]
        if keyword not in sectionRules["requiredKeywords"] and keyword not in sectionRules["optionalKeywords"]:
            raise ValidationException(message + "Invalid keyword: " + keyword)
        if keyword in configTypeRules:
            if type(keyValue).__name__ != configTypeRules[keyword]:
                raise ValidationException(message + "Invalid type for keyword: " + str(keyword) + ". Expected: " +
                                          configTypeRules[keyword] + " Received: " + type(keyValue).__name__)
        if keyword in configEnumRules:
            if keyValue not in configEnumRules[keyword]:
                raise ValidationException(message + "Invalid value for keyword: " + keyword)
        if keyword in variableValueRequirements:
            if keyValue in variableValueRequirements[keyword]:
                requiredKeywords.extend(variableValueRequirements[keyword][keyValue])
        if keyword in variableTestFunctions:
            if not variableTestFunctions[keyword](keyValue):
                if keyword in variableTestFunctionFailMessages:
                    raise ValidationException(message + "Validation function failed for " + keyword + " " +
                                              variableTestFunctionFailMessages[keyword])
                else:
                    raise ValidationException(message + "Validation function failed for " + keyword)

    for keyword in requiredKeywords:
        if keyword not in sectionData:
            raise ValidationException(message + "Missing required keyword: " + keyword)
    return True


def validateMachineConfig(machineConfig, deviceDrivers, message):
    validateSection(False, machineConfig, machineConfigRules, message)
    for variableKey, variableData in machineConfig["variables"].items():
        validateSection(variableKey, variableData, variableConfigRules, message + "Variable: ")
    for measurerKey, measurerData in machineConfig["measurers"].items():
        validateSection(measurerKey, measurerData, measurerConfigRules, message + "Measurer: ")
    for effectorKey, effectorData in machineConfig["effectors"].items():
        validateSection(effectorKey, effectorData, effectorConfigRules, message + "Effector: ")
    effectorVariables = [x["controlVariable"] for x in machineConfig["effectors"].values() if "controlVariable" in x]
    for x in effectorVariables:
        if x not in machineConfig["variables"]:
            raise ValidationException(message + "Effector variable " + str(x) + " is not present.")
    measurerVariables = [x["variable"] for x in machineConfig["measurers"].values()]
    for x in measurerVariables:
        if x not in machineConfig["variables"]:
            raise ValidationException(message + "Measurer variable " + str(x) + " is not present.")
    driverKeys = [x["driverKey"] for x in machineConfig["measurers"].values()] + \
                 [x["driverKey"] for x in machineConfig["effectors"].values()]
    for x in driverKeys:
        if x not in deviceDrivers:
            raise ValidationException(message + "Driver " + str(x) + " is not present.")


def validateProcessConfig(processConfig, message):
    validateSection(False, processConfig, processConfigRules, message)
    for stage in processConfig["stages"].values():
        validateSection(False, stage, stageConfigRules, message)


def testName(segment, message):
    if "name" not in segment:
        raise ValidationException(message + "name variable is not present")
    if type(segment["name"]).__name__ != "str":
        raise ValidationException(message + "name variable " + str(segment["name"]) + " is not a string.")


def validateNamespace(machineConfig, processConfig):
    global variableNames
    global measurerNames
    global effectorNames
    testName(machineConfig, "Machine config: ")
    machineNamespace = [machineConfig["name"]]
    for variable in machineConfig["variables"].values():
        testName(variable, "Variable: ")
        if variable["name"] in machineNamespace:
            raise ValidationException("Namespace collision: Variable name " + variable["name"] + " already used.")
        machineNamespace.append(variable["name"])
        variableNames.append(variable["name"])
    for measurer in machineConfig["measurers"].values():
        testName(measurer, "Measurer: ")
        if measurer["name"] in machineNamespace:
            raise ValidationException("Namespace collision: Measurer name " + measurer["name"] + " already used.")
        machineNamespace.append(measurer["name"])
        measurerNames.append(measurer["name"])
    for effector in machineConfig["effectors"].values():
        testName(effector, "Effector: ")
        if effector["name"] in machineNamespace:
            raise ValidationException("Namespace collision: Effector name " + effector["name"] + " already used.")
        machineNamespace.append(effector["name"])
        effectorNames.append(effector["name"])
    testName(processConfig, "Process Config: ")
    processNamespace = [processConfig["name"]]
    for stage in processConfig["stages"].values():
        testName(stage, "Process Stage: ")
        if stage["name"] in processNamespace:
            raise ValidationException("Namespace collision: Stage name " + stage["name"] + " already used")
        processNamespace.append(stage["name"])
    if "forMachine" not in processConfig:
        raise ValidationException("Process config does not have forMachine")
    if type(processConfig["forMachine"]).__name__ != "str":
        raise ValidationException("Process config forMachine is not string")
    if processConfig["forMachine"] != machineConfig["name"]:
        raise ValidationException("Process config forMachine '" + processConfig["forMachine"] + "' and machine name '" +
                                  machineConfig["name"] + "' do not match.")


def applyOverrides(config, overrides, message):
    for key, value in overrides.items():
        if key in bannedOverrideKeys:
            raise ValidationException(message + "Invalid override keyword: " + key)
        if key in config:
            if type(value).__name__ == "dict":
                applyOverrides(config[key], value, message)
            else:
                config[key] = value
    return True, ""


def validateFullConfig(machineConfig, processConfig, deviceDrivers):
    testedBaseMachineConfig = False
    try:
        validateNamespace(machineConfig, processConfig)
        validateProcessConfig(processConfig, "Process Config: ")
        for stage in processConfig["stages"].values():
            if "overrides" in stage:
                if stage["overrides"]:
                    stageMachineConfig = copy.deepcopy(machineConfig)
                    applyOverrides(stageMachineConfig, stage["overrides"], stage["name"] + "override failure: ")
                    validateMachineConfig(stageMachineConfig, deviceDrivers, stage["name"] + "override: ")
                    continue
            if not testedBaseMachineConfig:
                validateMachineConfig(machineConfig, deviceDrivers, stage["name"] + "no overrides: ")
                testedBaseMachineConfig = True
    except ValidationException as e:
        return False, str(e)
    return True, ""


if __name__ == "__main__":
    fakeMachineConfig = json.loads(open("fakeMachineConfig.json").read())
    fakeProcessConfig = json.loads(open("fakeProcessConfig.json").read())
    print(validateFullConfig(fakeMachineConfig, fakeProcessConfig, fakeDeviceDrivers))
