# SPSMU

- [SPSMU](#spsmu)
  - [Version](#version)
  - [Driver Installation](#driver-installation)
      - [Windows：](#windows)
  - [Connect](#connect)
  - [SCPI Commands](#scpi-commands)

## Version
2024/06/22 First update

2024/06/24 Update CH343 serial chip driver

## Driver Installation

#### Windows：

1. 双击安装目录下的CH343SER.EXE，下一步直至安装完成
2. 使用任意软件连接设备

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
> `SPDev,SPSMU,SP-0002,BySirus_P-1.00`

注释：无

------

- #### SOURce:VOLTage:RANGe

描述：设置或返回通道的工作模式

语法：

SOURce:MODE  [channel],{FV|FI|HiZV|HiZI|SINKI},{MI|MV|MTemp|HiZ},{UA5|UA20|UA200|MA2|MA50}

SOURce:MODE? [channel]

| 参数  |              对应效果              |
| :---: | :--------------------------------: |
|  FV   |              输出电压              |
|  FI   |              输出电流              |
| HiZV  | 输出高阻，能更快转换到输出电压模式 |
| HiZI  | 输出高阻，能更快转换到输出电流模式 |
| SINKI |            输入电流模式            |

| 参数  |    对应效果    |
| :---: | :------------: |
|  MI   |    测量电流    |
|  MV   |    测量电压    |
| MTemp |    测量温度    |
|  HiZ  | 测量引脚高阻抗 |

| 参数  |   对应效果    |
| :---: | :-----------: |
|  UA5  |  电流范围5uA  |
| UA20  | 电流范围20uA  |
| UA200 | 电流范围200uA |
|  MA2  |  电流范围2mA  |
| MA50  | 电流范围50mA  |

举例：

> SOUR:MODE 1,FV,MI,UA5	- 设置1通道工作模式为输出电压，测量输出电流，电流范围5uA

> SOUR:MODE? 1	       - 返回通道1的工作模式设定状态
> 
> `"FV","MI","UA5"`

> [!NOTE]
>
> 默认上电或复位后的输出模式为高阻输出，测量高阻，5uA测量范围。当通道模式切换时，如果输出模式以及电流范围不变化，输出会保持上一次的设定状态；当输出模式改变时，输出会自动归零；当工作在输出电压模式时，改变测量模式以及电流范围参数均会保持上一次的设定参数；当工作在输出电流模式时，仅当只改变测量模式时，输出保持为上次的设定状态，改变电流范围输出一样会归零。

- #### SOURce:VOLTage

描述：设定或返回通道输出电压

语法：

SOURce:VOLTage [channel],[numeric_value]

SOURce:VOLTage? [channel]

举例：

> SOUR:VOLT 1,1.114514	- 设置1通道输出电压1.114514V

> SOUR:VOLT? 1		      - 返回通道1当前设置的电压值
> 
> `1.114514`

> [!NOTE]
> 
> 因为numeric_value传入的参数为float类型传入参数，请不要传入有效位数超过8位的参数。这里的设定numeric_value参数的单位为V。

------

- #### SOURce:VOLTage:LAST

描述：返回通道上一次设定的输出电压

语法：SOURce:VOLTage:LAST? [channel]

举例：

> SOURce:VOLTage:LAST? 1
>
> `1.114514`

> [!NOTE]
> 
> none

------

- #### SOURce:CURRent

描述：设定或返回通道输出电流

语法：

SOURce:CURRent [channel],[numeric_value]

SOURce:CURRent? [channel]

举例：

> SOUR:CURR 1,1.114514	- 设置1通道输出电流1.114514uA

> SOUR:CURR? 1		      - 返回通道1当前设置的电流值
> 
> `1.114514`

> [!NOTE]
> 
> 因为numeric_value传入的参数为float类型传入参数，请不要传入有效位数超过8位的参数。这里的设定numeric_value参数的单位为uA。

------

- #### SOURce:CURRent:LAST

描述：返回通道上一次设定的输出电流

语法：SOURce:CURRent:LAST? [channel]

举例：

> SOURce:CURRent:LAST? 1
>
> `1.114514`

> [!NOTE]
> 
> none

------

- #### SOURce:CLAMp:CURRent

描述：设定通道的钳位电流

语法：

SOURce:CLAMp:CURRent [channel],[persentage]

举例：

> SOURce:CLAMp:CURRent 1,0.5

> [!NOTE]
> 
> 此命令可以用来保护SMU设备或者输出的待测设备，但是因为钳位后会导致输出能力下降，造成实际输出与设定不符合，在运用此命令时请多加注意。参数中第二个为百分比的小数形式，例如0.1、0.2。

------

- #### SOURce:CLAMp:VOLTage

描述：设定通道的钳位电压

语法：

SOURce:CLAMp:VOLTage [channel],[persentage]

举例：

> SOURce:CLAMp:VOLTage 1,0.5

> [!NOTE]
> 
> 此命令可以用来保护SMU设备或者输出的待测设备，但是因为钳位后会导致输出能力下降，造成实际输出与设定不符合，在运用此命令时请多加注意。参数中第二个为百分比的小数形式，例如0.1、0.2。

------

- #### MEASure:VOLTage

描述：返回通道的电压测量结果

语法：

MEASure:VOLTage? [channel]

举例：

> MEAS:VOLT? 1
>
> `1.114514`

> [!NOTE]
> 
> 返回参数的单位为V

------

- #### MEASure:CURRent

描述：返回通道的电流测量结果

语法：

MEASure:CURRent? [channel]

举例：

> MEAS:CURR? 1
>
> `1.114514`

> [!NOTE]
> 
> 返回参数的单位为uA

------
------

> [!WARNING]
>
> 以下列出的命令均有ADMIN前缀，为方便管理或调试的预留命令，请用户在使用前一定理解自己的设定会带来什么样的结果！

------
------

- #### ADMIN:AD5522:SYSOut:CTRL

描述：设定ad5522芯片通道与芯片系统输出相连接（PCB板中对应SMA接口）

语法：

ADMIN[:AD5522]:SYSOut:CTRL [chip_sel],[channel_pmu],{HiZ|SENSe|FORCe|ALL}

| 参数  |                   对应效果                   |
| :---: | :------------------------------------------: |
|  HiZ  |               芯片系统输出高阻               |
| SENSe |       芯片对应通道SENSe连接至系统SENSe       |
| FORCe |       芯片对应通道FORCe连接至系统FORCe       |
|  ALL  | 芯片对应通道SENSe&FORCe连接至系统SENSe&FORCe |

举例：

> ADMIN:SYSO:CTRL 1,2,FORC

> [!NOTE]
> 
> none
