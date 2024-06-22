import time
import numpy as np
from IPython.display import Image, display
from qcodes_contrib_drivers.drivers.SPDev import SPDAC
spdac = SPDAC.SPDac('SPDAC', address='ASRL/dev/ttyUSB1::INSTR')

spdac.ch04.output_mode()

# 创建一个从-8π到8π的电压数组，步长为0.001π
voltages = np.arange(-8 * np.pi, 8 * np.pi + 0.01, 0.01 * np.pi)
# 计算幅度为4V的正弦函数值
sin_voltages = np.sin(voltages)

# 使用for循环输出所有电压值
for voltage in sin_voltages:
    voltage = round(voltage, 5)
    print(f"Voltage: {voltage}V")
    spdac.ch04.dc_constant_V(voltage + 1)

