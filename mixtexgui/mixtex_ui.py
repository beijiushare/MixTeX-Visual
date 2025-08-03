# Renqing Luo
# Commercial use prohibited
import tkinter as tk
from PIL import Image, ImageTk
import pystray
from pystray import MenuItem as item
import threading
from transformers import RobertaTokenizer, ViTImageProcessor
import onnxruntime as ort
import numpy as np
from PIL import ImageGrab
import pyperclip
import time
import sys
import os
import csv
import re
import ctypes
import queue

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
        self.icon = self.load_scaled_image(os.path.join(base_path, "icon.png"))

        self.main_frame = tk.Frame(self.root, bg=self.TRANSCOLOUR)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题栏
        self.title_bar = tk.Frame(self.main_frame, bg='white', height=self.scale_size(25),
                                 highlightbackground="#e0e0e0", highlightthickness=1)
        self.title_bar.pack(fill=tk.X)

        # 装饰圆圈
        circle_frame = tk.Frame(self.title_bar, bg='white')
        circle_frame.pack(side=tk.LEFT, padx=self.scale_size(8), pady=self.scale_size(5))

        # 红色圆圈
        red_circle = tk.Canvas(circle_frame, width=self.scale_size(10), height=self.scale_size(10),
                              bg='white', highlightthickness=0)
        red_circle.create_oval(1, 1, self.scale_size(9), self.scale_size(9), fill="#ff5f57", outline="")
        red_circle.pack(side=tk.LEFT, padx=self.scale_size(3))

        # 绿色圆圈
        green_circle = tk.Canvas(circle_frame, width=self.scale_size(10), height=self.scale_size(10),
                                bg='white', highlightthickness=0)
        green_circle.create_oval(0, 0, self.scale_size(10), self.scale_size(10), fill="#00c853", outline="")
        green_circle.pack(side=tk.LEFT, padx=self.scale_size(2))

        # 蓝色圆圈
        blue_circle = tk.Canvas(circle_frame, width=self.scale_size(10), height=self.scale_size(10),
                               bg='white', highlightthickness=0)
        blue_circle.create_oval(0, 0, self.scale_size(10), self.scale_size(10), fill="#2196f3", outline="")
        blue_circle.pack(side=tk.LEFT, padx=self.scale_size(2))

        # 标题文本
        title_font_size = self.scale_size(8)
        self.title_label = tk.Label(self.title_bar, text="MixTeX-Visual",
                                   bg='white', fg="#333333",
                                   font=('Times New Roman', title_font_size, 'bold'))
        self.title_label.pack(side=tk.LEFT, padx=self.scale_size(10))
        self.title_label.bind('<ButtonPress-1>', self.start_move)
        self.title_label.bind('<B1-Motion>', self.do_move)

        # 阴影边框
        self.shadow_frame = tk.Frame(self.main_frame, bg='#e0e0e0')
        self.shadow_frame.pack(padx=self.scale_size(0), pady=self.scale_size(0))
        self.text_frame = tk.Frame(self.shadow_frame, bg='white', bd=0, relief=tk.FLAT)
        self.text_frame.pack(padx=self.scale_size(1), pady=self.scale_size(1), fill=tk.BOTH, expand=True)

        # 文本框
        font_size = self.scale_size(8)
        self.text_box = tk.Text(self.text_frame, wrap=tk.WORD, bg='white', fg='#333333',
                               height=6, width=30, font=('Segoe UI', font_size),
                               bd=0, relief=tk.FLAT, highlightthickness=1, highlightbackground="#f0f0f0")
        self.text_box.pack(padx=self.scale_size(10), pady=self.scale_size(10), fill=tk.BOTH, expand=True)

        # 窗口拖动绑定
        self.title_bar.bind('<ButtonPress-1>', self.start_move)
        self.title_bar.bind('<B1-Motion>', self.do_move)
        self.main_frame.bind('<ButtonPress-3>', self.show_menu)

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

        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)

        if not os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['file_name', 'text', 'feedback'])

        # 菜单创建
        self.menu = tk.Menu(self.root, tearoff=0)
        settings_menu = tk.Menu(self.menu, tearoff=0)
        settings_menu.add_checkbutton(label="$ 公式 $", onvalue=1, offvalue=0, command=self.toggle_latex_replacement,
                                      variable=tk.BooleanVar(value=self.use_dollars_for_inline_math))
        settings_menu.add_checkbutton(label="$$ 单行公式 $$", onvalue=1, offvalue=0, command=self.toggle_convert_align_to_equations,
                                      variable=tk.BooleanVar(value=self.convert_align_to_equations_enabled))
        self.menu.add_command(label="截图", command=self.take_screenshot)
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

        self.create_tray_icon()

        self.model = self.load_model('onnx')

        if self.model is None:
            self.log("模型加载失败，部分功能将不可用")
            self.ocr_paused = True  # 暂停OCR功能
        else:
            self.ocr_thread = threading.Thread(target=self.ocr_loop, daemon=True)
            self.ocr_thread.start()
            # 启动更新文本框的线程
            self.update_thread = threading.Thread(target=self.update_text_box, daemon=True)
            self.update_thread.start()

    def scale_size(self, size):
        """根据DPI缩放尺寸"""
        return int(size * self.dpi_scale)

    def load_scaled_image(self, image_path, custom_scale=None):
        scale = custom_scale if custom_scale is not None else getattr(self, 'dpi_scale', 1.0)

        if not os.path.exists(image_path):
            alt_path = os.path.join(os.path.dirname(sys.executable), os.path.basename(image_path))
            if os.path.exists(alt_path):
                image_path = alt_path
            else:
                print(f"找不到图像文件: {image_path}")
                return Image.new('RGB', (64, 64), (200, 200, 200))

        image = Image.open(image_path)
        new_width = int(image.width * scale)
        new_height = int(image.height * scale)
        return image.resize((new_width, new_height), Image.LANCZOS)

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

    def save_data(self, image, text, feedback):
        file_name = f"{int(time.time())}.png"
        file_path = os.path.join(self.data_folder, file_name)
        image.save(file_path, 'PNG')

        rows = []
        with open(self.metadata_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        updated = False
        for row in rows[1:]:
            if row[1] == text:
                row[2] = feedback
                updated = True
                break

        if not updated:
            rows.append([file_name, text, feedback])

        with open(self.metadata_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)

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

    def load_model(self, path):
        try:
            # 模型路径检查
            model_paths = [
                path,
                os.path.join(os.path.dirname(sys.executable), 'onnx'),
                os.path.abspath("onnx")
            ]
            
            valid_path = None
            for model_path in model_paths:
                if os.path.exists(model_path):
                    required_files = [
                        os.path.join(model_path, "encoder_model.onnx"),
                        os.path.join(model_path, "decoder_model_merged.onnx"),
                        os.path.join(model_path, "tokenizer.json"),
                        os.path.join(model_path, "vocab.json")
                    ]
                    
                    if all(os.path.exists(file_path) for file_path in required_files):
                        valid_path = model_path
                        self.log(f"使用模型路径: {valid_path}")
                        break
            
            if valid_path is None:
                self.log("找不到有效的模型文件")
                ctypes.windll.user32.MessageBoxW(0, 
                    "找不到必要的模型文件\n请确保exe同目录下的onnx文件夹包含完整的模型文件。", 
                    "模型加载错误", 0)
                return None
                    
            tokenizer = RobertaTokenizer.from_pretrained(valid_path)
            feature_extractor = ViTImageProcessor.from_pretrained(valid_path)
            encoder_session = ort.InferenceSession(f"{valid_path}/encoder_model.onnx")
            decoder_session = ort.InferenceSession(f"{valid_path}/decoder_model_merged.onnx")
            self.log('\n===成功加载模型===\n')
            return (tokenizer, feature_extractor, encoder_session, decoder_session)
        except Exception as e:
            self.log(f"模型加载失败: {e}")
            ctypes.windll.user32.MessageBoxW(0, 
                f"模型加载失败: {str(e)}\n请确保exe同目录下的onnx文件夹包含完整的模型文件。", 
                "模型加载错误", 0)
            return None

    def show_feedback_options(self):
        feedback_menu = tk.Menu(self.menu, tearoff=0)
        feedback_menu.add_command(label="完美", command=lambda: self.handle_feedback("Perfect"))
        feedback_menu.add_command(label="普通", command=lambda: self.handle_feedback("Normal"))
        feedback_menu.add_command(label="失误", command=lambda: self.handle_feedback("Mistake"))
        feedback_menu.add_command(label="错误", command=lambda: self.handle_feedback("Error"))
        feedback_menu.add_command(label="标注", command=self.add_annotation)
        feedback_menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())

    def handle_feedback(self, feedback_type):
        image = self.current_image
        text = self.output
        if image and text:
            if self.check_repetition(text):
                self.log("反馈已记录: Repeat")
            else:
                self.save_data(image, text, feedback_type)
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

    def check_repetition(self, s, repeats=12):
        for pattern_length in range(1, len(s) // repeats + 1):
            for start in range(len(s) - repeats * pattern_length + 1):
                pattern = s[start:start + pattern_length]
                if s[start:start + repeats * pattern_length] == pattern * repeats:
                    return True
        return False

    def mixtex_inference(self, max_length, num_layers, hidden_size, num_attention_heads, batch_size):
        tokenizer, feature_extractor, encoder_session, decoder_session = self.model
        try:
            generated_text = ""
            head_size = hidden_size // num_attention_heads
            inputs = feature_extractor(self.current_image, return_tensors="np").pixel_values
            encoder_outputs = encoder_session.run(None, {"pixel_values": inputs})[0]
            
            num_layers = 6
            
            decoder_inputs = {
                "input_ids": tokenizer("<s>", return_tensors="np").input_ids.astype(np.int64),
                "encoder_hidden_states": encoder_outputs,
                "use_cache_branch": np.array([True], dtype=bool),
                **{f"past_key_values.{i}.{t}": np.zeros((batch_size, num_attention_heads, 0, head_size), dtype=np.float32) 
                for i in range(num_layers) for t in ["key", "value"]}
            }
            
            for _ in range(max_length):
                decoder_outputs = decoder_session.run(None, decoder_inputs)
                next_token_id = np.argmax(decoder_outputs[0][:, -1, :], axis=-1)
                token_text = tokenizer.decode(next_token_id, skip_special_tokens=True)
                generated_text += token_text
                
                # 将每个识别出的token放入队列，实现实时输出
                self.result_queue.put(token_text)
                
                if self.check_repetition(generated_text, 21):
                    self.result_queue.put('\n===?!重复重复重复!?===\n')
                    self.save_data(self.current_image, generated_text, 'Repeat')
                    break
                    
                if next_token_id == tokenizer.eos_token_id:
                    # 根据模式输出不同的完成提示
                    if self.is_custom_screenshot:
                        self.result_queue.put('\n===截图识别完成，结果已复制到剪切板===\n')
                    else:
                        self.result_queue.put('\n===成功复制到剪切板===\n')
                    break

                decoder_inputs.update({
                    "input_ids": next_token_id[:, None],
                    **{f"past_key_values.{i}.{t}": decoder_outputs[i*2+1+j] 
                    for i in range(num_layers) for j, t in enumerate(["key", "value"])}
                })
                
            if self.convert_align_to_equations_enabled:
                generated_text = self.convert_align_to_equations(generated_text)
                
            return generated_text
        except Exception as e:
            self.result_queue.put(f"Error during OCR: {e}")
            return ""

    def convert_align_to_equations(self, text):
        text = re.sub(r'\\begin\{align\*\}|\\end\{align\*\}', '', text).replace('&','')
        equations = text.strip().split('\\\\')
        converted = []
        for eq in equations:
            eq = eq.strip().replace('\\[','').replace('\\]','').replace('\n','')
            if eq:
                converted.append(f"$$ {eq} $$")
        return '\n'.join(converted)

    def pad_image(self, img, out_size):
        x_img, y_img = out_size
        background = Image.new('RGB', (x_img, y_img), (255, 255, 255))
        width, height = img.size
        
        if width < x_img and height < y_img:
            x = (x_img - width) // 2
            y = (y_img - height) // 2
            background.paste(img, (x, y))
        else:
            scale = min(x_img / width, y_img / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img_resized = img.resize((new_width, new_height), Image.LANCZOS)
            x = (x_img - new_width) // 2
            y = (y_img - new_height) // 2
            background.paste(img_resized, (x, y))
            
        return background

    def ocr_loop(self):
        while True:
            if not self.ocr_paused and (self.tray_icon.visible or not self.is_only_parse_when_show):
                try:
                    # 重置截图模式标志
                    self.is_custom_screenshot = False
                    image = ImageGrab.grabclipboard()
                    if image is not None and type(image) != list:
                        self.current_image = self.pad_image(image.convert("RGB"), (448,448))
                        result = self.mixtex_inference(512, 3, 768, 12, 1)
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
            new_icon = self.load_scaled_image(os.path.join(base_path, "icon_gray.png"))
        else:
            new_icon = self.load_scaled_image(os.path.join(base_path, "icon.png"))
            
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

    def take_screenshot(self):
        # 隐藏主窗口
        self.root.withdraw()
        time.sleep(0.1)  # 确保窗口完全隐藏
        
        # 获取系统真实分辨率（不受DPI缩放影响）
        user32 = ctypes.WinDLL('user32')
        screen_width = user32.GetSystemMetrics(0)  # 屏幕宽度
        screen_height = user32.GetSystemMetrics(1)  # 屏幕高度
        
        # 创建覆盖整个屏幕的无装饰窗口
        self.screenshot_overlay = tk.Toplevel()
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
                self.current_image = ImageGrab.grab(bbox).convert('RGB')
                # 恢复主窗口并处理截图
                self.cancel_screenshot()
                self.root.deiconify()
                self.process_screenshot()  # 处理截图
            else:
                self.cancel_screenshot()
                self.root.deiconify()
                self.log("截图区域过小，请重新选择")
    
    def cancel_screenshot(self):
        if hasattr(self, 'screenshot_overlay'):
            self.screenshot_overlay.destroy()
            del self.screenshot_overlay
        self.sel_start = None
        self.sel_rect = None
    
    def process_screenshot(self):
        # 处理截图并进行OCR识别（复用现有逻辑）
        if self.current_image:
            # 设置截图模式标志
            self.is_custom_screenshot = True
            self.current_image = self.pad_image(self.current_image, (448, 448))
            # 启动独立线程处理截图识别，避免UI卡顿
            threading.Thread(target=self._process_screenshot_async, daemon=True).start()
        else:
            self.log("截图处理失败：未获取到有效图像")
    
    def _process_screenshot_async(self):
        try:
            self.result_queue.put("\n===开始处理截图...===")
            result = self.mixtex_inference(512, 3, 768, 12, 1)
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
