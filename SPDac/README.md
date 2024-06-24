# SPDac

- [SPDac](#spdac)
  - [Version](#version)
  - [Driver Installation](#driver-installation)
      - [Windows：](#windows)
      - [Linux：](#linux)
  - [Connect](#connect)
  - [SCPI Commands](#scpi-commands)
  - [QCoDeS Functions](#qcodes-functions)

## Version
2024/06/22 First update
2024/06/24 Update FPGA serial chip driver

## Driver Installation

#### Windows：

1. 下载安装[Python](https://www.python.org/downloads/ "python 官网下载")
2. 双击安装目录下的CDM212364_Setup.exe，下一步直至安装完成
3. 双击SPDac_env_cfg.bat，等待命令执行完后按任意键退出完成QCoDeS Driver配置

#### Linux：

1. 使用包管理器安装Python
2. 执行SPDac_env_cfg.sh脚本完成QCoDeS Driver配置

> [!NOTE]
>
> 如果系统中安装过anaconda或使用conda管理不同的python环境的话，SPDac_env_cfg环境安装脚本默认将Python环境安装在base环境下。

## Connect
设备支持仪器通用可编程仪器标准指令(SCPI)，通过USB串口与设备进行连接，可以通过MATLAB、PyVISA等工具进行控制，如果需要直接使用串口工具控制，推荐使用[Tabby](https://github.com/Eugeny/tabby "一个十分好用的现代终端模拟器")。

> [!NOTE]
> 
> 随着设备连接的电脑不同，设备对应的端口号可能会发生改变，需要根据设备实际的端口号进行连接。

## SCPI Commands

------

- #### *IDN?

描述：ID请求命令，返回设备名、型号类型、设备序列码等

语法：*IDN?

参数：无

举例：

> *IDN?
> 
> `SPDev,SPDAC,SP-0001,BySirus_P-1.00`

注释：无

------

- #### SOURce:VOLTage:RANGe

描述：输出或读取每个电压输出通道的输出电压范围

语法：

SOURce[:VOLTage]:RANGe  [channel],{LOW|HIGH}

SOURce[:VOLTage]:RANGe? [channel]

| 参数  | 对应效果 |
| :---: | :------: |
|  LOW  |  正负5V  |
| HIGH  | 正负10V  |

举例：

> SOUR:RANG 1,LOW	- 设置1通道的输出电压范围为低范围（正负5V）

> SOUR:RANG? 1	       - 返回通道1的输出电压范围状态 
> 
> `"LOW"`

> [!NOTE]
>
> 如果正负5V的输出电压范围足够某次应用，请优先使用低电压测量范围。另外每当输出电压范围切换时，输出电压会有变为原来的2倍(LOW->HIGH)或者变为原来的1/2(HIGH->LOW)的情况。当某一次应用中需要更换测量量程时，推荐将所有的输出电压归零后再调整输出电压范围。此缺陷也许能在后续的硬件迭代中解决，软件能够消除输出电压的变化，但是无法消除范围切换时的电压跳变(假设LOW下输出电压为2V，实际电压变化为2V->1V->2V，电压还是会有突变)。

------

- #### SOURce:VOLTage:OUTPut

描述：改变或返回某一个通道输出电压的状态

语法：

SOURce[:VOLTage]:OUTPut [channel],{NORMal|CLAMped6k|TRIState}

SOURce[:VOLTage]:OUTPut? [channel]

|   参数    |        对应效果         |
| :-------: | :---------------------: |
|  NORMal   |      普通输出模式       |
| CLAMped6k | 输出通过6k电阻下拉至GND |
| TRIState  |       输出高阻态        |

举例：

> SOUR:OUTP 1,NORM	- 设置1通道正常输出电压

> SOUR:OUTP? 1		  - 返回通道1输出电压状态
> 
> `"NORMal"`

> [!NOTE]
> 
> 为保证待测设备的安全，所有通道在上电状态默认为clamped6k（输出6k电阻下拉到GND），需要输出电压前请执行此命令将输出电压状态更改为normal模式。

------

- #### SOURce:VOLTage:MODE

描述：改变或返回某一个通道的工作模式

语法：

SOURce[:VOLTage]:MODE [channel],{FIXed|SWEep|LIST}

SOURce[:VOLTage]:MODE? [channel]

| 参数  |   对应效果   |
| :---: | :----------: |
| FIXed | 固定输出电压 |
| SWEep |   电压扫描   |
| LIST  |   电压列表   |

举例：

> SOUR:MODE 1,FIX	- 设置1通道工作在固定输出电压模式

> SOUR:MODE? 1	    - 返回通道1输出电压模式
> 
> `"FIXed"`

> [!NOTE]
> 
> 目前单单只实现了FIXed模式，SWEep模式和LIST模式现在都没有用，所以这个command没啥用。

------

- #### SOURce:VOLTage:IMMediate

描述：改变或返回一个通道的固定输出电压（FIXed工作模式）

语法：

SOURce:VOLTage[:IMMediate] [channel],[numeric_value]

举例：

> SOUR:VOLT 1,1.114514	- 设置1通道输出电压1.114514V

> SOUR:VOLT? 1		      - 返回通道1当前设置的电压值
> 
> `1.114514`

> [!NOTE]
> 
> 因为numeric_value传入的参数为float类型传入参数，请不要传入有效位数超过8位的参数

------

- #### SOURce:VOLTage:LAST?

描述：返回一个通道上一次设定的输出电压

语法：

SOURce:VOLTage:LAST? [channel]

举例：

> SOUR:VOLT:LAST?
> 
> `1.114514`

> [!NOTE]
> 
> none

------

- #### MEASure:VOLTage:DC?

描述：返回ADC采样通道换算后的电压值

语法：

MEASure:VOLTage[:DC]? [channel]

举例：

> MEAS:VOLT? 1
> 
> `1`

> [!NOTE]
>
> 一块SPDac子板的ADC采样通道一共开放了4个，分别对应4个SMA插头，从靠近输出电压的通道为1开始往后分别为1、2、3、4通道，如果使用了两块SPDac子板，第二块（远离FPGA板USB口的子板为第二块）ADC采样通道数目从5开始顺延为5、6、7、8。通道1、2为直流采样通道，采样时间相对较长(100mS)，3、4通道设置为信号采样通道，采样时间较快(161uS)，直流精度相对较差。 

## QCoDeS Functions

------

- #### output_mode

描述：设置通道输出电压的范围以及输出模式

语法：

[device].ch[channel].output_mode(range, state)

| 参数  | 对应效果 |
| :---: | :------: |
|  LOW  |  正负5V  |
| HIGH  | 正负10V  |

|   参数    |        对应效果         |
| :-------: | :---------------------: |
|  NORMal   |      普通输出模式       |
| CLAMped6k | 输出通过6k电阻下拉至GND |
| TRIState  |       输出高阻态        |

举例：

> spdac.ch01.output_mode(range="low", state="normal")

> [!NOTE]
>
> 函数中range与state参数分别默认为low、high，也就是说调用函数spdac.ch01.output_mode(range="low", state="normal")与函数spdac.ch01.output_mode()是等效的。

- #### dc_constant_V

描述：设置通道输出电压值

语法：

[device].ch[channel].dc_constant_V(voltage)

举例：

> spdac.ch01.dc_constant_V(1.114514)

> [!NOTE]
>
> 请不要传入有效位数超过8位的参数，在传入电压参数时可以使用round(voltage, 6)进行小数点位数的限制

- #### ad_sample_V

描述：返回ADC通道采样值

语法：

[device].ch[channel].ad_sample_V()

举例：

> spdac.ch01.ad_sample_V()
>
> `1.114514`

> [!NOTE]
>
> none

- #### print_readable_snapshot

描述：打印通道的工作信息

语法：

[device].ch[channel].print_readable_snapshot(update=[boolean])

| update |         对应效果         |
| :----: | :----------------------: |
|   0    | 显示上次更新时获得的结果 |
|   1    |      更新结果并显示      |

举例：

> spdac.ch01.print_readable_snapshot(update=1)
> 
>     SPDAC_ch01:
>             parameter           value
>     --------------------------------------------------------------------------------
>     ad_sample_V          :  1.6503 (V)
>     dc_constant_V        :  0 (V)
>     dc_last_V            :  0 (V)
>     dc_mode              :  "FIXed"
>     dc_slew_rate_V_per_s :  None (V/s)
>     output_range         :  "LOW"
>     output_state         :  "NORMal"

> [!NOTE]
>
> 此函数在高速重复调用时会出现显示文字框位置变化的bug，目前为未解之谜，请不要高速循环调用此函数