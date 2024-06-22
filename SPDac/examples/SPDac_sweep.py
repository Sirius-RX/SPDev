import time
from IPython.display import Image, display
from qcodes_contrib_drivers.drivers.SPDev import SPDAC
spdac = SPDAC.SPDac('SPDAC', address='ASRL/dev/ttyUSB1::INSTR')

spdac.ch04.output_mode()

# 使用for循环和range函数来生成所需的电压值列表
for i in range(-1000, 1001):  # 从-1000到1000，包含结束值
    voltage = i / 1000  # 将索引值转换为电压值
    print(f"Current voltage: {voltage:.3f}V")
    spdac.ch04.dc_constant_V(voltage)
