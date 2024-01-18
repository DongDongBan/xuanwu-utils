import tkinter as tk
from tkinter import ttk
import threading
from typing import List

class PreviewWindow(tk.Toplevel):
    def __init__(self, title: str, video_path_lst: List[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(title)
        self.geometry("800x600")

        self.video_path_lst = video_path_lst

        # 第一排控件
        self.thumbnail_button = ttk.Button(self, text="缩略图加载")
        self.thumbnail_button.grid(row=0, column=0, sticky="nsew")

        self.thumbnail_progress_text = tk.Text(self, height=1, width=1)
        self.thumbnail_progress_text.grid(row=0, column=1, sticky="nsew")

        self.video_button = ttk.Button(self, text="视频加载")
        self.video_button.grid(row=0, column=2, sticky="nsew")

        self.video_progress_text = tk.Text(self, height=1, width=1)
        self.video_progress_text.grid(row=0, column=3, sticky="nsew")

        # 配置列的权重，使其能够均匀分配宽度
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=3)

        # 分割线
        self.separator1 = ttk.Separator(self, orient='horizontal')
        self.separator1.grid(row=1, column=0, columnspan=4, sticky="ew", pady=5)

        # 第二排控件 - 画布
        self.canvas = tk.Canvas(self, bg="black")
        self.canvas.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)

        # 配置行的权重，使画布能够随窗口大小变化
        self.grid_rowconfigure(2, weight=1)

        # 第三排控件 - 分割线
        self.separator2 = ttk.Separator(self, orient='horizontal')
        self.separator2.grid(row=3, column=0, columnspan=4, sticky="ew", pady=5)

        # 第四排控件 - 滑动条
        self.slider = ttk.Scale(self, orient='horizontal', length=400)
        self.slider.grid(row=4, column=0, columnspan=4, sticky="ew", padx=5)

        # 为了使滑动条看起来更像播放器进度条，我们可以自定义它的样式
        style = ttk.Style(self)
        style.theme_use('clam')  # 使用 'clam' 主题作为基础，因为它允许更多自定义
        style.configure("Custom.Horizontal.TScale", troughcolor="#4D4D4D", sliderlength=20, sliderrelief='flat')
        self.slider.configure(style="Custom.Horizontal.TScale")

        # 绑定窗口大小变化事件，以便更新画布大小
        self.bind("<Configure>", self.on_resize)

        # 用于控制加载线程的事件
        self.loading_event = threading.Event()        

    def on_resize(self, event):
        # 更新画布大小以填充窗口
        width = self.winfo_width()
        height = self.winfo_height()
        self.canvas.config(width=width - 10, height=height - 100)  # 调整画布大小

    def load_thumbnail(self):
        ...
        # ... (其他代码)

    def load_video(self):
        ...
        # ... (其他代码)

    def cancel_loading(self):
        ...
        # ... (其他代码)

    def thumbnail_loading_thread(self):
        self.progress.start()
        # 这里添加缩略图加载的代码
        # 检查self.loading_event是否被设置来取消加载
        # ...
        self.progress.stop()
        self.loading_event.wait()  # 等待取消或完成
        self.cancel_loading()  # 恢复按钮状态

    def video_loading_thread(self):
        self.progress.start()
        # 这里添加视频加载的代码
        # 检查self.loading_event是否被设置来取消加载
        # ...
        self.progress.stop()
        self.loading_event.wait()  # 等待取消或完成
        self.cancel_loading()  # 恢复按钮状态