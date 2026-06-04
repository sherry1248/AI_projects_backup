import torch
import torch.nn as nn
from torch.nn import CrossEntropyLoss, MSELoss
from transformers.activations import get_activation
from transformers import (
  ElectraPreTrainedModel,
  ElectraModel,
  ElectraConfig,
  ElectraTokenizer,
  BertConfig,
  BertTokenizer
)

# MODEL_CLASSES = {
#     "koelectra-base": (ElectraConfig, koElectraForSequenceClassification, ElectraTokenizer),
#     "koelectra-small": (ElectraConfig, koElectraForSequenceClassification, ElectraTokenizer),
#     "koelectra-base-v2": (ElectraConfig, koElectraForSequenceClassification, ElectraTokenizer),
#     "koelectra-small-v2": (ElectraConfig, koElectraForSequenceClassification, ElectraTokenizer),
# }


# def load_tokenizer(args):
#   return MODEL_CLASSES[args.model_type][2].from_pretrained(args.model_name_or_path)


class ElectraClassificationHead(nn.Module):
  """Head for sentence-level classification tasks."""

  def __init__(self, config, num_labels):
    super().__init__()
    #  # 4배 크기의 은닉 크기를 가진 완전 연결 레이어와 GELU 활성화 함수
    self.dense = nn.Linear(config.hidden_size, 4*config.hidden_size)  
    self.dropout = nn.Dropout(config.hidden_dropout_prob)
    # # 분류를 위한 출력 레이어
    self.out_proj = nn.Linear(4*config.hidden_size,num_labels)

  def forward(self, features, **kwargs):
    # # features에서 [CLS] 토큰의 표현을 추출
    x = features[:, 0, :]  # <s> 토큰 가져오기 ( [CLS]와 동일)
    x = self.dropout(x)
    x = self.dense(x)
    x = get_activation("gelu")(x)  # although BERT uses tanh here, it seems Electra authors used gelu here
    x = self.dropout(x)
    x = self.out_proj(x)
    return x

class koElectraForSequenceClassification(ElectraPreTrainedModel):
  def __init__(self,
               config,
               num_labels):
    super().__init__(config)
    self.num_labels = num_labels
    # # Electra 모델을 기본으로 사용
    self.electra = ElectraModel(config)
    # 분류 헤드
    self.classifier = ElectraClassificationHead(config, num_labels)
    
    # 가중치 초기화
    self.init_weights()

  # Forward 함수에서는 입력을 Electra 모델에 전달하고 그 결과를 분류 헤드에 전달하여 최종 분류 결과를 얻음
  def forward(
          self,
          input_ids=None,
          attention_mask=None,
          token_type_ids=None,
          position_ids=None,
          head_mask=None,
          inputs_embeds=None,
          labels=None,
          output_attentions=None,
          output_hidden_states=None,
  ):
    
    
    r"""
    labels (:obj:`torch.LongTensor` of shape :obj:`(batch_size,)`, `optional`, defaults to :obj:`None`):
        Labels for computing the sequence classification/regression loss.
        Indices should be in :obj:`[0, ..., config.num_labels - 1]`.
        If :obj:`config.num_labels == 1` a regression loss is computed (Mean-Square loss),
        If :obj:`config.num_labels > 1` a classification loss is computed (Cross-Entropy).
    """
    discriminator_hidden_states = self.electra(
      input_ids,
      attention_mask,
      token_type_ids,
      position_ids,
      head_mask,
      inputs_embeds,
      output_attentions,
      output_hidden_states,
    )

    # Discriminator에서 나온 hidden_states 중 [CLS] 토큰에 해당하는 부분 선택
    sequence_output = discriminator_hidden_states[0]
    # 선택한 hidden_states를 분류 헤드에 전달하여 로짓 생성
    logits = self.classifier(sequence_output)

    # 모델의 출력에 hidden states와 attention을 추가
    outputs = (logits,) + discriminator_hidden_states[1:]  # add hidden states and attention if they are here

    # 레이블이 주어진 경우, 손실 계산
    if labels is not None:
  
      if self.num_labels == 1:
        # 회귀 작업인 경우
        loss_fct = MSELoss()
        loss = loss_fct(logits.view(-1), labels.view(-1))

        # 다중 클래스 분류인 경우
      else:
        loss_fct = CrossEntropyLoss()
        loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))
      outputs = (loss,) + outputs

    return outputs  # (loss), (logits), (hidden_states), (attentions)


# 입력 텍스트를 koelectra 모델에 맞게 전처리하여 딕셔너리 형태로 반환하는 함수
# 최대 시퀀스 길이에 맞게 토큰화되고, 패딩이 적용된 후 딕셔너리로 반환
def koelectra_input(tokenizer, str, device = None, max_seq_len = 512):
  index_of_words = tokenizer.encode(str)
  # token_type_ids = [0] * len(index_of_words)
  attention_mask = [1] * len(index_of_words)

  # Padding Length
  padding_length = max_seq_len - len(index_of_words)

  # Zero Padding
  index_of_words += [0] * padding_length
  # token_type_ids += [0] * padding_length
  attention_mask += [0] * padding_length

  data = {
    'input_ids': torch.tensor([index_of_words]).to(device),
    'attention_mask': torch.tensor([attention_mask]).to(device),
  }
  return data
