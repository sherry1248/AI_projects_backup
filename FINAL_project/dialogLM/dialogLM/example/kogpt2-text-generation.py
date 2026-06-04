import os
import numpy as np
import torch
import sys
sys.path.append('C:\\sqlite\\mysql\\code\\AI\\FINAL_project\\dialogLM\\dialogLM')
from model.kogpt2 import DialogKoGPT2
from transformers import GPT2TokenizerFast

root_path = 'C:\\sqlite\\mysql\\code\\AI\\FINAL_project\\dialogLM\\dialogLM'
checkpoint_path = f"{root_path}\\checkpoint"
save_ckpt_path = f"{checkpoint_path}\\kogpt2-wellnesee-auto-regressive2.pth"

ctx = "cuda" if torch.cuda.is_available() else "cpu"
device = torch.device(ctx)

# 저장한 Checkpoint 불러오기
checkpoint = torch.load(save_ckpt_path, map_location=device)

model = DialogKoGPT2()
model.load_state_dict(checkpoint['model_state_dict'])
model.to(device)
model.eval()

tokenizer = GPT2TokenizerFast.from_pretrained('skt/kogpt2-base-v2', padding_side='left')

while True:
    sent = input('Question: ')
    tokenized_indexs = tokenizer.encode(sent, add_special_tokens=False)

    try:
        # 인덱스 범위 확인
        for idx in tokenized_indexs:
            if idx >= tokenizer.vocab_size:
                raise ValueError(f"Token index {idx} is out of range.")

        input_ids = torch.tensor([tokenizer.bos_token_id,] + tokenized_indexs + [tokenizer.eos_token_id]).unsqueeze(0).to(device)
        attention_mask = torch.ones(input_ids.shape, dtype=torch.long).to(device)
        attention_mask[:, len(tokenized_indexs) + 1:] = 0  # eos_token_id 이후를 패딩으로 처리

        # generate 메서드 호출
        sample_output = model.generate(input_ids=input_ids, 
                                       attention_mask=attention_mask, 
                                       pad_token_id=tokenizer.eos_token_id)

        # 답변 출력
        answer = tokenizer.decode(sample_output[0].tolist(), skip_special_tokens=True)
        print("Answer: ", answer)
    except ValueError as e:
        print(f"A ValueError occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    print(100 * '-')
