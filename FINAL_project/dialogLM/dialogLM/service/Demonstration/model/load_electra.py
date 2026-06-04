import random
import torch
import torch.nn as nn
from transformers import ElectraConfig, ElectraTokenizer
from .koelectra import koElectraForSequenceClassification, koelectra_input

class DialogElectra:
    def __init__(self, model_path, category_path, answer_path):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.save_ckpt_path = model_path

        # Load categories and answers
        self.category, self.answer = self.load_wellness_answer(category_path, answer_path)

        # Load pretrained model
        self.tokenizer = ElectraTokenizer.from_pretrained("monologg/koelectra-base-discriminator")
        electra_config = ElectraConfig.from_pretrained("monologg/koelectra-base-discriminator")
        
        self.model = koElectraForSequenceClassification.from_pretrained(
            pretrained_model_name_or_path="monologg/koelectra-base-discriminator",
            config=electra_config,
            num_labels=len(self.category)
        )
        self.model.classifier.out_proj = nn.Linear(3072, 358)
        
        state_dict = torch.load(self.save_ckpt_path, map_location=self.device)['model_state_dict']
        new_state_dict = {k: v for k, v in state_dict.items() if k in self.model.state_dict()}
        new_state_dict['classifier.out_proj.weight'] = new_state_dict['classifier.out_proj.weight'][:-1, :]
        new_state_dict['classifier.out_proj.bias'] = new_state_dict['classifier.out_proj.bias'][:-1]
        self.model.load_state_dict(new_state_dict)

        self.model.to(self.device)
        self.model.eval()


    def predict(self, sentence):
        data = koelectra_input(self.tokenizer, sentence, self.device, max_seq_len=512)
        output = self.model(**data)

        logits = output[0] if isinstance(output, tuple) else output
        softmax_logit = nn.Softmax(dim=1)(logits)
        softmax_logit = softmax_logit.squeeze()

        max_index = torch.argmax(softmax_logit).item()
        category_name = self.category[str(max_index)]

        return category_name

    def get_response(self, userQuery):
        # 사용자 질문의 카테고리를 예측합니다.
        category_name = self.predict(userQuery)
        # 해당 카테고리의 응답 목록을 가져옵니다.
        response_list = self.answer[category_name]
        # 목록에서 무작위로 하나의 응답을 선택합니다.
        response = random.choice(response_list)
        return response


    def load_wellness_answer(self, category_path, answer_path):
        with open(category_path, 'r', encoding="utf-8") as c_f, open(answer_path, 'r', encoding="utf-8") as a_f:
            category_lines = c_f.readlines()
            answer_lines = a_f.readlines()

        category = {}
        answer = {}
        for line_data in category_lines:
            data = line_data.split('    ')
            # print(data[0])
            category[data[1][:-1]] = data[0]

        for line_data in answer_lines:
            data = line_data.split('    ')
            keys = answer.keys()
            if data[0] in keys:
                answer[data[0]] += [data[1][:-1]]
            else:
                answer[data[0]] = [data[1][:-1]]
        return category, answer
