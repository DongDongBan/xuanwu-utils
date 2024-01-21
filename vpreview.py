import tkinter as tk
from tkinter import ttk
import threading
import os
import time
import sys
import subprocess
import multiprocessing
import numpy as np
from typing import List
from math import ceil, floor

import __main__
if "DEBUG_MODE" in dir(__main__): DEBUG_MODE = __main__.DEBUG_MODE
else:                             DEBUG_MODE = False

import warnings
try: 
    from PIL import Image, ImageTk
except ImportError:
    warnings.warn("加载缩略图需要使用pillow库，请安装后再尝试！")   
    tk.messagebox.showerror("加载缩略图需要使用pillow库，请安装后再使用此功能！")    

try: 
    import av
except ImportError: 
    warnings.warn("加载缩略图需要使用av库，请安装后再尝试！")   
    tk.messagebox.showerror("加载缩略图需要使用av库，请安装后再使用此功能！")

def _worker_func(datapath, vrelpath, outpath, sec_lst):
    os.makedirs(outpath, exist_ok=True)

    def replace_special_chars(input_str):
        special_chars = {'/': '／', '\\': '＼', ':': '：', '*': '＊', '?': '？', '"': '＂', '<': '＜', '>': '＞', '|': '｜'}
        output_str = input_str
        for char, replacement in special_chars.items():
            output_str = output_str.replace(char, replacement)
        return output_str
    out_prefix = replace_special_chars(vrelpath)
    
    container = av.open(os.path.join(datapath, vrelpath))
    for cur_sec in sec_lst: 
        if cur_sec == 0: continue # seek(0) 对于部分视频会报错，因为查找方向是Backward的，详见PyAv文档
        container.seek(round(cur_sec * av.time_base))
        frame = next(container.decode(video=0))
        frame_rgb = frame.to_rgb().to_ndarray()

        # 将帧保存为图片
        img = Image.fromarray(frame_rgb)
        
        img.save(os.path.join(outpath, f'{out_prefix}_{cur_sec}.png')) 
    return img if 'img' in locals() else None

def float_range(start, stop, step):
    while start < stop:
        yield start
        start += step

class ThumbnailLoader(threading.Thread):
    def __init__(self, data_path: str, video_lst: List[str], interval: float, outpath, text4out, canvas, watch_dog, batch_size=32, *args, **kwargs): 
        super().__init__(*args, **kwargs)
        # 视频文件大小与基本格式检查在此处
        self.data_path = data_path
        self.video_lst = video_lst
        self.outpath = outpath
        self.frame_interval = interval
        self.outtext_widget = text4out
        self.canvas = canvas
        self.watch_dog = watch_dog
        self.batch_size = batch_size
        self.daemon = True  # 设置为守护线程，以便主程序退出时线程也会退出

    def run(self):     
        frame_interval, batch_size = self.frame_interval, self.batch_size  
        os.makedirs(self.outpath, exist_ok=True)

        start_time = time.time() 

        with multiprocessing.Pool() as pool: 
            async_results = []
            for vpath in self.video_lst: 
                container = av.open(os.path.join(self.data_path, vpath))
                stream = next(s for s in container.streams if s.type == 'video')
                len_in_sec = container.duration / av.time_base

                for batch_start_sec in float_range(0, len_in_sec, frame_interval*batch_size):
                    if not self.watch_dog.is_set(): # 任务被取消
                        pool.terminate(); pool.join()
                        return     
                            
                    batch_end_sec =  min(len_in_sec, batch_start_sec + frame_interval*batch_size)
                    batch_times = tuple(float_range(batch_start_sec, batch_end_sec, frame_interval))
                    # pool.apply_async(_worker_func, (os.path.dirname(vpath), os.path.basename(vpath), 'temp_frames', batch_times))
                    async_result = pool.apply_async(_worker_func, (self.data_path, vpath, self.outpath, batch_times))
                    async_results.append(async_result)

            pool.close()
            ntasks = len(async_results); step = ceil(ntasks/100); k_in_mem = ntasks // step # floor(ntasks/step)
            self.canvas.imgarr = np.empty(shape=(k_in_mem, ), dtype='object')
            self.canvas.num_img = k_in_mem
            for k, async_result in enumerate(async_results):
                if not self.watch_dog.is_set(): # 任务被取消
                    pool.terminate(); pool.join()
                    return
                try: 
                    img = async_result.get()
                except Exception as err: 
                    warnings.warn(f"处理第{k}个任务时发生错误{err}")
                else: 
                    if img is not None: 
                        self.update_canvas(img)
                        if k % step == 0: self.canvas.imgarr[k//step] = img
                    self.outtext_widget.insert("end", f"{k*100 / ntasks:.2f}%\n")
            pool.join()
        self.outtext_widget.insert("end", f"{time.time() - start_time:.2f}秒")
        self.outtext_widget.see("end")

    def update_canvas(self, img):
        # 在线程中更新画布
        self.canvas.after(0, self._update_canvas, img)

    def _update_canvas(self, img):
        # 清除画布
        self.canvas.delete("all")

        # 获取画布的当前大小
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # 调整图像大小以填充画布，使用 NEAREST 方法以提高速度
        pil_image_resized = img.resize((canvas_width, canvas_height), Image.Resampling.NEAREST)

        # # 调整图像大小以填充画布
        # pil_image_resized = pil_image.resize((canvas_width, canvas_height), Image.LANCZOS)    

        # 创建 ImageTk.PhotoImage 对象并在画布上显示
        photo = ImageTk.PhotoImage(pil_image_resized)
        self.canvas.create_image(0, 0, anchor='nw', image=photo)
        
        # 保存引用以防止被垃圾回收
        self.canvas.image = photo


class VideoLoader(threading.Thread): 
    def __init__(self, vdir_path, vlist, outpath, canvas, watch_dog, *args, **kwargs): 
        super().__init__(*args, **kwargs)
        ...
        self.daemon = True 
    def run(self): 
        ...

class PreviewWindow(tk.Toplevel):
    def __init__(self, short_name: str, data_path: str, video_lst: List[str], temp_path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(f"{short_name}({len(video_lst)})")
        self.geometry("600x400")

        self.short_name = short_name
        self.data_path = data_path
        self.video_lst = video_lst
        self.temp_path = temp_path

        # 第一排控件
        self.label_per = tk.Label(self, text="每")
        self.label_per.grid(row=0, column=0, sticky="nsew")

        self.var = tk.DoubleVar(self, value=5.00)
        self.var.trace_add('write', self.validate_input)    
        self.frame_interval = 5    

        self.spinbox = tk.Spinbox(self, from_=0.04, to=400.00, increment=1, format="%.2f", textvariable=self.var)
        self.spinbox.grid(row=0, column=1, sticky="nsew")

        self.label_sec = tk.Label(self, text="秒")
        self.label_sec.grid(row=0, column=2, sticky="nsew")

        self.thumbnail_button = ttk.Button(self, text="缩略图加载", command=self.load_thumbnail)
        self.thumbnail_button.grid(row=0, column=3, sticky="nsew")

        self.thumbnail_progress_text = tk.Text(self, height=1, width=24)
        self.thumbnail_progress_text.grid(row=0, column=4, sticky="nsew")

        self.video_button = ttk.Button(self, text="视频加载", command=self.load_video, state="disabled") # 这个功能可能之后会移除，目前实现优先级也不高
        self.video_button.grid(row=0, column=5, sticky="nsew")

        self.video_progress_text = tk.Text(self, height=1, width=24)
        self.video_progress_text.grid(row=0, column=6, sticky="nsew")

        # 配置列的权重，使其能够均匀分配宽度
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=2)
        self.grid_columnconfigure(4, weight=10)
        self.grid_columnconfigure(5, weight=2)
        self.grid_columnconfigure(6, weight=10)

        # 分割线
        self.separator1 = ttk.Separator(self, orient='horizontal')
        self.separator1.grid(row=1, column=0, columnspan=7, sticky="ew", pady=5)

        # 第二排控件 - 画布
        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.grid(row=2, column=0, columnspan=7, sticky="nsew", padx=5, pady=5)

        # 配置行的权重，使画布能够随窗口大小变化
        self.grid_rowconfigure(2, weight=1)

        # 第三排控件 - 分割线
        self.separator2 = ttk.Separator(self, orient='horizontal')
        self.separator2.grid(row=3, column=0, columnspan=7, sticky="ew", pady=5)

        # 第四排控件 - 滑动条
        self.slider = ttk.Scale(self, orient='horizontal', length=400, state='disabled')
        self.slider.grid(row=4, column=0, columnspan=7, sticky="ew", padx=5)

        # 为了使滑动条看起来更像播放器进度条，我们可以自定义它的样式
        style = ttk.Style(self)
        style.theme_use('clam')  # 使用 'clam' 主题作为基础，因为它允许更多自定义
        style.configure("Custom.Horizontal.TScale", troughcolor="#4D4D4D", sliderlength=20, sliderrelief='flat')
        self.slider.configure(style="Custom.Horizontal.TScale")

        # 绑定窗口大小变化事件，以便更新画布大小
        self.bind("<Configure>", self.on_resize)

        # 用于控制加载线程的事件
        self.loading_thumbnail_event = threading.Event()
        self.loading_video_event = threading.Event()  

    def validate_input(self, *args):
        try:
            value = self.var.get()
        except tk.TclError:
            self.var.set(self.frame_interval)
        else: 
            if value < 0.04:
                self.var.set(0.04)
                self.frame_interval = 0.04
            elif value > 400: 
                self.var.set(400) 
                self.frame_interval = 400           
            else: 
                self.frame_interval = value              

    def on_resize(self, event):
        # 更新画布大小以填充窗口
        width = self.winfo_width()
        height = self.winfo_height()
        self.canvas.config(width=width - 10, height=height - 100)  # 调整画布大小

    def load_thumbnail(self):
        self.loading_thumbnail_event.set()
        self.thumbnail_loading_thread()
        # self.thumbnail_button.config(text="取消加载", command=self.cancel_thumbnail_loading)
        self.thumbnail_button.config(text="加载中...")
        self.spinbox.config(state="disabled")

    def load_video(self):
        self.loading_video_event.set()
        self.video_loading_thread()
        self.video_button.config(text="取消加载", command=self.cancel_video_loading)

    def cancel_thumbnail_loading(self):
        ...
        self.loading_thumbnail_event.clear()

    def cancel_video_loading(self):
        ...
        self.loading_video_event.clear()

    def thumbnail_load_complete(self): 
        self.thumbnail_button.config(text="打开目录", command=self.open_directory)
        self.slider.config(state='normal', from_=0, to=(self.canvas.num_img) - 1, command=self.on_slider_change)
        self.bind("<Left>", self.decrease_slider)
        self.bind("<Right>", self.increase_slider)
        # self.bind("<MouseWheel>", self.scroll_slider) # 貌似没有预想效果

        self.tip_window = None  # Initialize tip_window attribute to None
        self.tip_job = None  # Initialize a variable to store the ID of the after job

        # Allow the window to be focused so it can receive key events
        self.focus_set()

    def decrease_slider(self, event):
        self.slider.set(max(self.slider.get() - 1, self.slider['from']))

    def increase_slider(self, event):
        self.slider.set(min(self.slider.get() + 1, self.slider['to']))

    def scroll_slider(self, event):
        new_val = self.slider.get() + (1 if event.delta > 0 else -1)     
        new_val = min(max(new_val, self.slider['from']), self.slider['to'])  
        self.slider.set(new_val)        

    def thumbnail_loading_thread(self):
        self.instance_path = isinstance_path = os.path.join(self.temp_path, self.short_name)
        os.makedirs(isinstance_path, exist_ok=True)
        self.thumbnail_loader = ThumbnailLoader(self.data_path, self.video_lst, self.frame_interval, 
                                                isinstance_path, self.thumbnail_progress_text, self.canvas, 
                                                self.loading_thumbnail_event)
        self.thumbnail_loader.start()
        self.event_poll(lambda: self.thumbnail_loader.is_alive(), 40, 
                        self.thumbnail_load_complete) 
        # 每隔40ms轮询一次加载线程是否完成

    def video_loading_thread(self):
        self.instance_path = isinstance_path = os.path.join(self.temp_path, self.short_name)
        os.makedirs(isinstance_path, exist_ok=True)
        self.video_loader = VideoLoader(self.data_path, self.video_lst,  
                                        isinstance_path, self.canvas, 
                                        self.loading_video_event)
        self.video_loader.start()
        # self.event_poll()
    
    def event_poll(self, condition_func, delay_ms, task_func): 
        if condition_func(): 
            self.after(delay_ms, lambda: self.event_poll(condition_func, delay_ms, task_func))
        else: 
            task_func()

    def open_directory(self): 
        # 使用操作系统命令来打开目录
        if os.name == 'nt':  # Windows系统
            os.startfile(self.instance_path)
        elif os.name == 'posix':  # Linux和macOS系统
            if sys.platform == 'darwin':  # macOS系统
                subprocess.Popen(['open', self.instance_path])
            else:  # Linux系统
                subprocess.Popen(['xdg-open', self.instance_path])
        else:
            warnings.warn(f"无法在当前操作系统{sys.platform}上打开文件管理器")     

    def on_slider_change(self, value: str):
        slider_value = round(float(value))
        self.show_tip(f"{slider_value+1}/{self.canvas.num_img}")
        self.update_canvas(self.canvas.imgarr[slider_value])

    def show_tip(self, message):
        # Cancel the existing after job if it's still scheduled
        if self.tip_job is not None:
            self.after_cancel(self.tip_job)
            self.tip_job = None

        # Destroy the existing tip window if it's still open
        if self.tip_window is not None and self.tip_window.winfo_exists():
            try: 
                self.tip_window.destroy()
            except: 
                pass
            self.tip_window = None

        # Calculate the position of the tooltip
        x = self.slider.winfo_x() + (self.slider.get() - self.slider['from']) / (self.slider['to'] - self.slider['from']) * self.slider.winfo_width()
        y = self.slider.winfo_y()

        # Create a new top-level window
        self.tip_window = tk.Toplevel(self)
        self.tip_window.wm_overrideredirect(True)  # Remove window decorations
        self.tip_window.wm_geometry(f"+{int(self.winfo_rootx() + x)}+{int(self.winfo_rooty() + y - 30)}")  # Position window above the slider

        # Add a label with the message
        label = tk.Label(self.tip_window, text=message, background="#ffffe0", borderwidth=1, relief="solid")
        label.pack()

        # Schedule the tip to close after 0.5s and store the job ID
        self.tip_job = self.tip_window.after(500, self.destroy_tip_window)

    def destroy_tip_window(self):
        if self.tip_window is not None and self.tip_window.winfo_exists():
            self.tip_window.destroy()
            self.tip_window = None
        self.tip_job = None  # Reset the job ID when the window is destroyed

    def update_canvas(self, img):
        # 在线程中更新画布
        self.canvas.after(0, self._update_canvas, img)

    def _update_canvas(self, img):
        # 清除画布
        self.canvas.delete("all")

        # 获取画布的当前大小
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # 调整图像大小以填充画布，使用 NEAREST 方法以提高速度
        pil_image_resized = img.resize((canvas_width, canvas_height), Image.Resampling.NEAREST)

        # # 调整图像大小以填充画布
        # pil_image_resized = pil_image.resize((canvas_width, canvas_height), Image.LANCZOS)    

        # 创建 ImageTk.PhotoImage 对象并在画布上显示
        photo = ImageTk.PhotoImage(pil_image_resized)
        self.canvas.create_image(0, 0, anchor='nw', image=photo)
        
        # 保存引用以防止被垃圾回收
        self.canvas.image = photo
