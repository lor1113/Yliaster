import copy
import json

from fakeMachineDriver import deviceDrivers

machineConfigRules = {
    "requiredKeywords": ["name", "variables", "measurers", "effectors"],
    "optionalKeywords": ["description"],
}

variableConfigRules = {
    "requiredKeywords": ["name", "visible", "defaultTarget"],
    "optionalKeywords": ["description", "safeMax", "safeMin", "shutdownMin", "shutdownMax", "sensorMixing"],
}

measurerConfigRules = {
    "requiredKeywords": ["name", "variable", "driverKey", "remeasureMS", "active"],
    "optionalKeywords": ["description", "offsetMS"],
}

effectorConfigRules = {
    "requiredKeywords": ["name", "driverKey", "controlType", "shutdownSetting", "active"],
    "optionalKeywords": ["description", "controlVariable", "controlData", "readjustMS", "offsetMS"]
}

processConfigRules = {
    "requiredKeywords": ["name", "forMachine", "stages"],
    "optionalKeywords": ["description", "overrides"]
}

stageConfigRules = {
    "requiredKeywords": ["name", "stageControl"],
    "optionalKeywords": ["description", "overrides", "controlData", "variableTargets", "effectorSettings",
                         "recalculateTimers"]
}

bannedOverrideKeys = ["name", "description"]

configTypeRules = {
    "name": "str",
    "variables": "dict",
    "measurers": "dict",
    "effectors": "dict",
    "description": "str",
    "visible": "bool",
    "recalculateMS": "int",
    "defaultTarget": "int",
    "safeMax": "int",
    "safeMin": "int",
    "shutdownMin": "int",
    "shutdownMax": "int",
    "sensorMixing": "str",
    "driverKey": "str",
    "controlType": "str",
    "shutdownSetting": "int",
    "controlVariable": "str",
    "readjustMS": "int",
    "stageControl": "str",
    "overrides": "dict",
    "recalculateTimers": "bool",
    "active": "bool"
}

configEnumRules = {
    "sensorMixing": ["min", "max", "avg"],
    "controlType": ["static", "threshold", "PID", "binary", "binaryInverted"],
    "stageControl": ["target", "time", "shutdown"],
    "stageControlTargets": ["above", "below"]
}

controlTypeRequirements = {
    "static": {},
    "threshold": {"controlData": "dict", "controlVariable": "str"},
    "PID": {"controlData": "list", "controlVariable": "str"},
    "binary": {"controlData": "int", "controlVariable": "str"},
    "binaryInverted": {"controlData": "int", "controlVariable": "str"}
}


def applyOverride(config, override):
    for key, value in override.items():
        if key in bannedOverrideKeys:
            return False, "Invalid override keyword: " + key
        if key in config.keys():
            if type(value).__name__ == "dict":
                applyOverride(config[key], value)
            else:
                config[key] = value
    return True, ""


def validateConfig(config, configRules):
    keys = config.keys()
    for keyword in configRules["requiredKeywords"]:
        if keyword not in keys:
            return False, "Missing required keyword: " + keyword
    for keyword in keys:
        if keyword not in configRules["requiredKeywords"] and keyword not in configRules["optionalKeywords"]:
            return False, "Invalid keyword: " + keyword
        if keyword in configTypeRules.keys():
            if type(config[keyword]).__name__ != configTypeRules[keyword]:
                return False, "Invalid type for keyword: " + keyword + ". Expected: " + configTypeRules[
                    keyword] + " Received: " + type(config[keyword]).__name__
        if keyword in configEnumRules.keys():
            if config[keyword] not in configEnumRules[keyword]:
                return False, "Invalid value for keyword: " + keyword
    return True, ""


def validateMachineConfig(machineConfig, deviceDrivers):
    valid, message = validateConfig(machineConfig, machineConfigRules)
    if not valid:
        return False, message
    variableNames = []
    measurerVariables = []
    multipleMeasurers = []
    for variable in machineConfig["variables"].values():
        try:
            subMessage = str(variable["name"]) + ": "
        except KeyError:
            return False, "Variable missing name"
        except TypeError:
            return False, "Invalid variable name: " + str(variable["name"])
        valid, message = validateConfig(variable, variableConfigRules)
        if not valid:
            return False, subMessage + message
        if variable["name"] in variableNames:
            return False, subMessage + "Duplicate variable name: " + variable["name"]
        variableNames.append(variable["name"])
    measurerNames = []
    for measurer in machineConfig["measurers"].values():
        try:
            subMessage = str(measurer["name"]) + ": "
        except KeyError:
            return False, "Measurer missing name"
        except TypeError:
            return False, "Invalid measurer name: " + str(measurer["name"])
        valid, message = validateConfig(measurer, measurerConfigRules)
        if not valid:
            return False, subMessage + message
        if measurer["name"] in measurerNames:
            return False, subMessage + "Duplicate measurer name: " + measurer["name"]
        if measurer["variable"] not in variableNames:
            return False, subMessage + "Measurer variable not found: " + measurer["variable"]
        if measurer["driverKey"] not in deviceDrivers.keys():
            return False, subMessage + "Measurer driver not found: " + measurer["driverKey"]
        if measurer["variable"] in measurerVariables:
            multipleMeasurers.append(measurer["variable"])
        else:
            measurerVariables.append(measurer["variable"])
        measurerNames.append(measurer["name"])
    effectorNames = []
    for effector in machineConfig["effectors"].values():
        try:
            subMessage = str(effector["name"]) + ": "
        except KeyError:
            return False, "Effector missing name"
        except TypeError:
            return False, "Invalid effector name: " + str(effector["name"])
        valid, message = validateConfig(effector, effectorConfigRules)
        if not valid:
            return False, subMessage + message
        if effector["name"] in effectorNames:
            return False, subMessage + "Duplicate effector name: " + effector["name"]
        if effector["driverKey"] not in deviceDrivers.keys():
            return False, subMessage + "Effector driver not found: " + effector["driverKey"]
        for variable, variableType in controlTypeRequirements[effector["controlType"]].items():
            if variable not in effector.keys():
                return False, subMessage + "Effector missing required controlType variable: " + variable
            if type(effector[variable]).__name__ != variableType:
                return False, subMessage + "Effector controlType variable has invalid type: " + variable
        if effector["controlType"] == "PID":
            if len(effector["controlData"]) != 3:
                return False, subMessage + "Effector controlType PID requires 3 controlData values"
        if "controlVariable" in effector.keys():
            if effector["controlVariable"] not in variableNames:
                return False, subMessage + "Effector control variable not found: " + effector["controlVariable"]
        effectorNames.append(effector["name"])
    for variable in machineConfig["variables"].values():
        if variable["name"] in multipleMeasurers:
            if "sensorMixing" not in variable.keys():
                return False, "Variable with multiple measurers missing sensor mixing: " + variable["name"]
    lenTotalNames = len(variableNames + measurerNames + effectorNames)
    lenUniqueNames = len(set(variableNames + measurerNames + effectorNames))
    if lenTotalNames != lenUniqueNames:
        return False, "Duplicate name found"
    return True, ""


def validateFullConfig(machineConfig, processConfig, deviceDrivers):
    valid, message = validateMachineConfig(machineConfig, deviceDrivers)
    if not valid:
        return False, message
    valid, message = validateConfig(processConfig, processConfigRules)
    if not valid:
        return False, message
    if processConfig["forMachine"] != machineConfig["name"]:
        return False, "Process forMachine: " + processConfig["forMachine"] + " does not match machine name: " + \
                      machineConfig["name"]
    stageNames = []
    counter = 0
    machineVariableNames = machineConfig["variables"].keys()
    machineEffectorNames = machineConfig["effectors"].keys()
    for stage in processConfig["stages"].keys():
        if stage != str(counter):
            return False, "Invalid stage order at stage: " + str(stage)
        counter += 1
        stageData = processConfig["stages"][stage]
        try:
            subMessage = str(stageData["name"]) + ": "
        except KeyError:
            return False, "Stage missing name"
        except TypeError:
            return False, "Invalid stage name: " + str(stageData["name"])
        valid, message = validateConfig(stageData, stageConfigRules)
        if not valid:
            return False, subMessage + message
        if "variableTargets" in stageData.keys():
            for variable in stageData["variableTargets"].keys():
                if variable not in machineVariableNames:
                    return False, subMessage + "Variable " + variable + " not found"
        if "effectorSettings" in stageData.keys():
            for effector in stageData["effectorSettings"].keys():
                if effector not in machineEffectorNames:
                    return False, subMessage + "Effector " + effector + " not found"
        if stageData["stageControl"] == "target":
            if type(stageData["controlData"]).__name__ != "dict":
                return False, subMessage + "Invalid controlData type: " + type(stageData["controlData"]).__name__
            for key, value in stageData["controlData"].items():
                if key not in machineVariableNames:
                    return False, subMessage + "controlData variable " + key + " not found"
                if type(value).__name__ != "list":
                    return False, subMessage + "Invalid controlData value type, should be list: " + type(
                        value).__name__
                if len(value) != 2:
                    return False, subMessage + "Invalid controlData value length: " + str(len(value))
                if value[0] not in configEnumRules["stageControlTargets"]:
                    return False, subMessage + "Invalid controlData comparative value: " + value[0]
                if type(value[1]).__name__ != "int":
                    return False, subMessage + "Invalid controlData taret value type, should be int: " + type(
                        value[1]).__name__
        elif stageData["stageControl"] == "time":
            if type(stageData["controlData"]).__name__ != "int":
                return False, subMessage + "Invalid controlData type, should be int: " + type(
                    stageData["controlData"]).__name__
        if stageData["name"] in stageNames:
            return False, subMessage + "Duplicate stage name: " + stageData["name"]
        stageNames.append(stageData["name"])
    if "overrides" in processConfig.keys():
        machineProcessConfig = copy.deepcopy(machineConfig)
        valid, message = applyOverride(machineProcessConfig, processConfig["overrides"])
        if not valid:
            return False, "Process override invalid: " + message
        valid, message = validateMachineConfig(machineProcessConfig, deviceDrivers)
        if not valid:
            return False, "Process override invalid: " + message
    else:
        machineProcessConfig = machineConfig
    for stage, stageData in processConfig["stages"].items():
        if "overrides" in stageData.keys():
            machineStageConfig = copy.deepcopy(machineProcessConfig)
            valid, message = applyOverride(machineStageConfig, stageData["overrides"])
            if not valid:
                return False, "Stage " + stage + " override invalid: " + message
            valid, message = validateMachineConfig(machineStageConfig, deviceDrivers)
            if not valid:
                return False, "Stage " + stage + " override invalid: " + message
        else:
            machineStageConfig = machineProcessConfig
        valid, message = validateStage(machineStageConfig, stageData)
        if not valid:
            return False, "Stage " + stage + " invalid: " + message
    return True, ""


def validateStage(machineStageConfig, stageData):
    effectorVariables = {}
    for effector in machineStageConfig["effectors"].values():
        if "controlVariable" in effector.keys():
            if effector["controlVariable"] not in effectorVariables.keys():
                effectorVariables[effector["controlVariable"]] = []
            effectorVariables[effector["controlVariable"]].append(effector["name"])
    measurerVariables = []
    for measurer in machineStageConfig["measurers"].values():
        if measurer["variable"] not in measurerVariables:
            measurerVariables.append(measurer["variable"])
    for variable in effectorVariables.keys():
        if variable not in measurerVariables:
            return False, "Variable " + variable + " required by effector/s " + str(effectorVariables[
                                                                                        variable]) + " but has no input"
    if "effectorSettings" in stageData.keys():
        for effector in stageData["effectorSettings"].keys():
            if machineStageConfig["effectors"][effector]["controlType"] != "static":
                return False, "Atempting to set value for non-static effector: " + effector
    return True, ""


if __name__ == "__main__":
    fakeMachineConfig = json.loads(open("fakeMachineConfig.json").read())
    fakeProcessConfig = json.loads(open("fakeProcessConfig.json").read())
    print(validateFullConfig(fakeMachineConfig, fakeProcessConfig, deviceDrivers))
