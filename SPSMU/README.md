# SPSMU

- [SPSMU](#spsmu)
  - [Version](#version)
  - [Driver Installation](#driver-installation)
      - [Windows：](#windows)
      - [Linux：](#linux)
  - [Connect](#connect)
  - [Examples](#examples)
  - [Pin Out](#pin-out)
  - [IntLib](#intlib)
  - [SCPI Commands](#scpi-commands)
  - [Status Indicate](#status-indicate)
      - [RGB Light](#rgb-light)
      - [Beep](#beep)

## Version

2024/08/16 Update windows driver installation steps & clamp function description

2024/06/22 First update

2024/06/24 Update CH343 serial chip driver

2024/06/25 Update status indicate description

## Driver Installation

#### Windows：

1. 双击安装目录下的CH343SER.EXE，下一步直至安装完成
2. 安装[NI-VISA](https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html# "NI-VISA为使用以太网、GPIB、串口、USB和其他类型仪器的用户提供支持。")，如果不想通过登录NI帐号下载NI-VISA，也可以直接通过[点击此处](https://download.ni.com/support/nipkg/products/ni-v/ni-visa/24.5/offline/ni-visa_24.5.0_offline.iso "链接更新日期为2024.08.16，如果链接内容无法访问请联系sirius_rx@qq.com更新连接")直接下载
3. 使用任意软件连接设备

#### Linux：

- Linux系统一般自带CH343驱动，无需额外安装

## Connect
设备支持仪器通用可编程仪器标准指令(SCPI)，通过USB串口与设备进行连接，可以通过MATLAB、PyVISA等工具进行控制，如果需要直接使用串口工具控制，推荐使用[Tabby](https://github.com/Eugeny/tabby "一个十分好用的现代终端模拟器")。

Tabby连接串口的推荐设置如下图流程所示：

1. 进入设置后点击配置和连接后点击高级设置

![Tabby_setting](../assets/Tabby高级设置.png "Tabby 高级设置界面")

2. 点击串口(serial)进入子菜单设定

![Tabby_serial_default](../assets/Tabby串口设置.png "Tabby 串口设置界面")

3. 设置输入模式为逐行(Line by line)

![Tabby_serial_mode](../assets/Tabby串口逐行.png "Tabby 串口设置界面设置输入模式为逐行")

> [!NOTE]
> 
> 设备串口波特率921600。
> 
> 随着设备连接的电脑不同，设备对应的端口号可能会发生改变，需要根据设备实际的端口号进行连接。

## Examples

examples目录内为使用PyVISA连接并控制设备的例程，可以为编写Python脚本控制设备实现复杂测试流程的自动化提供参考。

## Pin Out

![Pin_Out_sch](../assets/Pin_Out_sch.png "HR2.54排母接口原理图PinOut")
![Pin_Out_pcb](../assets/Pin_Out_pcb.png "HR2.54排母接口PCB PinOut")

> [!NOTE]
> 
> SPSMU的HR2.54排母引脚定义为上图sch所示，注意排针连接时引脚定义需要将中间对称调换（因为排针排母的连接方式，排母在板边的内侧对应排针在板边的内侧）。

## IntLib

IntLib文件夹中的Chip_ISCLS_0613.IntLib为Altium Designer EDA软件的集成封装库，该封装库中包括了与SPSMU排母连接的排针的引脚定义。除此之外还包含了一些常用器件的封装。

使用只需要使用Altium Designer打开文件导入即可自动完成封装库的导入。

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

> [!NOTE]
>
> none

------

- #### SOURce:MODE

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

> SOUR:VOLT? 1 - 返回通道1当前设置的电压值
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

> SOUR:CURR 1,1.114514 - 设置1通道输出电流1.114514uA

> SOUR:CURR? 1 - 返回通道1当前设置的电流值
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

SOURce:CLAMp:CURRent [channel],[I_low_persentage],[I_high_persentage]

举例：

> SOURce:CLAMp:CURRent 1,-0.5,0.5 - 在fv模式下，设置输出电流范围为总范围的-0.5~0.5，如输出电流范围MA50，限制输出电流-25mA~25mA

> [!NOTE]
> 
> 此命令可以用来保护SMU设备或者输出的待测设备，但是因为钳位后会导致输出能力下降，可能会造成实际输出与设定不符合，在运用此命令时请多加注意。并且因为钳位未经过校准，会出现限制传入参数为0.5，但是实际作用参数等效为0.6。参数中第二、三个为百分比的小数形式，例如0.1、0.2。

------

- #### SOURce:CLAMp:VOLTage

描述：设定通道的钳位电压

语法：

SOURce:CLAMp:VOLTage [channel],[V_low_persentage],[V_high_persentage]

举例：

> SOURce:CLAMp:VOLTage 1,-0.5,0.5

> [!NOTE]
> 
> 此命令可以用来保护SMU设备或者输出的待测设备，但是因为钳位后会导致输出能力下降，可能会造成实际输出与设定不符合，在运用此命令时请多加注意。并且因为钳位未经过校准，会出现限制传入参数为0.5，但是实际作用参数等效为0.6。参数中第二、三个为百分比的小数形式，例如0.1、0.2。

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

描述：设定AD5522芯片通道与芯片系统输出相连接（PCB板中对应SMA接口）

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

## Status Indicate

#### RGB Light

|          效果          |                 对应工作状态                 |
| :--------------------: | :------------------------------------------: |
|          黄色          |                 系统初始化中                 |
|          青色          |         系统初始化完毕，等待指令输入         |
|         亮青色         |                Button按键按下                |
|          蓝色          |            系统空闲，等待指令输入            |
|          绿色          |         接受到指令，正在执行对应函数         |
| 红色分量存在，亮度较低 |                 SCPI指令出错                 |
| 红色分量存在，亮度较高 | 固件程序崩溃，出现此情况请反馈并附上操作过程 |

#### Beep

|  效果  |                 对应工作状态                 |
| :----: | :------------------------------------------: |
| 响一下 |                系统初始化完成                |
|  静默  |                 系统正常工作                 |
| 有点吵 |                 SCPI指令出错                 |
| 吵死人 | 固件程序崩溃，出现此情况请反馈并附上操作过程 |

> [!NOTE]
>
> 当RGB出现红色分量或蜂鸣器鸣响时，可以先尝试:
> 1. 按下PCB板上的Button按键
> 2. 通过串口传输SYSTem:ERRor? SCPI命令直至所有错误清除
> 
> 如果上述两种方法无法消除RGB红色分量和使得蜂鸣器静默，说明固件程序**发生崩溃**，请反馈此情况并附上造成错误前的操作。