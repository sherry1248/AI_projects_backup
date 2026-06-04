import torch.nn as nn
# from model.kogpt2_transformers import get_kogpt2_model
from model.kogpt2_transformers.load_model import get_kogpt2_model

class DialogKoGPT2(nn.Module):
    def __init__(self):
        super(DialogKoGPT2, self).__init__()
        self.kogpt2 = get_kogpt2_model()

    def generate(self,
                 input_ids,
                 do_sample=False,
                 max_length=50,
                 top_p=0.92,
                 top_k=50,
                 temperature=1.0,
                 no_repeat_ngram_size=0,
                 num_return_sequences=1,
                 num_beams=1,
                 early_stopping=False):
        return self.kogpt2.generate(
            input_ids=input_ids,
            do_sample=do_sample,
            max_length=max_length,
            top_p=top_p,
            top_k=top_k,
            temperature=temperature,
            no_repeat_ngram_size=no_repeat_ngram_size,
            num_return_sequences=num_return_sequences,
            num_beams=num_beams,
            early_stopping=early_stopping
        )

    def forward(self, input_ids, labels=None):
        if labels is not None:
            outputs = self.kogpt2(input_ids=input_ids, labels=labels)
        else:
            outputs = self.kogpt2(input_ids=input_ids)
        return outputs

