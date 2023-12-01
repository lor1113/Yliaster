from fakeMachine import testMeasurer, testEffector


def pumpWater(x):
    print("Pumping water: " + str(x))


def setHeater(x):
    testEffector.setEffector(x)
    print("Setting heater: " + str(x))


def measureTemp():
    temperature = testMeasurer.measureValue()
    print(temperature)
    return temperature


deviceDrivers = {
    "heatMeasurer": measureTemp,
    "heatEffector": setHeater,
    "pumpControl": pumpWater
}
