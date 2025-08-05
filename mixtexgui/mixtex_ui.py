# Renqing Luo
# Commercial use prohibited
import tkinter as tk
import pystray
from pystray import MenuItem as item
import threading
import sys
import os
import csv
import re
import ctypes
import queue
import pyperclip
import time
from PIL import Image, ImageTk
from PIL import ImageGrab

# 导入模块
from ui_components import UIComponents
from model_handler import ModelHandler
from screenshot_handler import ScreenshotHandler
import utils

if hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.abspath(".")


class MixTeXApp:
    def __init__(self, root):
        self.root = root
        # 添加 DPI 感知支持
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            self.dpi_scale = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100
            self.root.tk.call('tk', 'scaling', self.dpi_scale)
        except Exception as e:
            print(f"DPI 设置失败: {e}")
            self.dpi_scale = 1.0

        self.root.title('MixTeX')
        self.root.resizable(False, False)
        self.root.overrideredirect(True)
        self.root.wm_attributes('-topmost', 1)
        self.root.attributes('-alpha', 0.85)
        self.TRANSCOLOUR = '#a9abc6'
        self.is_only_parse_when_show = False

        # 系统托盘图标加载
        self.icon = utils.load_scaled_image(os.path.join(base_path, "icon.png"), self.dpi_scale)

        # 初始化各模块
        self.ui_components = UIComponents(self)
        self.model_handler = ModelHandler(self)
        self.screenshot_handler = ScreenshotHandler(self)

        self.main_frame = tk.Frame(self.root, bg=self.TRANSCOLOUR)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题栏
        self.title_bar = self.ui_components.create_title_bar(self.main_frame)

        # 文本框
        self.text_box = self.ui_components.create_text_box(self.main_frame)

        # 数据文件夹和元数据文件
        self.data_folder = "data"
        self.metadata_file = os.path.join(self.data_folder, "metadata.csv")
        self.use_dollars_for_inline_math = False
        self.convert_align_to_equations_enabled = False
        self.ocr_paused = False
        self.annotation_window = None
        self.current_image = None
        self.output = None
        self.is_custom_screenshot = False
        # 用于存储识别结果的队列
        self.result_queue = queue.Queue()
        self.data_initialized = False  # 新增：数据文件初始化标志

        # 菜单创建
        self.menu = tk.Menu(self.root, tearoff=0)
        settings_menu = tk.Menu(self.menu, tearoff=0)
        settings_menu.add_checkbutton(label="$ 公式 $", onvalue=1, offvalue=0, command=self.toggle_latex_replacement,
                                      variable=tk.BooleanVar(value=self.use_dollars_for_inline_math))
        settings_menu.add_checkbutton(label="$$ 单行公式 $$", onvalue=1, offvalue=0, command=self.toggle_convert_align_to_equations,
                                      variable=tk.BooleanVar(value=self.convert_align_to_equations_enabled))
        self.menu.add_command(label="截图", command=self.screenshot_handler.take_screenshot)
        self.menu.add_cascade(label="设置", menu=settings_menu)
        self.menu.add_command(label="最小化", command=self.minimize)
        self.menu.add_command(label="反馈标注", command=self.show_feedback_options)
        self.menu.add_command(label="关于", command=self.show_about)
        self.menu.add_command(label="退出", command=self.quit)

        if sys.platform == 'darwin':  # macOS
            self.root.config(menu=self.menu)
        else:  # Windows/Linux
            self.root.bind('<Button-3>', self.show_menu)
            self.root.wm_attributes("-transparentcolor", self.TRANSCOLOUR)

        self.log("正在加载模型中...")

        self.root.update_idletasks()
        self.root.deiconify()

        self.create_tray_icon()

        # 后台线程加载模型
        threading.Thread(target=self.load_model_background, daemon=True).start()

        # 延迟绑定非关键事件（100ms后执行）
        self.root.after(100, self.bind_events)

    def scale_size(self, size):
        """根据DPI缩放尺寸"""
        return int(size * self.dpi_scale)

    # 添加bind_events方法作为类成员方法
    def bind_events(self):
        """延迟绑定非关键事件，减少启动时开销"""
        # 窗口拖动绑定
        self.title_bar.bind('<ButtonPress-1>', self.start_move)
        self.title_bar.bind('<B1-Motion>', self.do_move)
        self.main_frame.bind('<ButtonPress-3>', self.show_menu)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def toggle_latex_replacement(self):
        self.use_dollars_for_inline_math = not self.use_dollars_for_inline_math

    def toggle_convert_align_to_equations(self):
        self.convert_align_to_equations_enabled = not self.convert_align_to_equations_enabled

    def minimize(self):
        self.root.withdraw()
        self.tray_icon.visible = True

    def show_about(self):
        about_text = "MixTeX-Visual\n版本: 1.0.0 \n作者: beijiux \nGithub:github.com/beijiushare/MixTeX-Visual \n网站:beijiu.top \nFork自项目：MixTeX \n版本: 3.2.4b \nMixTeX作者: lrqlrqlrq \nQQ群：612725068 \nB站：bilibili.com/8922788 \nGithub:github.com/RQLuo \n"
        self.text_box.delete(1.0, tk.END)
        self.text_box.insert(tk.END, about_text)

    def quit(self):
        self.tray_icon.stop()
        self.root.quit()

    def only_parse_when_show(self):
        self.is_only_parse_when_show = not self.is_only_parse_when_show

    def create_tray_icon(self):
        menu = pystray.Menu(
            item('显示', self.show_window),
            item("开关只在最大化启用", self.only_parse_when_show),
            item('退出', self.quit)
        )

        self.tray_icon = pystray.Icon("MixTeX", self.icon, "MixTeX", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self):
        self.root.deiconify()
        self.tray_icon.visible = False

    def show_feedback_options(self):
        feedback_menu = tk.Menu(self.menu, tearoff=0)
        feedback_menu.add_command(label="完美", command=lambda: self.handle_feedback("Perfect"))
        feedback_menu.add_command(label="普通", command=lambda: self.handle_feedback("Normal"))
        feedback_menu.add_command(label="失误", command=lambda: self.handle_feedback("Mistake"))
        feedback_menu.add_command(label="错误", command=lambda: self.handle_feedback("Error"))
        feedback_menu.add_command(label="标注", command=self.add_annotation)
        feedback_menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def handle_feedback(self, feedback_type):
        # 延迟初始化数据文件
        utils.initialize_data_files(self)
        
        image = self.current_image
        text = self.output
        if image and text:
            if utils.check_repetition(text):
                self.log("反馈已记录: Repeat")
            else:
                utils.save_data(self, image, text, feedback_type)
                self.log(f"反馈已记录: {feedback_type}")
        else:
            self.log("反馈无法记录: 缺少图片或者推理输出")

    def add_annotation(self):
        if self.annotation_window is not None:
            return

        self.annotation_window = tk.Toplevel(self.root)
        self.annotation_window.wm_attributes("-alpha", 0.85)
        self.annotation_window.overrideredirect(True)
        self.annotation_window.wm_attributes('-topmost', 1)

        self.update_annotation_position()

        font_size = self.scale_size(11)
        entry = tk.Entry(self.annotation_window, width=45, font=('Arial', font_size))
        entry.pack(padx=self.scale_size(10), pady=self.scale_size(10))
        entry.focus_set()

        confirm_button = tk.Button(self.annotation_window, text="确认",
                                   command=lambda: self.confirm_annotation(entry))
        confirm_button.pack(pady=(0, self.scale_size(10)))

        self.root.bind('<Configure>', lambda e: self.update_annotation_position())

    def confirm_annotation(self, entry):
        annotation = entry.get()
        image = self.current_image
        text = self.output
        if annotation and image and text:
            self.handle_feedback(f"Annotation: {annotation}")
            self.log(f"标注已添加: {annotation}")
        else:
            self.log("反馈无法记录: 缺少图片或推理输出或输入标注。")
        self.close_annotation()

    def update_annotation_position(self):
        if self.annotation_window:
            x = self.root.winfo_x() + self.scale_size(10)
            y = self.root.winfo_y() + self.root.winfo_height() + self.scale_size(10)
            self.annotation_window.geometry(f"+{x}+{y}")

    def close_annotation(self):
        if self.annotation_window:
            self.annotation_window.destroy()
        self.annotation_window = None

    def ocr_loop(self):
        while True:
            if not self.ocr_paused and (self.tray_icon.visible or not self.is_only_parse_when_show):
                try:
                    # 重置截图模式标志
                    self.is_custom_screenshot = False
                    image = ImageGrab.grabclipboard()
                    if image is not None and type(image) != list:
                        self.current_image = utils.pad_image(image.convert("RGB"), (448,448))
                        result = self.model_handler.mixtex_inference(512, 3, 768, 12, 1)
                        result = result.replace('\\[', '\\begin{align*}').replace('\\]', '\\end{align*}').replace('%', '\\%')
                        self.output = result
                        
                        if self.use_dollars_for_inline_math:
                            result = result.replace('\\(', '$').replace('\\)', '$')
                            
                        pyperclip.copy(result)
                except Exception as e:
                    self.result_queue.put(f"Error: {e}")
                    
                time.sleep(0.1)

    def update_icon(self):
        if self.ocr_paused:
            new_icon = utils.load_scaled_image(os.path.join(base_path, "icon_gray.png"), self.dpi_scale)
        else:
            new_icon = utils.load_scaled_image(os.path.join(base_path, "icon.png"), self.dpi_scale)
            
        self.icon = new_icon
        self.icon_tk = ImageTk.PhotoImage(self.icon)
        self.tray_icon.icon = self.icon

    def log(self, message, end='\n'):
        self.root.after(0, lambda: self._safe_log(message, end))

    def _safe_log(self, message, end):
        try:
            self.text_box.insert(tk.END, message + end)
            self.text_box.see(tk.END)
        except Exception as e:
            print(f"日志输出失败: {e}")

    def process_screenshot(self):
        # 处理截图并进行OCR识别（复用现有逻辑）
        if self.current_image:
            # 设置截图模式标志
            self.is_custom_screenshot = True
            self.current_image = utils.pad_image(self.current_image, (448, 448))
            # 启动独立线程处理截图识别，避免UI卡顿
            threading.Thread(target=self._process_screenshot_async, daemon=True).start()
        else:
            self.log("截图处理失败：未获取到有效图像")
    
    def _process_screenshot_async(self):
        try:
            self.result_queue.put("\n===开始处理截图...===")
            result = self.model_handler.mixtex_inference(512, 3, 768, 12, 1)
            result = result.replace('\\[', '\\begin{align*}').replace('\\]', '\\end{align*}').replace('%', '\\%')
            self.output = result
            
            if self.use_dollars_for_inline_math:
                result = result.replace('\\(', '$').replace('\\)', '$')
                
            pyperclip.copy(result)
        except Exception as e:
            self.result_queue.put(f"截图处理错误: {e}")

    def update_text_box(self):
        """持续从队列中获取内容并更新到文本框"""
        while True:
            try:
                # 非阻塞方式获取队列内容
                item = self.result_queue.get_nowait()
                # 使用after确保UI操作在主线程执行
                self.root.after(0, lambda: self._safe_log(item, ""))
                self.result_queue.task_done()
            except queue.Empty:
                # 队列为空时短暂休眠
                time.sleep(0.05)
            except Exception as e:
                print(f"更新文本框错误: {e}")
                time.sleep(0.1)

    # 添加新的后台加载模型方法
    def load_model_background(self):
        self.model = self.model_handler.load_model('onnx')
        if self.model is None:
            self.ocr_paused = True  # 暂停OCR功能
        else:
            # 模型加载成功后启动OCR和更新线程
            self.ocr_thread = threading.Thread(target=self.ocr_loop, daemon=True)
            self.ocr_thread.start()
            self.update_thread = threading.Thread(target=self.update_text_box, daemon=True)
            self.update_thread.start()

if __name__ == '__main__':
    try:
        root = tk.Tk()
        app = MixTeXApp(root)
        root.mainloop()
    except Exception as e:
        with open('error_log.txt', 'w') as f:
            import traceback
            f.write(str(e) + '\n')
            f.write(traceback.format_exc())
            
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, f"程序启动失败: {str(e)}\n详细信息已保存到error_log.txt", "错误", 0)