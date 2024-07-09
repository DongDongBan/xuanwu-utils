*注意事项：本文件夹内的代码额外需要第三方库：mne, Edflib-Python, plotly*

请直接尝试运行generate_plotinfo_[edflib|mne].py

* 检查EDF文件合法性与连续性（组合使用pyedflib & mne）
* 据此生成plotinfo.json（推荐手动补充seizure_list信息，顺带检查标注时间是否合规，跨文件通道数目与排列顺序是否一致）
* 生成timeline.html与overview.svg并搭配MD5SUMS.txt上传至语雀文档

【可选】使用np.memmap存储超大edf中的data

@swz 待实现
