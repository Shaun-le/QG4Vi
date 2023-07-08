import torch
from datasets import Dataset
from flask import Flask, request, jsonify
from flask_cors import CORS
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, DataCollatorForSeq2Seq

app = Flask(__name__)
CORS(app)

tokenizer = AutoTokenizer.from_pretrained('lehl/ViT5-vinewqg')
model = AutoModelForSeq2SeqLM.from_pretrained('lehl/ViT5-vinewqg')

def preprocess_function(examples):
    pad_on_right = tokenizer.padding_side == "right"
    model_inputs = tokenizer(
        examples["answers" if pad_on_right else "contexts"],
        examples["contexts" if pad_on_right else "answers"],
        truncation="only_second" if pad_on_right else "only_first",
        max_length=1024,
        padding="max_length")
    model_inputs['input_ids'] = model_inputs['input_ids']
    return model_inputs

@app.route('/api', methods=['POST'])
def generate_question():

    data = request.get_json()
    context = data.get('context', '')
    answer = data.get('answer', '')

    dict_obj = {'contexts': [context], 'answers': [answer]}
    data = Dataset.from_dict(dict_obj)
    tokenized_test = data.map(preprocess_function, batched=True, remove_columns=['contexts', 'answers'], num_proc=32)
    data_collator = DataCollatorForSeq2Seq(tokenizer, model=model, return_tensors="pt")

    max_target_length = 256
    dataloader = torch.utils.data.DataLoader(tokenized_test, collate_fn=data_collator, batch_size=32)

    for i, batch in enumerate(tqdm(dataloader)):
        outputs = model.generate(
            input_ids=batch['input_ids'],  # .to('cuda'),
            max_length=max_target_length,
            attention_mask=batch['attention_mask'],  # .to('cuda'),
        )
        with tokenizer.as_target_tokenizer():
            outputs = [tokenizer.decode(out, clean_up_tokenization_spaces=True, skip_special_tokens=True) for out in
                       outputs]

    question = outputs[0]

    return jsonify({'prediction': question})

if __name__ == '__main__':
    app.run(port=7777)