import os
import numpy as np
from edfreader import EDFreader

# 匹配命令行参数
import argparse

parser = argparse.ArgumentParser(
    usage='%(prog)s --edf-dir target [--outpt-json jsonpath] [--output-html htmlpath]',
    description='这个脚本用来扫描筛选脑电记录信息',
)
parser.add_argument("--edf-dir",type=str)
parser.add_argument("--outpt-json",type=str,required=False) 
parser.add_argument("--output-html",type=str,required=False)
parser.add_argument("--outpt-npmemmap",type=bool,required=False) 
parser.add_argument("--output-channel-figure",type=str,required=False)
# parser.add_argument("--ignore_lst",type=str,nargs='?',required=False)

args = parser.parse_args()
patient = os.path.basename(os.path.abspath(args.edf_dir))
if not getattr(args, "outpt_json", None): setattr(args, "outpt_json", f"{patient}-plotinfo.json")
if not getattr(args, "output_html", None): setattr(args, "output_html", f"{patient}-timeline.html")

# TODO 下面两个参数选型需要探讨
if not getattr(args, "outpt_npmemmap", None): 
    setattr(args, "outpt_npmemmap", False)
if not getattr(args, "output_channel_figure", None): 
    setattr(args, "output_channel_figure", f"{patient}-channel-figure.???")

# TODO 检查这个上下文管理器的正确性
class EdfReaderWrapper(EDFreader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        super().close()


# 扫描edf-dir中的所有类edf文件
import glob

record_fn_lst =  list(glob.iglob(os.path.join(args.edf_dir, "**", "*.edf"), recursive=True))
record_fn_lst.extend(list(glob.iglob(os.path.join(args.edf_dir, "**", "*.bdf"), recursive=True)))

# TODO 依据edf记录开始的时刻，对record_fn_lst进行排序
def get_start_datetime(fn: str):
    with EdfReaderWrapper(fn) as edf:
        ... # TODO 这里需要检查实现接口
        # return edf.getStartdatetime()
record_fn_lst.sort(key=get_start_datetime)

# TODO 比较任意相邻的两个edf的通道是否完全一致
... # 请实现并尝试可视化通道变化

from typing import List
def _is_possile_sz(s: str, kws: List[str] = ['sz', 'seiz', 'onset', '发作', '癫痫', '?', '？']): 
    s = s.lower()
    if any([ kw in s for kw in kws ]):  return True
    else:                               return False

def worker_func(edf_path: str, result_obj: dict): # 请将result_obj改为线程安全的结果队列
    print(f"Try loading {edf_path}")

    # TODO 请检查下列代码的正确性
    with EdfReaderWrapper(edf_path) as pedf:
        ...
    #     start_dt = pedf.getStartdatetime()
    #     end_dt = start_dt + timedelta(seconds=(edf_len := pedf.getFileDuration()))
    #     fs = pedf.getSampleFrequency(0)
    #     # assert all((FS := pedf.getSampleFrequencies()) == fs) # TODO 支持过滤非脑电数据通道
    #     result_obj["record_lst"].append({
    #         "file": os.path.basename(edf_path), 
    #         # "span": [start_dt.isoformat(), end_dt.isoformat()], 
    #         "span": [start_dt, end_dt], 
    #         "info": f"{os.path.basename(edf_path)} of shape {pedf.signals_in_file, pedf.getNSamples()[0]}"
    #     })

    # TODO 请实现这几个函数
    def parse_datarecords(edf_path: str): 
        if args.outpt_npmemmap: 
            parse_datarecords()
        read_annotations()

    annotations = parse_datarecords(edf_path)

    ### TODO 请对照mne的实现，检查edflib信息提取是否完整
    # with MNEEdfObjWrapper(edf_path, preload=False) as raw:
    #     start_dt = raw.info['meas_date']
    #     end_dt = start_dt + timedelta(seconds=(raw.n_times / raw.info['sfreq'])) # TODO 核查对于EDF-D情形下此算法是否正确
    #     fs = raw.info['sfreq']

    #     # 构建病人信息字典，并添加到列表中
    #     result_obj["record_lst"].append({
    #         "file": os.path.basename(edf_path),
    #         "span": [start_dt, end_dt],
    #         "info": f"{os.path.basename(edf_path)} of shape {len(raw.ch_names), raw.n_times}", 
    #         "annotations": [(a['onset'], a['description']) for a in annotations] if len(annotations) else []
    #     })   
        
    #     # 检查跨文件通道一致性
    #     if last_ch_names is None: last_ch_names = raw.ch_names
    #     elif last_ch_names != raw.ch_names: 
    #         warnings.warn(f"相较于之前的通道排布发生变化！\n{edf_path}")
    #         last_ch_names = raw.ch_names

    #     # TODO 非精准匹配可能的发作标注
    #     for annt in annotations: 
    #         if _is_possile_sz(annt['description']): 
    #             result_obj["seizure_lst"].append({
    #                 "span": [annt['orig_time'], annt['orig_time']+timedelta(seconds=annt['duration'])], 
    #                 "info": annt['description'] + f" Onset {annt['orig_time'].isoformat()}, last {annt['duration']}s"
    #             })

# for edf_path in record_fn_lst: worker_func(edf_path)

# TODO 使用任务队列和线程池分发任务
# 将下面用于接收结果的list()改为线程安全的queue
# result_obj = {"record_lst": [], "seizure_lst": [], "unused_rec_idx_lst": []}
# from concurrent.futures import ThreadPoolExecutor
# with ThreadPoolExecutor() as executor:
#     for edf_path in record_fn_lst: executor.submit(worker_func, edf_path, result_obj)

result_obj["seizure_lst"].sort(key=lambda obj:obj["span"])

# 保存元信息为json文件
import copy
import json
# for k, rec_info in enumerate(result_obj["record_lst"]):
#     if rec_info["file"] in args.ignore_lst:
#         result_obj["unused_rec_idx_lst"].append(k)
json_obj = copy.deepcopy(result_obj)
for rec_info in json_obj["record_lst"]:
    rec_info["span"] = [rec_info["span"][0].isoformat(), rec_info["span"][1].isoformat()]
for seiz_info in json_obj["seizure_lst"]:
    seiz_info["span"] = [seiz_info["span"][0].isoformat(), seiz_info["span"][1].isoformat()]
    
# with open(os.path.join(plot_args_path, f'{entry.name}.json'), "wt") as fout:
with open(args.outpt_json, "wt") as fout:
    json.dump(json_obj, fout, indent=2)

# 绘制Timeline
import plotly.offline as pyo
from timeline import get_pat_timeline
fig = get_pat_timeline(title=patient, record_seq=result_obj["record_lst"], seizure_seq=result_obj["seizure_lst"])

pyo.plot(fig, filename=args.output_html, # include_plotlyjs="./plotly.min.js", 
            auto_open=False, image='svg', image_width=2560, image_height=1440)
fig.show()

