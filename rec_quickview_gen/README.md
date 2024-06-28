*注意事项：本文件夹内的代码额外需要第三方库：mne, pyedflib, plotly*

请直接尝试运行generate_plotinfo.ipynb

* 检查EDF文件合法性与连续性（组合使用pyedflib & mne）
* 据此生成plotinfo.json（推荐手动补充seizure_list信息，顺带检查标注时间是否合规，跨文件通道数目与排列顺序是否一致）
* 生成timeline.html与overview.svg并搭配MD5SUMS.txt上传至语雀文档

【可选】使用mmap给mne添加超大edf读取支持（测试版本）

下面以提取注释为例，修改${PYTHON_HOME}\Lib\site-packages\mne\io\edf\edf.py下面几行：

```python
        with open(annotations, "rb") as annot_file:
            triggers = re.findall(pat.encode(), annot_file.read())
            triggers = [tuple(map(lambda x: x.decode(encoding), t)) for t in triggers]
```

替换为：

```python
        import mmap
        with open(annotations, "rb") as annot_file:
            with mmap.mmap(annot_file.fileno(), length=0, access=mmap.ACCESS_READ) as mmapped_file:
                triggers = re.findall(pat.encode(), mmapped_file)
                triggers = [tuple(map(lambda x: x.decode(encoding), t)) for t in triggers]
```

【可选】使用np.memmap存储超大edf中的data

@swz 待实现
