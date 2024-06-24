## 使用配置脚本进行安装

1. 前往python官网(https://www.python.org/downloads/)下载python
2. 双击文件目录中的SPDac_env_cfg.bat文件，等待出现按任意键退出即可完成配置，如果后续出现问题可能得手动进行配置，如果有相关问题请随时联系。电话:17320035702 QQ:1716194438

## 以下为手动安装教程，有待完善

1. 使用python自带的pip管理器安装需要的python包，在windows终端中输入以下命令，windows终端可以通过win+x i打开

```python
pip install qcodes qcodes_contrib_drivers pyvisa pyvisa-py pyusb libusb pyserial zeroconf
```

2. 将SPDac驱动拷贝至qcodes_contrib_drivers对应的目录中，SPDac驱动为文件夹中的SPDav文件夹，这一步可以手动完成，也可以执行对应的脚本来完成操作

> [!NOTE]
>
> qcodes_contrib_drivers对应的安装目录可以通过在windows终端中执行命令pip show qcodes_contrib_drivers发挥的location字段来获取