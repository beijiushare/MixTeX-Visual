import tkinter as tk
import ctypes
import os
from PIL import Image, ImageTk

class UIComponents:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.dpi_scale = app.dpi_scale
        self.TRANSCOLOUR = '#a9abc6'
        
    def create_title_bar(self, main_frame):
        # 标题栏
        title_bar = tk.Frame(main_frame, bg='white', height=self.app.scale_size(25),
                            highlightbackground="#e0e0e0", highlightthickness=1)
        title_bar.pack(fill=tk.X)
        
        # 装饰圆圈
        circle_frame = tk.Frame(title_bar, bg='white')
        circle_frame.pack(side=tk.LEFT, padx=self.app.scale_size(8), pady=self.app.scale_size(5))
        
        # 红色圆圈
        red_circle = tk.Canvas(circle_frame, width=self.app.scale_size(10), height=self.app.scale_size(10),
                              bg='white', highlightthickness=0)
        red_circle.create_oval(1, 1, self.app.scale_size(9), self.app.scale_size(9), fill="#ff5f57", outline="")
        red_circle.pack(side=tk.LEFT, padx=self.app.scale_size(3))
        
        # 绿色圆圈
        green_circle = tk.Canvas(circle_frame, width=self.app.scale_size(10), height=self.app.scale_size(10),
                                bg='white', highlightthickness=0)
        green_circle.create_oval(0, 0, self.app.scale_size(10), self.app.scale_size(10), fill="#00c853", outline="")
        green_circle.pack(side=tk.LEFT, padx=self.app.scale_size(2))
        
        # 蓝色圆圈
        blue_circle = tk.Canvas(circle_frame, width=self.app.scale_size(10), height=self.app.scale_size(10),
                               bg='white', highlightthickness=0)
        blue_circle.create_oval(0, 0, self.app.scale_size(10), self.app.scale_size(10), fill="#2196f3", outline="")
        blue_circle.pack(side=tk.LEFT, padx=self.app.scale_size(2))
        
        # 标题文本
        title_font_size = self.app.scale_size(8)
        title_label = tk.Label(title_bar, text="MixTeX-Visual",
                              bg='white', fg="#333333",
                              font=('Times New Roman', title_font_size, 'bold'))
        title_label.pack(side=tk.LEFT, padx=self.app.scale_size(10))
        title_label.bind('<ButtonPress-1>', self.app.start_move)
        title_label.bind('<B1-Motion>', self.app.do_move)
        
        return title_bar
        
    def create_text_box(self, main_frame):
        # 阴影边框
        shadow_frame = tk.Frame(main_frame, bg='#e0e0e0')
        shadow_frame.pack(padx=self.app.scale_size(0), pady=self.app.scale_size(0))
        text_frame = tk.Frame(shadow_frame, bg='white', bd=0, relief=tk.FLAT)
        text_frame.pack(padx=self.app.scale_size(1), pady=self.app.scale_size(1), fill=tk.BOTH, expand=True)
        
        # 文本框
        font_size = self.app.scale_size(8)
        text_box = tk.Text(text_frame, wrap=tk.WORD, bg='white', fg='#333333',
                          height=6, width=30, font=('Segoe UI', font_size),
                          bd=0, relief=tk.FLAT, highlightthickness=1, highlightbackground="#f0f0f0")
        text_box.pack(padx=self.app.scale_size(10), pady=self.app.scale_size(10), fill=tk.BOTH, expand=True)
        
        return text_box
