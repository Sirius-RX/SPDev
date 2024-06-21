# SPDac

[TOC]

## SCPI Commands

- #### *IDN?

​	描述：ID请求命令，返回设备名、型号类型、设备序列码等

​	语法：*IDN?

​	参数：无

​	举例：>*IDN?

​		   SPDev,SPDAC,SP-0001,BySirus_P-1.00

​	注释：无

- #### SOURce:VOLTage:RANGe

​	描述：输出或读取每个电压输出通道的输出电压范围

​	语法：SOURce[:VOLTage]:RANGe  [channel],{LOW|HIGH}

​		   SOURce[:VOLTage]:RANGe? [channel]

​	参数：LOW	 正负5V

​		   HIGH	正负10V

​	举例：>SOUR:RANG 1,LOW	- 设置1通道的输出电压范围为低范围（正负5V）

​		   >SOUR:RANG? 1	       - 返回通道1的输出电压范围状态

​		   "LOW"

​	注释：如果正负5V的输出电压范围足够某次应用，请优先使用低电压测量范围。另外每当输出电压范围切换时，输出电压会有变为原来的2倍(LOW->HIGH)或者变为原来的1/2(HIGH->LOW)的情况。当某一次应用中需要更换测量量程时，推荐将所有的输出电压归零后再调整输出电压范围。此缺陷也许能在后续的硬件迭代中解决，软件能够消除输出电压的变化，但是无法消除范围切换时的电压跳变(假设LOW下输出电压为2V，实际电压变化为2V->1V->2V，电压还是会有突变)。

- #### SOURce:VOLTage:OUTPut

​	描述：改变或返回某一个通道输出电压的状态

​	语法：SOURce[:VOLTage]:OUTPut [channel],{NORMal|CLAMped6k|TRIState}

​		   SOURce[:VOLTage]:OUTPut? [channel]

​	参数：NORMal		普通输出模式

​		   CLAMped6k	  输出通过6k电阻下拉至GND

​		   TRIState		输出高阻态

​	举例：>SOUR:OUTP 1,NORM	- 设置1通道正常输出电压

​		   >SOUR:OUTP? 1		  - 返回通道1输出电压状态

​		   "NORMal"

​	注释：为保证待测设备的安全，所有通道在上电状态默认为clamped6k（输出6k电阻下拉到GND），需要输出电压前请执行此命令将输出电压状态更改为normal模式。

- #### SOURce:VOLTage:MODE

  描述：改变或返回某一个通道的工作模式

  语法：SOURce[:VOLTage]:MODE [channel],{FIXed|SWEep|LIST}

  ​	   SOURce[:VOLTage]:MODE? [channel]

  参数：FIXed	   固定输出电压

  ​	   SWEep	电压扫描

  ​	   LIST	     电压列表

  举例：>SOUR:MODE 1,FIX	- 设置1通道工作在固定输出电压模式

  ​	   >SOUR:MODE? 1	    - 返回通道1输出电压模式

  ​	   "FIXed"

  注释：目前单单只实现了FIXed模式，SWEep模式和LIST模式现在都没有用，所以这个command没啥用。

- #### SOURce:VOLTage:IMMediate

​	描述：改变或返回一个通道的固定输出电压（FIXed工作模式）

​	语法：SOURce:VOLTage[:IMMediate] [channel],[numeric_value]

​	参数：无

​	举例：>SOUR:VOLT 1,1.114514	- 设置1通道输出电压1.114514V

​		   >SOUR:VOLT? 1		      - 返回通道1当前设置的电压值

​		   1.114514

​	注释：因为numeric_value传入的参数为float类型传入参数，请不要传入有效位数超过8位的参数

- #### SOURce:VOLTage:LAST?

​	描述：返回一个通道上一次设定的输出电压

​	语法：SOURce:VOLTage:LAST? [channel]

​	参数：无

​	举例：>SOUR:VOLT:LAST?

​		   1.114514

​	注释：无

- #### MEASure:VOLTage:DC?

​	描述：返回ADC采样通道换算后的电压值

​	语法：MEASure:VOLTage[:DC]? [channel]

​	参数：无

​	举例：>MEAS:VOLT? 1

​		   1

​	注释：一块SPDac子板的ADC采样通道一共开放了4个，分别对应4个SMA插头，从靠近输出电压的通道为1开始往后分别为1、2、3、4通道，如果使用了两块SPDac子板，第二块（远离FPGA板USB口的子板为第二块）ADC采样通道数目从5开始顺延为5、6、7、8。通道1、2为直流采样通道，采样时间相对较长(100mS)，3、4通道设置为信号采样通道，采样时间较快(161uS)，直流精度相对较差。

## QCoDeS Functions
