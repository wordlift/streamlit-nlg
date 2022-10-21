import torch
import streamlit as st
from transformers import BertTokenizerFast, EncoderDecoderModel
from transformers import MBartTokenizer, MBartForConditionalGeneration
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transformers import PegasusForConditionalGeneration, PegasusTokenizer


@st.experimental_memo
def load_t5_model():
    model_name = 'mrm8488/t5-base-finetuned-summarize-news'
    _model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    return _model


@st.experimental_memo
def load_t5_tokenizer():
    model_name = 'mrm8488/t5-base-finetuned-summarize-news'
    _tokenizer = AutoTokenizer.from_pretrained(model_name)
    return _tokenizer


@st.experimental_memo
def load_longt5_model():
    model_name = 'pszemraj/long-t5-tglobal-base-16384-book-summary'
    _model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    return _model


@st.experimental_memo
def load_longt5_tokenizer():
    model_name = 'pszemraj/long-t5-tglobal-base-16384-book-summary'
    _tokenizer = AutoTokenizer.from_pretrained(model_name)
    return _tokenizer


@st.experimental_memo
def load_roberta_model():
    model_name = 'mrm8488/roberta-med-small2roberta-med-small-finetuned-cnn_daily_mail-summarization'
    _model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    return _model


@st.experimental_memo
def load_roberta_tokenizer():
    model_name = 'mrm8488/roberta-med-small2roberta-med-small-finetuned-cnn_daily_mail-summarization'
    _tokenizer = AutoTokenizer.from_pretrained(model_name)
    return _tokenizer


@st.experimental_memo
def load_pegasus_model():
    model_name = "google/pegasus-xsum"
    _model = PegasusForConditionalGeneration.from_pretrained(model_name)
    return _model


@st.experimental_memo
def load_pegasus_tokenizer():
    model_name = "google/pegasus-xsum"
    _tokenizer = PegasusTokenizer.from_pretrained(model_name)
    return _tokenizer


@st.cache
def summarize_text(text, model_name, min_summary_length=32, max_summary_length=512):
    if model_name == "T5-base":
        model = load_t5_model()
        tokenizer = load_t5_tokenizer()

        input_ids = tokenizer.encode(text,
                                     return_tensors="pt",
                                     add_special_tokens=True,
                                     padding='max_length',
                                     truncation=True,
                                     max_length=512)

        generated_ids = model.generate(input_ids=input_ids,
                                       num_beams=4,
                                       min_length=min_summary_length,
                                       max_length=max_summary_length,
                                       repetition_penalty=2.5,
                                       length_penalty=1.0,
                                       early_stopping=True)

        t5_summary = [tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=True) for g in
                      generated_ids]
        returned_summary = t5_summary[0]

    elif model_name == 'Roberta-med':
        model = load_roberta_model()
        tokenizer = load_roberta_tokenizer()

        inputs = tokenizer(text, max_length=512, return_tensors="pt", truncation=True)
        summary_ids = model.generate(inputs["input_ids"],
                                     num_beams=4,
                                     min_length=min_summary_length,
                                     max_length=max_summary_length,
                                     repetition_penalty=2.5,
                                     length_penalty=1.0,
                                     early_stopping=True
                                     )

        returned_summary = \
            tokenizer.batch_decode(summary_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)[0]

    elif model_name == 'Long-T5':
        model = load_longt5_model()
        tokenizer = load_longt5_tokenizer()

        inputs = tokenizer(text, max_length=512, return_tensors="pt", truncation=True)  # 1024
        summary_ids = model.generate(inputs["input_ids"],
                                     num_beams=4,
                                     min_length=min_summary_length,
                                     max_length=max_summary_length,
                                     repetition_penalty=2.5,
                                     length_penalty=1.0,
                                     early_stopping=True
                                     )

        returned_summary = \
        tokenizer.batch_decode(summary_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)[0]

    elif model_name == 'Pegasus-xsum':
        loaded_model = load_pegasus_model()
        tokenizer_model = load_pegasus_tokenizer()

        tokens = tokenizer_model(text, truncation=True, padding="max_length", return_tensors="pt")
        summary = loaded_model.generate(**tokens,
                                        min_length=min_summary_length,
                                        max_length=max_summary_length,
                                        do_sample=True, temperature=3.0,
                                        top_k=30, top_p=0.70,
                                        repetition_penalty=1.2,
                                        length_penalty=5,
                                        num_return_sequences=1)
        returned_summary = tokenizer_model.decode(summary[0], skip_special_tokens=True,
                                                  clean_up_tokenization_spaces=True)

    elif model_name == 'German':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        ckpt = 'mrm8488/bert2bert_shared-german-finetuned-summarization'
        tokenizer = BertTokenizerFast.from_pretrained(ckpt)
        model = EncoderDecoderModel.from_pretrained(ckpt).to(device)
        if device == 'cuda':
            model.to('cuda:0')

        returned_summary = generate_german_summary(text, tokenizer, model, device, max_summary_length)

    elif model_name == 'Italian':
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        tokenizer = MBartTokenizer.from_pretrained("ARTeLab/mbart-summarization-mlsum")
        model = MBartForConditionalGeneration.from_pretrained("ARTeLab/mbart-summarization-mlsum")
        if device == 'cuda':
            model.to('cuda:0')

        returned_summary = generate_italian_summary(text, tokenizer, model, device, max_summary_length)

    else:
        returned_summary = "[Error] No summarizer has been selected."

    return returned_summary


def generate_german_summary(text, tokenizer, model, device, min_summary_length, max_summary_length):
    inputs = tokenizer([text],
                       padding="max_length",
                       truncation=True,
                       max_length=512,
                       return_tensors="pt")
    input_ids = inputs.input_ids.to(device)
    attention_mask = inputs.attention_mask.to(device)
    output = model.generate(input_ids,
                            min_length=min_summary_length,
                            max_length=max_summary_length,
                            attention_mask=attention_mask)
    return tokenizer.decode(output[0], skip_special_tokens=True)


def generate_italian_summary(text, tokenizer, model, device, min_summary_length, max_summary_length):
    inputs = tokenizer([text],
                       padding="max_length",
                       truncation=True,
                       max_length=1024,
                       return_tensors="pt")
    input_ids = inputs.input_ids.to(device)
    attention_mask = inputs.attention_mask.to(device)
    output = model.generate(input_ids,
                            min_length=min_summary_length,
                            max_length=max_summary_length,
                            attention_mask=attention_mask)
    return tokenizer.decode(output[0], skip_special_tokens=True)