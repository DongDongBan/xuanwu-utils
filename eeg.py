import os
import json
import warnings
from os.path import join, getsize
from datetime import datetime, timedelta
from typing import Dict, List
from enum import IntEnum

class SRC_TYPE(IntEnum): 
    NATUS = 0
    NEURACLE = 1
    NDRJ = 2
    NEUR_SUB = 3
    NDRJ_SUB = 4
    UNKNOWN = -1

# class OpenWithTimeout(): 
#     ...

# class ScandirWithTimeout(): 
#     ...

OpenWithTimeout = open; ScandirWithTimeout = os.scandir

__all__ = ['SRC_TYPE', 'scan_datadir', 'get_dsize', 'extract_attrs']

class NDRJTreeNode:
    def __init__(self, path):
        self.path = path
        self.children = []
        self.contains_seg = False

def scan_ndrj_patdir(patpath: str, pat_2_path: Dict) -> None: 

    def build_ndrjdb_tree(root_path: str, depth: int=0) -> NDRJTreeNode:
        if depth > 3:
            return None

        node = NDRJTreeNode(root_path)

        topdir = os.path.basename(root_path)
        ndrj_subdir_files = {
            f"{topdir}.eeg", 
            f"{topdir}.ng", 
            f"{topdir}-Seg1-CH1.mp4", 
            f"{topdir}-Seg1-CH1.ref", 
        }
        files_present = set()
        with ScandirWithTimeout(root_path) as entries:
            for entry in entries:
                if entry.is_file():
                    filename = entry.name
                    files_present.add(filename) 
                if entry.is_dir() and depth == 3: # 这是超离三界之外的新文件夹，不妨回到原点，开始全新扫描过程😀
                    scan_datadir(entry.path, pat_2_path)     
        if len(ndrj_subdir_files.intersection(files_present)) > 1: 
            node.contains_seg = len(ndrj_subdir_files.intersection(files_present)) / len(ndrj_subdir_files)

        if depth == 3:
            return node

        for entry in os.scandir(root_path):
            if entry.is_dir():
                child_node = build_ndrjdb_tree(entry.path, depth + 1)
                if child_node is not None:
                    if child_node.contains_seg: node.contains_seg = True
                    node.children.append(child_node)

        return node
    
    root_node = build_ndrjdb_tree(patpath)
    pat_key = os.path.basename(patpath)
    if pat_key not in pat_2_path: pat_2_path[pat_key] = []
    toplist = pat_2_path[pat_key] 

    def generate_info_from_tree(node: NDRJTreeNode, info_list: List) -> None: 
        if not node.contains_seg: scan_datadir(node.path, pat_2_path)
        else: 
            if len(node.children) == 0: 
                info_list.append({
                    "PATH": node.path, 
                    "TYPE": SRC_TYPE.NDRJ.name, 
                    "CONFIDENCE": node.contains_seg, 
                    "SHORTNAME": pat_key[:4] + ".." + pat_key[-4:] if len(pat_key) > 10 else pat_key, 
                })
            else: 
                childs_info_list = []
                info_list.append(childs_info_list)
                for child in node.children: 
                    generate_info_from_tree(child, childs_info_list)

    generate_info_from_tree(root_node, toplist)

ndrj_db_files = {'Eeg.cfg', 'patient.mdb', 'Report.mod'}
neuracle_files = {'datainfo.json', 'evt.bdf', 'ExamInfo.json', 'JsonVersion.json', 'RecordInfo.json', 'videoinfo.json'} 
neuracle_subdir_files = {'data.bdf', 'spike.bdf'}

def scan_datadir(toppath: str, pat_2_path: Dict[str, List[Dict]]) -> None:
    files_present = set()
    with ScandirWithTimeout(toppath) as entries:
        for entry in entries:
            if entry.is_file():
                filename = entry.name
                files_present.add(filename)  
    topdir = os.path.basename(toppath)  
    natus_files = {
        f"{topdir}.eeg", 
        f"{topdir}.ent", 
        f"{topdir}.epo", 
        f"{topdir}.erd", 
        f"{topdir}.etc", 
        f"{topdir}.snc", 
        f"{topdir}.stc", 
        f"{topdir}.vtc", 
        f"{topdir}.vt2", 
    }
    ndrj_subdir_files = {
        f"{topdir}.eeg", 
        f"{topdir}.ng", 
        f"{topdir}-Seg1-CH1.mp4", 
        f"{topdir}-Seg1-CH1.ref", 
    }    
    if len(natus_files.intersection(files_present)) > 1: 
        if (_loc := topdir.find('_')) != -1 and (_loc + 1 + 36) == len(topdir): 
                pat_key = topdir[:_loc]
        else:   pat_key = topdir

        video_lst = list(filter(lambda fn: fn.endswith(".avi"), files_present)); video_lst.sort()

        this_elem = {
            "PATH": toppath, 
            "TYPE": SRC_TYPE.NATUS.name, 
            "CONFIDENCE": len(natus_files.intersection(files_present)) / len(natus_files), 
            # "SHORTNAME": topdir[(topdir.find('_')+1):(topdir.find('_')+5)] + ".." + topdir[-4:], 
            "SHORTNAME": topdir[:4] + ".." + topdir[-4:] if len(topdir) > 10 else topdir, 
        }
        if len(video_lst) > 0: this_elem["video_lst"] = video_lst
        if pat_key in pat_2_path: pat_2_path[pat_key].append(this_elem)
        else: pat_2_path[pat_key] = [this_elem]

        with os.scandir(toppath) as entries: # 之前已经成功在有限时间内读取，此处可以用普通scandir
            for entry in entries:
                if entry.is_dir() and entry.name != "Decimated":
                    scan_datadir(entry.path, pat_2_path)                        
    
    elif len(neuracle_files.intersection(files_present)) > 1: 
        content = None # 患者名字和开始时间
        with OpenWithTimeout(join(toppath, "ExamInfo.json"), "rt") as f: 
            content = f.read()
        examinfo = dict(); this_elem = dict()
        try: 
            examinfo = json.loads(content)
        except Exception as err: 
            warnings.warn(f"解析{join(toppath, 'ExamInfo.json')}时出错，数据包可能已经损坏！")
            this_elem["BROKEN"] = True
        
        pat_key = examinfo["FullName"] if "FullName" in examinfo else topdir
        
        if "FullName" not in examinfo:  
            warnings.warn(f"{join(toppath, 'ExamInfo.json')}缺键，数据包可能已经损坏！")
            this_elem["BROKEN"] = True
        if "ExamTime" in examinfo: 
            # this_elem['记录时间'] = examinfo["ExamTime"] 
            this_elem['start_dt'] = datetime.fromisoformat(examinfo["ExamTime"])
        else: 
            warnings.warn(f"{join(toppath, 'ExamInfo.json')}缺键，数据包可能已经损坏！")
            this_elem["BROKEN"] = True

        this_elem.update({
            "PATH": toppath, 
            "TYPE": SRC_TYPE.NEURACLE.name, 
            "CONFIDENCE": len(neuracle_files.intersection(files_present)) / len(neuracle_files), 
            "SHORTNAME": topdir[:4] + ".." + topdir[-4:] if len(topdir) > 10 else topdir, 
        })
        
        if pat_key in pat_2_path: pat_2_path[pat_key].append(this_elem)
        else: pat_2_path[pat_key] = [this_elem]                
        
        # 扫描子文件夹并获取可能存在的视频路径列表
        
        with os.scandir(toppath) as entries: # 之前已经成功在有限时间内读取，此处可以用普通scandir
            for entry in entries:
                if entry.is_dir():
                    bdf_count = 0; video_lst = []; to_be_scaned_lst = []
                    with ScandirWithTimeout(entry.path) as subents: 
                        for sub_entry in subents:
                            if sub_entry.is_dir(): to_be_scaned_lst.append(sub_entry.path)
                            elif sub_entry.is_file(): 
                                if sub_entry.name in neuracle_subdir_files: bdf_count += 1
                                if sub_entry.name.endswith('avi'): video_lst.append(os.path.relpath(sub_entry.path, start=toppath))
                    if bdf_count == 0: scan_datadir(entry.path, pat_2_path) 
                    else: 
                        if bdf_count == 1: this_elem["BROKEN"] = True
                        if "video_lst" in this_elem: 
                            this_elem["video_lst"] += video_lst  
                        elif video_lst: 
                            this_elem["video_lst"] = video_lst
                        for unrecognized_subpath in to_be_scaned_lst:
                            scan_datadir(unrecognized_subpath, pat_2_path)
        if "video_lst" in this_elem: this_elem["video_lst"].sort()

    elif len(ndrj_db_files.intersection(files_present)) > 1: 
        with os.scandir(toppath) as entries: # 之前已经成功在有限时间内读取，此处可以用普通scandir
            for pat in entries:
                if pat.is_dir():
                    scan_ndrj_patdir(pat.path, pat_2_path)
    
    elif len(neuracle_subdir_files.intersection(files_present)) > 1: # 博睿康不完整数据包
        pat_key = topdir

        video_lst = list(filter(lambda fn: fn.endswith(".avi"), files_present)); video_lst.sort()

        this_elem = {
            "PATH": toppath, 
            "TYPE": SRC_TYPE.NEUR_SUB.name, 
            "CONFIDENCE": len(neuracle_subdir_files.intersection(files_present)) / len(natus_files), 
            "SHORTNAME": topdir[:4] + ".." + topdir[-4:] if len(topdir) > 10 else topdir, 
        }     
        if len(video_lst) > 0: this_elem["video_lst"] = video_lst
        if pat_key in pat_2_path: pat_2_path[pat_key].append(this_elem)
        else: pat_2_path[pat_key] = [this_elem]

        with os.scandir(toppath) as entries: # 之前已经成功在有限时间内读取，此处可以用普通scandir
            for entry in entries:
                if entry.is_dir():
                    scan_datadir(entry.path, pat_2_path)    
    
    elif len(ndrj_subdir_files.intersection(files_present)) > 1: 
        pat_key = topdir

        this_elem = {
            "PATH": toppath, 
            "TYPE": SRC_TYPE.NDRJ_SUB.name, 
            "CONFIDENCE": len(ndrj_subdir_files.intersection(files_present)) / len(natus_files), 
            "SHORTNAME": topdir[:4] + ".." + topdir[-4:] if len(topdir) > 10 else topdir, 
        }     

        if pat_key in pat_2_path: pat_2_path[pat_key].append(this_elem)
        else: pat_2_path[pat_key] = [this_elem]

        with os.scandir(toppath) as entries: # 之前已经成功在有限时间内读取，此处可以用普通scandir
            for entry in entries:
                if entry.is_dir():
                    scan_datadir(entry.path, pat_2_path)  
    
    else: 
        with os.scandir(toppath) as entries: # 之前已经成功在有限时间内读取，此处可以用普通scandir
            for entry in entries:
                if entry.is_dir():
                    scan_datadir(entry.path, pat_2_path)          

# 统计包含eeg的文件夹及其子文件夹占用空间的大小
# TODO 可能耗时且可能因为软硬件错误卡死，改为支持取消的异步编程或者多线程编程
def get_dsize(toppath: str) -> int:
    ans = 0
    for root, dirs, files in os.walk(toppath):
        for name in files:
            ans += getsize(join(root, name))
    return ans                

features = [
              b'"FirstName"', 
              b'"LastName"', 
              b'"MiddleName"', 
              b'"PatientGUID"', 
              b'"CreationTime"', 
              b'"StudyName"', 
              b'"StudyRecordTime"'
            ]

### [Deprecated] 使用标准格式更好！
# # extract_natus_attrs()会用到的辅助函数，日期格式转换
# def _get_ct_str(ctime: float) -> str:
#     td = timedelta(days=ctime)
#     dt = datetime(1899, 12, 30) + td
#     return '%4d年%2d月%2d日%2d时%2d分%2d秒' % (dt.year, dt.month, dt.day, 
#                                              dt.hour, dt.minute, dt.second)

# # extract_natus_attrs()会用到的辅助函数，时间格式转换
# def _get_srt_str(srtime: float) -> str:
#     srsec = round(srtime)
#     return '%2d时%2d分%2d秒' % (srsec // 3600, srsec % 3600 // 60, srsec % 60)

import re
# 从eeg文件的内容中提取出一个dict，包含患者姓名、记录时间、持续时间等信息
# 从ent文件种提取出所有现存标注
def extract_natus_attrs(dirpath: str) -> Dict:
    eegfile = join(dirpath, os.path.basename(dirpath)+".eeg")
    val = dict()

    content = None
    with OpenWithTimeout(eegfile, "rb") as f: 
        content = f.read()
    if content is None: 
        warnings.warn(f"无法读取EEG文件{eegfile}")
        val["BROKEN"] = True        
    else: 
        for name in features:
            if name.endswith(b'Time"'): # CreationTime, StudyRecordTime 的值是数值型
                pattern = re.compile(rb'\.' + name + rb'\s*,\s*([0-9\.]+)')
                match = pattern.search(content)
                if match:
                    val[name] = float(match.group(1))
                else: 
                    warnings.warn(f"无法从EEG文件{eegfile}中找到特征{name}")
                    val["BROKEN"] = True
            else: # 其他属性是字符串型，有引号包围
                pattern = re.compile(rb'\.' + name + rb'\s*,\s*"([^"]*)"')
                match = pattern.search(content)
                if match:
                    val[name] = match.group(1)
                else: 
                    warnings.warn(f"无法从EEG文件{eegfile}中找到特征{name}")  
                    val["BROKEN"] = True                                      

    # patient = str(val[b'"FirstName"'] + val[b'"MiddleName"'] + val[b'"LastName"'], 
    #               encoding='ascii'  )
    ret =   {
            #   '患者姓名': patient, 
            #   'PGUID': str(val[b'"PatientGUID"'], encoding='ascii'), 
            #   '记录时间': _get_ct_str(val[b'"CreationTime"']), 
            #   'CTime': val[b'"CreationTime"'], 
            #   '持续时间': _get_srt_str(val[b'"StudyRecordTime"']), 
            #   'SRTime': val[b'"StudyRecordTime"'],
              '记录名称': str(val[b'"StudyName"'], encoding='ascii') if b'"StudyName"' in val else '',
              **val
            }
    
    if b'"CreationTime"' in val: 
              ret['start_dt'] = datetime(1899, 12, 30) + timedelta(days=val[b'"CreationTime"']) 
    if b'"StudyRecordTime"' in val: 
              ret['timedelta'] = timedelta(seconds=val[b'"StudyRecordTime"'])     

    content = None # 提取注释信息
    entfile = eegfile[:-3]+"ent"
    with OpenWithTimeout(entfile, 'rb') as f:
        content = f.read()
    
    if content is not None: 
        pattern = rb'\(\."Stamp", ([0-9]*)\), \(\."Text", "([^"]*)"\), \(\."Type", "([^"]*)"\)' 
        # 例如这个(."Stamp", 2294), (."Text", "Montage:Cui_YiBing"), (."Type", "Annotation")
        matches = re.findall(pattern, content)

        if len(matches) > 0: ret["annotations"] = matches
    else: 
        warnings.warn(f"无法读取{entfile}")
        ret["BROKEN"] = True

    return ret

def extract_neuracle_attrs(dirpath: str) -> Dict: 
    ret = dict()
    content = None # 提取记录持续时间
    with OpenWithTimeout(join(dirpath, "datainfo.json"), "rt") as f: 
        content = f.read()
    datainfo = dict()
    try: 
        datainfo = json.loads(content)
    except Exception as err: 
        warnings.warn(f"解析{join(dirpath, 'datainfo.json')}时出错，数据包可能已经损坏！")
        ret["BROKEN"] = True
    
    if "duration" in datainfo: 
        ret['timedelta'] = timedelta(seconds=datainfo["duration"])
    else: 
        warnings.warn(f"{join(dirpath, 'datainfo.json')}缺键，数据包可能已经损坏！")
        ret["BROKEN"] = True
    
    try: 
        from pyedflib import EdfReader
    except ImportError: 
        warnings.warn(f"解析博睿康数据注释需要pyedflib，未能检测到改为使用备用方案")
        content = None # 提取注释
        with OpenWithTimeout(join(dirpath, "RecordInfo.json"), "rt") as f: 
            content = f.read()
        RecordInfo = dict()
        try: 
            RecordInfo = json.loads(content)
        except Exception as err: 
            warnings.warn(f"解析{join(dirpath, 'RecordInfo.json')}时出错，数据包可能已经损坏！")
            ret["BROKEN"] = True
        
        if "RecordEvents" in RecordInfo: 
            ret['annotations'] = RecordInfo["RecordEvents"]
        else: 
            warnings.warn(f"{join(dirpath, 'RecordInfo.json')}缺键，数据包可能已经损坏！")
            ret["BROKEN"] = True        
    else: 
        edf = EdfReader(join(dirpath, "evt.bdf"))

        # 获取注释信息
        annotations = edf.readAnnotations()
        annt_lst = []

        for i in range(len(annotations[0])):
            onset = annotations[0][i]
            duration = annotations[1][i]
            description = annotations[2][i]
            annt_lst.append(f"Onset: {onset}  Duration: {duration}  Description: {description}")

        # 关闭文件
        edf.close()   
        ret["annotations"] = annt_lst 

    return ret

def extract_ndrj_attrs(dirpath: str) -> Dict: 
    return dict()

def _default_extract_attrs(dirpath: str) -> Dict: 
    return dict()

extract_attrs = {
    SRC_TYPE.NATUS.name: extract_natus_attrs, 
    SRC_TYPE.NEURACLE.name: extract_neuracle_attrs, 
    SRC_TYPE.NDRJ.name: extract_ndrj_attrs, 
    SRC_TYPE.NEUR_SUB.name: _default_extract_attrs, 
    SRC_TYPE.NDRJ_SUB.name: _default_extract_attrs, 
    SRC_TYPE.UNKNOWN.name: _default_extract_attrs
}