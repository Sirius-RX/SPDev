import pyvisa

rm = pyvisa.ResourceManager()
rm.list_resources()

spsmu = rm.open_resource('ASRL/dev/ttyACM0::INSTR')

spsmu.baud_rate = 921600

print(spsmu.query("*IDN?"))

for channel in range(1, 16 + 1):
    spsmu.write("sour:mode %u,fi,mi,ua20" % channel)
    print(spsmu.query("sour:mode? %u" % channel))

for channel in range(1, 16 + 1):
    spsmu.write("sour:curr %u,%f" %(channel, channel))

for channel in range(1, 16 + 1):
    print(spsmu.query("meas:curr? %u" % channel))