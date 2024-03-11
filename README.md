# xuanwu-utils

适用于北京邮电大学-首都医科大学宣武医院脑科学相关合作项目的定制工具

![临床数据收集分阶段优化方案](images/临床数据收集分阶段优化方案.png)

## 主要内容

1. 支持博睿康、尼高力、国产NDRJ三种数据包的扫描GUI工具，用于筛选汇总需要收集的数据包
2. 支持将专有数据格式转换为EDF(+)公开格式的转换器，最好是跨平台的
3. 提供常用CRUD操作的TB级脑电时序数据库

## 配套软件

* 跨平台目录同步软件，需要支持哈希校验、断点续传、图形化界面，可选特性多路并行传输与传输加密

## 筛选工具使用说明

本工具在3.11+的CPython版本上进行了一些简单的手工测试

安装依赖库：

```shell
pip install Edflib-Python pillow av
```

修改Edflib-Python的源代码放宽文件合规要求以读取博睿康不规范的evt.bdf文件！

找到${PYTHON_HOME}\Lib\site-packages\EDFlib\edfreader.py下面几行：

```python
    if self.__datarecords < 1:
      return -13
```

替换为：

```python
    if self.__datarecords < 0:
      return -13
```

运行主程序

```shell
python scaneeg.py
```

可以使用--help了解更多使用方法

### 图形界面说明

![软件截图](images/软件截图.png)

* 文件 >> 导出结果 会弹出两个保存文件的窗口，前者用于保存扫描到所有信息使用JSON格式，后者用于保存选中的所有项路径列表使用普通文本格式
* “Name”列中括号内的数字表示该数据包的标注中有多少条目是*疑似发作条目*
* 双击“占用空间”列会用资源管理器打开该行对应数据包所在的文件夹
* 双击“视频预览”列会打开该行数据包对应的视频速览窗口，目前仅实现多进程加载缩略图功能
* 双击“详细信息”列会打开该行对应的完整扫描结果
* “占用空间”列如果有警告符号⚠，说明该行对应数据包存在已知损坏（检查项目很少，没有符号不代表一定没有损坏）
* “视频预览”列如果有可视符号👁，说明该行对应数据包检测到了视频序列，反之则没有

## 传输工具说明

### Rclone跨平台同步命令（使用非本地账户传输需要按照官网说明配置一下）

0. 建议 `rclone sync`或者 `rclone copy`之前先用 `rclone sync --dry-run -v source/ dest/`（注：此处不能带--checksum）或者类似 `FreeFileSync`之类的软件快速比对一下两边目录的内容差异
1. 建议的实际同步命令参数（可自行阅读文档修改）

```cmd
  %拷贝一个项目%
  .\rclone.exe copy source-path dest-path --checksum --progress --use-mmap --log-file=rclone.log --log-level DEBUG
  %拷贝多个项目%
  .\rclone.exe copy --files-from source-list-file dest-path --checksum --progress --use-mmap --log-file=rclone.log --log-level DEBUG  
  %更新目标路径过时的文件%
  .\rclone.exe sync source-path dest-path --checksum --progress --use-mmap --log-file=rclone.log --log-level DEBUG --interactive 
```

2. 拷贝本目录中的 `rclog2md5.py`至rclone安装目录，并运行以从日志中提取校验和 `MD5SUMS.txt`，检查一切正常后拷贝校验和文件至目标目录 `dest-path`

### FreeFileSync对比与同步工具

## 格式转换器说明

### NATUS转换器EdfExport.exe

解压edfexport.zip后请先检查是否已安装依赖项微软C++运行库2008 32位

【注意事项】当给本转换器指派路径参数时，相对路径要使用POSIX格式即正斜杠作为分隔符，绝对路径不受影响

## 后处理事项

1. 有些片段对应时间区段重复，应该选取未被裁剪的原始数据作为主要依据！
2. 有些发作被重复计数，需要手动整理时仔细甄别！
