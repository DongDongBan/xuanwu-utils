#!/usr/bin/python3
# @Author: DongDongBan
# @Version: 0.2.1
# @Description: 这个脚本用来扫描筛选脑电记录，工作流程：
#   1. 查找源目录dbpath下所有的数据包，并搜索同目录是否有脑电视频文件
#   2. 拼接脑电视频文件至缓存目录tempdir，并人工预览视频打标签
#   3. 输出筛选过后的数据包信息
# @Usage: scaneeg.py [--temp-path tempdir] [dbpath]
#   --temp-path 用于设置时频的临时加载目录，可以设置为内存盘从而提高运行速度
# temp-path默认值tempfile.gettempdir()

from eeg import scan_datadir, get_dsize, extract_attrs, SRC_TYPE
import os
import json
import tempfile
import argparse 
import warnings
from typing import Optional, Dict
from shutil import disk_usage

__author__ = 'github.com/DongDongBan'

def scan_sort(dbpath: str) -> Dict: 
    print('将在%s中搜索数据包……' % dbpath)
    pat_2_path = dict() # dict(SHORTNAME=(dbpath[:4]+".."+dbpath[-4:] if len(dbpath) > 10 else dbpath), children=[])
    scan_datadir(dbpath, pat_2_path)

    # import pprint    
    # pp = pprint.PrettyPrinter(indent=4, width=40, compact=False)
    # pp.pprint(pat_2_path)

    for pat, rec_lst in pat_2_path.items(): 
        print(f"扫描到患者{pat}包括{len(rec_lst)}个目录")
        for rec_info in rec_lst: 
            if not isinstance(rec_info, dict): continue
            # print(rec_info["PATH"])
            extract_attrs_func = extract_attrs[rec_info["TYPE"]]
            try: # extract_attrs_func 会去实际读取文件，凡是涉及到实际文件IO，都有可能已经损坏
                rec_info.update(extract_attrs_func(rec_info["PATH"]))
            except Exception as err: 
                warnings.warn(f"When Retrieving Metainfo of {rec_info['PATH']}, {err}")
                rec_info["BROKEN"] = True
            
        # 将有"start_dt"的Dict和没有"start_dt"的Dict分开
        has_start_dt = [d for d in rec_lst if "start_dt" in d]
        no_start_dt = [d for d in rec_lst if "start_dt" not in d]        
        # 对有"start_dt"的Dict按照"start_dt"对应的值排序
        has_start_dt_sorted = sorted(has_start_dt, key=lambda x: x["start_dt"])
        # 合并排序后的有"start_dt"的Dict和没有"start_dt"的Dict
        pat_2_path[pat] = has_start_dt_sorted + no_start_dt     

    return pat_2_path

import tkinter as tk
from tkinter import ttk

class CheckableTreeview(ttk.Treeview):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.checkboxes = {}
        self.bind('<ButtonRelease-1>', self.on_click)
        self.bind('<<TreeviewOpen>>', self.on_open)
        self.bind('<<TreeviewClose>>', self.on_close)

    def insert(self, parent, index, iid=None, **kwargs):
        iid = super().insert(parent, index, iid=iid, **kwargs)
        self.checkboxes[iid] = tk.IntVar(value=0)
        self.item(iid, tags=iid)
        return iid

    def on_click(self, event):
        region = self.identify("region", event.x, event.y)
        if region == "cell":
            rowid = self.identify_row(event.y)
            column = self.identify_column(event.x)
            if column == "#1":
                self.toggle_checkbox(rowid)
        return 'break'

    def toggle_checkbox(self, item):
        current_value = self.checkboxes[item].get()
        new_value = 2 if current_value != 2 else 0
        self.checkboxes[item].set(new_value)
        self.update_checkbox(item)
        self.update_parent(item)
        self.update_children(item, new_value)

    def update_parent(self, item):
        parent = self.parent(item)
        if parent:
            children = self.get_children(parent)
            selected = sum(self.checkboxes[child].get() for child in children)
            state = 2 if selected == (2*len(children)) else (1 if selected else 0)
            self.checkboxes[parent].set(state)
            self.update_checkbox(parent)
            self.update_parent(parent)
            
    def update_children(self, item, state):
        children = self.get_children(item)
        for child in children:
            self.checkboxes[child].set(state)
            self.update_checkbox(child)
            self.update_children(child, state)

    def update_checkbox(self, item):
        checkbox_value = self.checkboxes[item].get()
        if checkbox_value == 0:
            self.set(item, column='checked', value='☐')
        elif checkbox_value == 1:
            self.set(item, column='checked', value='◐')
        elif checkbox_value == 2:
            self.set(item, column='checked', value='☑')

    def on_open(self, event):
        item = self.focus()
        self.update_checkbox(item)

    def on_close(self, event):
        item = self.focus()
        self.update_checkbox(item)

from tkinter import filedialog
def _insert_treenode(tree: CheckableTreeview, root_node, info: Dict) -> None: 
    tree.iid_2_info = dict()
    for pat, rec_lst in info.items(): 
        pat_node = tree.insert(root_node, 'end', text=pat[:4]+".."+pat[-4:] if len(pat) > 10 else pat, 
                               values=('☐', '', '', '', '', '', ''))
        def _recursive_insert(parent, children): 
            for child in children: 
                if isinstance(child, list): 
                    new_pat = tree.insert(parent, 'end', text='', 
                               values=('☐', '', '', '', '', '', ''))
                    _recursive_insert(new_pat, child)
                else: 
                    assert isinstance(child, dict)
                    leaf_node = tree.insert(parent, 'end', text=child["SHORTNAME"] if "SHORTNAME" in child else '', 
                                             values=(
                                                '☐', 
                                                child["TYPE"] if "TYPE" in child else '', 
                                                child["start_dt"].isoformat() if "start_dt" in child else '', 
                                                child["timedelta"].isoformat() if "timedelta" in child else '', 
                                                '', 
                                                '👁' if "video_lst" in child else '', 
                                                str(child)
                                             ))
                    tree.iid_2_info[leaf_node] = child
    
    tree.update_checkbox(root_node)

def select_directory(filemenu, tree):
    # 打开选择目录对话框并返回选择的路径
    directory_path = filedialog.askdirectory()
    if directory_path:
        display_info = scan_sort(directory_path)
        root_node = tree.insert((directory_path[:4]+".."+directory_path[-4:] if len(directory_path) > 10 else directory_path), 
                                'end', text='Root Node', values=('☐', '', '', '', '', '', ''))
        _insert_treenode(tree, root_node, display_info)
        filemenu.entryconfig("导出结果", state="normal")
        filemenu.entryconfig("选择目录", state="disabled")
def save_file_as(tree):
    # 打开保存文件对话框并返回选择的文件路径
    json_path = filedialog.asksaveasfilename(
        defaultextension=".json", filetypes=[("JSON files", "*.json")]
    )

    # Helper function to recursively collect selected nodes
    def collect_selected(item):
        data = {}
        if tree.checkboxes[item].get() > 0:  # Node is selected or partially selected
            data['text'] = tree.item(item, 'text')
            data['children'] = [collect_selected(child) for child in tree.get_children(item)]
            data['children'] = [child for child in data['children'] if child]  # Remove empty dicts
        return data if data else None

    # Start the collection from the root node
    selected_data = [collect_selected(child) for child in tree.get_children('')]
    selected_data = [data for data in selected_data if data]  # Remove empty dicts

    # Save the collected data to a JSON file
    with open(json_path, 'w') as outfile:
        json.dump(selected_data, outfile, indent=4)

# def select_vtmp_dir(): 
#     ... # 建议检测到有任何视频预览窗口线程活动就不让设置，并用一个信息提示取代正常窗口    
#     ... # 先显示当前的缓存路径右边一个浏览按钮，下边一个确定一个取消
#     ... # 浏览按钮打开 filedialog.askdirectory() 选择新目录
#     _, _, free = disk_usage(tmppath)
#     if free <= 2 ** 31: 
#         warnings.warn(f"缓存目录{tmppath}所在磁盘剩余空间不足2GB，建议重新设置")
#     ... # 确定按钮回调需要回传更改属性，同时要检测并取消所有正在进行的加载工作
    


from details import JSONViewer
from vpreview import PreviewWindow
import subprocess
import sys

def open_directory(directory_path):
    # 使用操作系统命令来打开目录
    if os.name == 'nt':  # Windows系统
        os.startfile(directory_path)
    elif os.name == 'posix':  # Linux和macOS系统
        if sys.platform == 'darwin':  # macOS系统
            subprocess.Popen(['open', directory_path])
        else:  # Linux系统
            subprocess.Popen(['xdg-open', directory_path])
    else:
        warnings.warn(f"无法在当前操作系统{sys.platform}上打开文件管理器")

def on_double_click(event, tree):
    region = tree.identify("region", event.x, event.y)
    if region == "cell":
        column = tree.identify_column(event.x)
        if tree.heading(column)['text'] == "完整信息":
            item = tree.identify_row(event.y)
            item_data = {
                "name": tree.item(item, "text"),
                "data": {
                    "checked": tree.set(item, "checked"),
                    "begin_time": tree.set(item, "begin_time"),
                    "duration": tree.set(item, "duration"),
                    "space": tree.set(item, "space"),
                    # ... 添加其他需要展示的数据
                }
            }
            JSONViewer(item_data)

        elif tree.heading(column)['text'] == "视频速览":
            item = tree.identify_row(event.y)
            if tree.parent(item) != "":  # 确保是叶子节点
                video_preview = tree.set(item, column="preview")
                if video_preview:  # 确保单元格内容非空
                    video_path = tree.set(item, column="duration") + ".mp4"
                    PreviewWindow(video_path)
        
        elif tree.heading(column)['text'] == "Name": 
            item = tree.identify_row(event.y)
            open_directory(tree.get_info_by_item[item]["PATH"])
        
        elif tree.heading(column)['text'] == "占用空间": 
            ... # get_dsize() 非阻塞式更新

def show_main_window(dbpath: Optional[str], tmppath: str): 
    if not os.path.isdir(tmppath): 
        warnings.warn(f"{tmppath}不是一个目录！已经重新设置为默认值，可以进入 设置 更改")
        tmppath = tempfile.gettempdir()
    _, _, free = disk_usage(tmppath)
    if free <= 2 ** 31: 
        warnings.warn(f"缓存目录{tmppath}所在磁盘剩余空间不足2GB，建议重新设置")
    
    if dbpath is not None and not os.path.isdir(dbpath): 
            warnings.warn(f"{dbpath}不是一个目录！请重新选择")
            dbpath = None
    
    root = tk.Tk()
    root.title("Checkable Treeview")
    root.geometry("800x600")

    # Create the menu bar
    menu_bar = tk.Menu(root)
    root.config(menu=menu_bar)

    # Create the File menu
    file_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="文件", menu=file_menu)

    if dbpath is not None:         
        file_menu.add_command(label="选择目录", state="disabled", command=lambda: select_directory(file_menu, tree))
        file_menu.add_command(label="导出结果", command=lambda: save_file_as(tree)) 
    else: 
        file_menu.add_command(label="选择目录", command=lambda: select_directory(file_menu, tree))
        file_menu.add_command(label="导出结果", state="disabled", command=lambda: save_file_as(tree))        
    
    # 重设缓存需要检查的状态很多（因为缓存可能正在被别的线程使用），之后用比较熟悉的Qt或者Web写界面的时候再做
    # setting_menu = tk.Menu(menu_bar, tearoff=0)
    # menu_bar.add_cascade(label="设置", menu=file_menu)
    # setting_menu.add_command(label="缓存目录", command=select_vtmp_dir)

    # Create a frame for the treeview and scrollbars
    frame = tk.Frame(root)
    frame.pack(expand=True, fill=tk.BOTH)

    # Create the treeview
    tree = CheckableTreeview(frame, columns=('checked', 'manufacturer', 'begin_time', 'duration', 'space', 'preview', 'info'))
    tree.heading('#0', text='Name')
    tree.heading('checked', text=' ')
    tree.heading('manufacturer', text='制造商')
    tree.heading('begin_time', text='开始时间')
    tree.heading('duration', text='持续时间')
    tree.heading('space', text='占用空间')
    tree.heading('preview', text='视频速览')
    tree.heading('info', text='完整信息')

    # Set the column widths
    tree.column('#0', width=16*8)  # Assuming each character is approximately 8 pixels wide
    tree.column('checked', width=20)  # Slightly wider than the checkbox
    tree.column('manufacturer', width=10*8)
    tree.column('begin_time', width=16*8)
    tree.column('duration', width=7*16)  # 7 Chinese characters
    tree.column('space', width=8*8)
    tree.column('preview', width=100)  # Enough for two buttons
    tree.column('info', stretch=tk.YES)  # Use remaining space

    # 绑定双击事件到 'on_info_click' 函数，并传递 'tree' 参数
    tree.bind("<Double-1>", lambda event: on_double_click(event, tree))

    # Create vertical scrollbar
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    vsb.pack(side='right', fill='y')
    tree.configure(yscrollcommand=vsb.set)

    # Create horizontal scrollbar
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
    hsb.pack(side='bottom', fill='x')
    tree.configure(xscrollcommand=hsb.set)

    # Pack the treeview last so it fills the remaining space
    tree.pack(side='left', expand=True, fill=tk.BOTH)

    if dbpath is not None: 
        display_info = scan_sort(dbpath)
        root_node = tree.insert((dbpath[:4]+".."+dbpath[-4:] if len(dbpath) > 10 else dbpath), 
                                'end', text='Root Node', values=('☐', '', '', '', '', '', ''))
        _insert_treenode(tree, root_node, display_info)    

    root.mainloop()    

if __name__ == '__main__':
    # 运行所需环境检查与参数的合法性检查

    parser = argparse.ArgumentParser(
        usage='%(prog)s [--temp-path tempdir] [dbpath]',
        description='这个脚本用来扫描筛选脑电记录信息',
        epilog='''脚本工作流程：
          1. 查找源目录dbpath下所有的数据包，并搜索同目录是否有脑电视频文件
          2. 拼接脑电视频文件至缓存目录tempdir，并人工预览视频打标签
          3. 导出筛选过后的数据包信息''',
        formatter_class=argparse.RawDescriptionHelpFormatter,

    )
    parser.add_argument('dbpath', nargs='?', 
                        help='待扫描的目录')
    parser.add_argument('--temp-path', nargs=1, metavar="'tmpdir'", dest='tmpdir', 
                        help='用于设置视频的临时加载目录，可以设置为内存盘从而提高运行速度，temp-path默认值tempfile.gettempdir()')
    args = parser.parse_args()

    if args.tmpdir is None:
        args.tmpdir = tempfile.gettempdir()    
    
    show_main_window(args.dbpath, args.tmpdir)   
        