import tkinter as tk
import ctypes
from PIL import ImageGrab

class ScreenshotHandler:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.screenshot_overlay = None
        self.sel_start = None
        self.sel_rect = None
        
    def take_screenshot(self):
        # 隐藏主窗口
        self.root.withdraw()
        self.app.root.after(100, self._create_screenshot_overlay)  # 延迟确保窗口隐藏
        
    def _create_screenshot_overlay(self):
        # 获取系统真实分辨率（不受DPI缩放影响）
        user32 = ctypes.WinDLL('user32')
        screen_width = user32.GetSystemMetrics(0)  # 屏幕宽度
        screen_height = user32.GetSystemMetrics(1)  # 屏幕高度
        
        # 创建覆盖整个屏幕的无装饰窗口
        self.screenshot_overlay = tk.Toplevel(self.root)
        self.screenshot_overlay.geometry(f"{screen_width}x{screen_height}+0+0")  # 精确设置位置和大小
        self.screenshot_overlay.overrideredirect(True)  # 无边框无标题栏
        self.screenshot_overlay.attributes('-alpha', 0.3)  # 半透明
        self.screenshot_overlay.attributes('-topmost', True)  # 置顶
        self.screenshot_overlay.config(cursor='cross')
        
        # 截图区域坐标
        self.sel_start = None
        self.sel_rect = None
        self.canvas = tk.Canvas(self.screenshot_overlay, cursor='cross', highlightbackground='red', highlightthickness=1)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定鼠标事件
        self.canvas.bind('<ButtonPress-1>', self.start_sel)
        self.canvas.bind('<B1-Motion>', self.update_sel)
        self.canvas.bind('<ButtonRelease-1>', self.end_sel)
        
        # 按ESC取消截图
        self.screenshot_overlay.bind('<Escape>', lambda e: self.cancel_screenshot())
        
    def start_sel(self, event):
        self.sel_start = (event.x, event.y)
        self.sel_rect = self.canvas.create_rectangle(0, 0, 0, 0, outline='red', width=2)
    
    def update_sel(self, event):
        if self.sel_start:
            x1, y1 = self.sel_start
            x2, y2 = event.x, event.y
            self.canvas.coords(self.sel_rect, min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    
    def end_sel(self, event):
        if self.sel_start:
            x1, y1 = self.sel_start
            x2, y2 = event.x, event.y
            bbox = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
            
            # 确保选择区域有效
            if (x2 - x1) > 10 and (y2 - y1) > 10:
                # 捕获选择区域
                self.app.current_image = ImageGrab.grab(bbox).convert('RGB')
                # 恢复主窗口并处理截图
                self.cancel_screenshot()
                self.root.deiconify()
                self.app.process_screenshot()  # 处理截图
            else:
                self.cancel_screenshot()
                self.root.deiconify()
                self.app.log("截图区域过小，请重新选择")
    
    def cancel_screenshot(self):
        if self.screenshot_overlay:
            self.screenshot_overlay.destroy()
            self.screenshot_overlay = None
        self.sel_start = None
        self.sel_rect = None
