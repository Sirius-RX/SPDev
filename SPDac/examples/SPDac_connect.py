import time
from IPython.display import Image, display
from qcodes_contrib_drivers.drivers.SPDev import SPDAC
spdac = SPDAC.SPDac('SPDAC', address='ASRL/dev/ttyUSB1::INSTR')
# 注意上面中address=后面的字段不同的电脑可能不一样，需要根据自己的电脑调整

def selftest(self) -> None:
    self.ch01.output_mode(range="high",state="clamped6k")
    time.sleep(0.1)  # 延迟100毫秒
    self.ch02.output_mode(range="high",state="clamped6k")
    time.sleep(0.1)  # 延迟100毫秒
    self.ch03.output_mode(range="high",state="clamped6k")
    time.sleep(0.1)  # 延迟100毫秒
    self.ch04.output_mode(range="high",state="clamped6k")
    time.sleep(0.1)  # 延迟100毫秒

    self.ch01.output_mode(range="low",state="clamped6k")
    time.sleep(0.1)  # 延迟100毫秒
    self.ch02.output_mode(range="low",state="clamped6k")
    time.sleep(0.1)  # 延迟100毫秒
    self.ch03.output_mode(range="low",state="clamped6k")
    time.sleep(0.1)  # 延迟100毫秒
    self.ch04.output_mode(range="low",state="clamped6k")
    time.sleep(0.1)  # 延迟100毫秒

selftest(spdac)

# spdac.ch0x.output_mode() function default value is range="low", state="normal"
# spdac.ch0x.output_mode() equal to spdac.ch0x.output_mode(range="low",state="normal")
spdac.ch01.output_mode(range="low",state="normal")
spdac.ch02.output_mode(range="low",state="normal")
spdac.ch03.output_mode(range="low",state="normal")
spdac.ch04.output_mode(range="low",state="normal")

# set volt value
spdac.ch01.dc_constant_V(1.114514)
spdac.ch02.dc_constant_V(1.114514)
spdac.ch03.dc_constant_V(1.114514)
spdac.ch04.dc_constant_V(1.114514)

# get adc sampling value
spdac.ch01.ad_sample_V()
spdac.ch02.ad_sample_V()
spdac.ch03.ad_sample_V()
spdac.ch04.ad_sample_V()