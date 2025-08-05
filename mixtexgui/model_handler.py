import os
import sys
import numpy as np
import onnxruntime as ort
from transformers import RobertaTokenizer, ViTImageProcessor
import ctypes

from utils import check_repetition

class ModelHandler:
    def __init__(self, app):
        self.app = app
        self.model = None
        self.tokenizer = None
        self.feature_extractor = None
        self.encoder_session = None
        self.decoder_session = None
        
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
                        self.app.log(f"使用模型路径: {valid_path}")
                        break
            
            if valid_path is None:
                self.app.log("找不到有效的模型文件")
                ctypes.windll.user32.MessageBoxW(0, 
                    "找不到必要的模型文件\n请确保exe同目录下的onnx文件夹包含完整的模型文件。", 
                    "模型加载错误", 0)
                return None
                    
            self.tokenizer = RobertaTokenizer.from_pretrained(valid_path)
            self.feature_extractor = ViTImageProcessor.from_pretrained(valid_path)
            self.encoder_session = ort.InferenceSession(f"{valid_path}/encoder_model.onnx")
            self.decoder_session = ort.InferenceSession(f"{valid_path}/decoder_model_merged.onnx")
            self.app.log('\n===成功加载模型===\n')
            return (self.tokenizer, self.feature_extractor, self.encoder_session, self.decoder_session)
        except Exception as e:
            self.app.log(f"模型加载失败: {e}")
            ctypes.windll.user32.MessageBoxW(0, 
                f"模型加载失败: {str(e)}\n请确保exe同目录下的onnx文件夹包含完整的模型文件。", 
                "模型加载错误", 0)
            return None
       
    def mixtex_inference(self, max_length, num_layers, hidden_size, num_attention_heads, batch_size):
        try:
            generated_text = ""
            head_size = hidden_size // num_attention_heads
            inputs = self.feature_extractor(self.app.current_image, return_tensors="np").pixel_values
            encoder_outputs = self.encoder_session.run(None, {"pixel_values": inputs})[0]
            
            num_layers = 6
            
            decoder_inputs = {
                "input_ids": self.tokenizer("<s>", return_tensors="np").input_ids.astype(np.int64),
                "encoder_hidden_states": encoder_outputs,
                "use_cache_branch": np.array([True], dtype=bool),
                **{f"past_key_values.{i}.{t}": np.zeros((batch_size, num_attention_heads, 0, head_size), dtype=np.float32) 
                for i in range(num_layers) for t in ["key", "value"]}
            }
            
            for _ in range(max_length):
                decoder_outputs = self.decoder_session.run(None, decoder_inputs)
                next_token_id = np.argmax(decoder_outputs[0][:, -1, :], axis=-1)
                token_text = self.tokenizer.decode(next_token_id, skip_special_tokens=True)
                generated_text += token_text
                
                # 将每个识别出的token放入队列，实现实时输出
                self.app.result_queue.put(token_text)
                
                if check_repetition(generated_text, 21):
                    self.app.result_queue.put('\n===?!重复重复重复!?===\n')
                    self.app.save_data(self.app.current_image, generated_text, 'Repeat')
                    break
                    
                if next_token_id == self.tokenizer.eos_token_id:
                    # 根据模式输出不同的完成提示
                    if self.app.is_custom_screenshot:
                        self.app.result_queue.put('\n===截图识别完成，结果已复制到剪切板===\n')
                    else:
                        self.app.result_queue.put('\n===成功复制到剪切板===\n')
                    break

                decoder_inputs.update({
                    "input_ids": next_token_id[:, None],
                    **{f"past_key_values.{i}.{t}": decoder_outputs[i*2+1+j] 
                    for i in range(num_layers) for j, t in enumerate(["key", "value"])}
                })
                
            if self.app.convert_align_to_equations_enabled:
                generated_text = self.convert_align_to_equations(generated_text)
                
            return generated_text
        except Exception as e:
            self.app.result_queue.put(f"Error during OCR: {e}")
            return ""
            
    def convert_align_to_equations(self, text):
        import re
        text = re.sub(r'\\begin\{align\*\}|\\end\{align\*\}', '', text).replace('&','')
        equations = text.strip().split('\\\\')
        converted = []
        for eq in equations:
            eq = eq.strip().replace('\\[','').replace('\\]','').replace('\n','')
            if eq:
                converted.append(f"$$ {eq} $$")
        return '\n'.join(converted)
