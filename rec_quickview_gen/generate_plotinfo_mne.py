import mne
import argparse

parser = argparse.ArgumentParser(
    usage='%(prog)s ',
    description='这个脚本用来扫描筛选脑电记录信息',
)
parser.add_argument("--edf_dir",type=str)
parser.add_argument("--outpt_json",type=str,required=False) 
parser.add_argument("--output_html",type=str,required=False)
# parser.add_argument("--ignore_lst",type=str,nargs='?',required=False)

args = parser.parse_args()

import os
patient = os.path.basename(os.path.abspath(args.edf_dir))
if not getattr(args, "outpt_json", None): setattr(args, "outpt_json", f"{patient}-plotinfo.json")
if not getattr(args, "output_html", None): setattr(args, "output_html", f"{patient}-timeline.html")


class MNEEdfObjWrapper:
    def __init__(self, *args, **kwargs):
        self.raw = mne.io.read_raw_edf(*args, **kwargs)
    def __enter__(self):
        return self.raw
    def __exit__(self, *args):
        self.raw.close()
        
from typing import List
# TODO 添加对Offset注释的识别
def _is_possile_sz(s: str, kws: List[str] = ['sz', 'seiz', 'onset', '发作', '癫痫', '?', '？']): 
    s = s.lower()
    if any([ kw in s for kw in kws ]):  return True
    else:                               return False
    

# xuanwu_data_path = args.edf_dir/../
# plot_args_path = args.outpt_json # ; os.makedirs(plot_args_path, exist_ok=True)
ignore_lst = [] # args.ignore_lst

import os
import json, csv
import glob
from datetime import datetime, timedelta
import warnings
import argparse 

# with os.scandir(xuanwu_data_path) as entries:
#     for entry in entries:
result_obj = {"record_lst": [], "seizure_lst": [], "unused_rec_idx_lst": []}
record_fn_lst =  list(glob.iglob(os.path.join(args.edf_dir, "**", "*.edf"), recursive=True))
# record_fn_lst.extend(glob.iglob(os.path.join(args.edf_dir, "**", "*.EDF"), recursive=True))
record_fn_lst.extend(list(glob.iglob(os.path.join(args.edf_dir, "**", "*.bdf"), recursive=True)))
# record_fn_lst.extend(glob.iglob(os.path.join(args.edf_dir, "**", "*.BDF"), recursive=True))

last_ch_names = None
for edf_path in record_fn_lst:
    try:
        print(f"Try loading {edf_path}")
        # with EdfReaderWrapper(edf_path) as pedf:
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

        annotations = mne.read_annotations(edf_path)

        with MNEEdfObjWrapper(edf_path, preload=False) as raw:
            start_dt = raw.info['meas_date']
            end_dt = start_dt + timedelta(seconds=(raw.n_times / raw.info['sfreq'])) # TODO 核查对于EDF-D情形下此算法是否正确
            fs = raw.info['sfreq']

            # 构建病人信息字典，并添加到列表中
            result_obj["record_lst"].append({
                "file": os.path.basename(edf_path),
                "span": [start_dt, end_dt],
                "info": f"{os.path.basename(edf_path)} of shape {len(raw.ch_names), raw.n_times}", 
                "annotations": [(a['onset'], a['description']) for a in annotations] if len(annotations) else []
            })   
            
            # 检查跨文件通道一致性
            if last_ch_names is None: last_ch_names = raw.ch_names
            elif last_ch_names != raw.ch_names: 
                warnings.warn(f"相较于之前的通道排布发生变化！\n{edf_path}")
                last_ch_names = raw.ch_names

            # TODO 非精准匹配可能的发作标注
            for annt in annotations: 
                if _is_possile_sz(annt['description']): 
                    result_obj["seizure_lst"].append({
                        "span": [annt['orig_time'], annt['orig_time']+timedelta(seconds=annt['duration'])], 
                        "info": annt['description'] + f" Onset {annt['orig_time'].isoformat()}, last {annt['duration']}s"
                    })
                                                
    except ValueError as exp:
        warnings.warn(f"ValueError from {exp}")

result_obj["record_lst"].sort(key=lambda obj:obj["span"])
result_obj["seizure_lst"].sort(key=lambda obj:obj["span"])
for k, rec_info in enumerate(result_obj["record_lst"]):
    if rec_info["file"] in ignore_lst:
        result_obj["unused_rec_idx_lst"].append(k)
    rec_info["span"] = [rec_info["span"][0].isoformat(), rec_info["span"][1].isoformat()]

for seiz_info in result_obj["seizure_lst"]:
    seiz_info["span"] = [seiz_info["span"][0].isoformat(), seiz_info["span"][1].isoformat()]
    
# with open(os.path.join(plot_args_path, f'{entry.name}.json'), "wt") as fout:
with open(args.outpt_json, "wt") as fout:
    json.dump(result_obj, fout, indent=2)

with open(args.outpt_json, "rt") as f:
    result_obj = json.load(f)

for k, rec_info in enumerate(result_obj["record_lst"]):
    # if rec_info["file"] in ignore_lst:
    #     result_obj["unused_rec_idx_lst"].append(k)
    rec_info["span"] = [datetime.fromisoformat(rec_info["span"][0]), datetime.fromisoformat(rec_info["span"][1])]

for seiz_info in result_obj["seizure_lst"]:
    seiz_info["span"] = [datetime.fromisoformat(seiz_info["span"][0]), datetime.fromisoformat(seiz_info["span"][1])]
    
import plotly.offline as pyo
from timeline import get_pat_timeline
fig = get_pat_timeline(title=patient, record_seq=result_obj["record_lst"], seizure_seq=result_obj["seizure_lst"])

pyo.plot(fig, filename=args.output_html, # include_plotlyjs="./plotly.min.js", 
            auto_open=False, image='svg', image_width=2560, image_height=1440)
fig.show()
