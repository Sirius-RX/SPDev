import pyvisa

rm = pyvisa.ResourceManager()
rm.list_resources()

spsmu = rm.open_resource('ASRL/dev/ttyACM2::INSTR')

spsmu.baud_rate = 921600

print(spsmu.query("*IDN?"))

for channel in range(1, 16 + 1):
    spsmu.write("sour:mode %u,fv,mv,ua5" % channel)
    print(spsmu.query("sour:mode? %u" % channel))

for channel in range(1, 16 + 1):
    spsmu.write("sour:volt %u,%f" %(channel, 5))

for channel in range(1, 16 + 1):
    print("channel %u voltage val is " % channel)
    print(spsmu.query("meas:volt? %u" % channel))