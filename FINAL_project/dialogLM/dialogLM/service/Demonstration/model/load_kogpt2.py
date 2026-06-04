import torch
import sys
import kss

sys.path.append('C:\\sqlite\\mysql\\code\\AI\\FINAL_project\\dialogLM\\dialogLM\\service\\Demonstration')
from model.kogpt2 import DialogKoGPT2
from model.kogpt2_transformers import get_kogpt2_tokenizer

class AnswerGenerator:
  def __init__(self):
    self.save_ckpt_path = "C:\\sqlite\\mysql\\code\\AI\\FINAL_project\\dialogLM\\dialogLM\\service\\Demonstration\\data\\kogpt2-wellnesee-auto-regressive_epoch7_origin.pth"
    self.ctx = "cuda" if torch.cuda.is_available() else "cpu"
    self.device = torch.device(self.ctx)
    # 저장한 Checkpoint 불러오기
    self.checkpoint = torch.load(self.save_ckpt_path, map_location=self.device)

    self.model = DialogKoGPT2()
    self.model.load_state_dict(self.checkpoint['model_state_dict'])

    self.model.eval()
    self.tokenizer = get_kogpt2_tokenizer()
    self.output_size = 200  # 출력하고자 하는 토큰 갯수

  def get_answer(self, question):
    tokenized_indexs = self.tokenizer.encode(question)
    input_ids = torch.tensor([self.tokenizer.bos_token_id] + tokenized_indexs + [self.tokenizer.eos_token_id]).unsqueeze(0).to(self.device)
    result = self.model.generate(input_ids=input_ids, max_length=self.output_size)
    answer = self.tokenizer.decode(result[0].tolist()[len(tokenized_indexs)+1:], skip_special_tokens=True)

    # kss 사용해서 text split
    sentences = kss.split_sentences(answer)
    selected_fir_sentence = sentences[0]
    selected_sec_sentence = sentences[1] if len(sentences) > 1 and sentences[0] != sentences[1] else ''
    
    return selected_fir_sentence + " " + selected_sec_sentence

