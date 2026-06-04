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

class ElectraClassificationHead(nn.Module):
  def __init__(self, config, num_labels):
    super().__init__()
    self.dense = nn.Linear(config.hidden_size, 4*config.hidden_size)
    self.dropout = nn.Dropout(config.hidden_dropout_prob)
    self.out_proj = nn.Linear(4*config.hidden_size,num_labels)

  def forward(self, features, **kwargs):
    x = features[:, 0, :]
    x = self.dropout(x)
    x = self.dense(x)
    x = get_activation("gelu")(x)  
    x = self.dropout(x)
    x = self.out_proj(x)
    return x

class koElectraForSequenceClassification(ElectraPreTrainedModel):
  def __init__(self, config, num_labels):
    super().__init__(config)
    self.num_labels = num_labels
    self.electra = ElectraModel(config)
    self.classifier = ElectraClassificationHead(config, num_labels)
    self.init_weights()

  def forward(self, input_ids=None, attention_mask=None, token_type_ids=None, 
              position_ids=None, head_mask=None, inputs_embeds=None, labels=None, 
              output_attentions=None, output_hidden_states=None):
    
    discriminator_hidden_states = self.electra(input_ids, attention_mask, token_type_ids, position_ids, 
                                               head_mask, inputs_embeds, output_attentions, output_hidden_states)

    sequence_output = discriminator_hidden_states[0]
    logits = self.classifier(sequence_output)

    outputs = (logits,) + discriminator_hidden_states[1:] 

    if labels is not None:
      if self.num_labels == 1:
        loss_fct = MSELoss()
        loss = loss_fct(logits.view(-1), labels.view(-1))
      else:
        loss_fct = CrossEntropyLoss()
        loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))
      outputs = (loss,) + outputs

    return outputs  

def koelectra_input(tokenizer, str, device=None, max_seq_len=512):
  index_of_words = tokenizer.encode(str)
  attention_mask = [1] * len(index_of_words)
  padding_length = max_seq_len - len(index_of_words)
  index_of_words += [0] * padding_length
  attention_mask += [0] * padding_length

  data = {
    'input_ids': torch.tensor([index_of_words]).to(device),
    'attention_mask': torch.tensor([attention_mask]).to(device),
  }
  return data
