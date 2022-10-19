import os
import re
import errno
import requests
import pandas as pd
import trafilatura
import textstat
from googlesearch import search
import streamlit as st
from zipfile import ZipFile
import base64
import smtplib, ssl
from pathlib import Path
from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
import torch
from transformers import BertTokenizerFast, EncoderDecoderModel
from transformers import MBartTokenizer, MBartForConditionalGeneration
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from transformers import PegasusForConditionalGeneration, PegasusTokenizer


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


# Run Google search
@st.cache
def get_serp_results(uQuery, uTLD, uNum, uStart, uStop, uCountry, uLanguage):
    d = []
    for j in search(query=uQuery,
                    tld=uTLD,
                    lang=uLanguage,
                    num=uNum,
                    start=uStart,
                    stop=uStop,
                    pause=2,
                    country=uCountry):
        d.append(j)
    return d


# Scraping results with Wordlift (Trafilatura can be an option)
@st.cache
def get_html_from_urls(_url, _quora_flag):

    query = {'u': _url}
    if '?' in _url:
        _url = _url.split('?')[0]

    response_status = 500
    try:
        response = requests.get("http://chrome-dev.wordlift.it", params=query)

        # Retrieve the content property from the json object
        if response.json()['status'] == 200:

            body = response.json()['content']  # extract the content from the returned JSON

            if _quora_flag != -1:
                # if promoted then drop everything after
                if ">Promoted<" in body:
                    # st.warning("Promoted content found. It will be dropped.")
                    body = body.split(">Promoted<")[0][:-8]

                if _quora_flag == 1:
                    body = body.split('upvotes" tabindex')[0]

            return body
        else:
            return None
    except:
        body = "Connection Error"
        return body


def clean_html_with_trafilatura(response_body):
    # print("Answer: Started cleaning the HTML with trafilatura")
    trafilatura_body = trafilatura.extract(response_body,
                                           favor_precision=True,
                                           include_tables=True,
                                           include_formatting=False,
                                           include_comments=False,
                                           include_links=False)
    return trafilatura_body


def evaluate_sentence_quality(_sentences):
    _result_list = []

    _sentences_list = _sentences.split('.')

    for _sentence in _sentences_list:
        _sentence = _sentence + '. '

        score = textstat.text_standard(_sentence, float_output=False)

        if score not in ['-1th and 0th grade', '0th and 1st grade', '1st and 2nd grade',
                         '2nd and 3rd grade', '3rd and 4th grade', '4th and 5th grade']:
            _result_list.append(str(_sentence))

    return _result_list


def display_result(_summary_result, _model_name, _count=1, _total=1):
    if _summary_result.strip():
        if _total != -1:
            st.markdown(
                '<p style="font-family:sans-serif; color:LightSeaGreen; font-size: 21px;">{} summary</p>'.format \
                    (_model_name, _count,
                     _total) + '<p style="font-family:sans-serif; color:DarkSlateGrey; font-size: 14px;"><em>'
                + _summary_result + '</em></p>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<p style="font-family:sans-serif; color:MediumPurple; font-size: 21px;">{} {} summary</p>'.format(
                    _model_name, _count)
                + '<p style="font-family:sans-serif; color:DarkSlateGrey; font-size: 14px;"><em>' + _summary_result + '</em></p>',
                unsafe_allow_html=True)
    else:
        _t5_summary_result = 'I am sorry. I am afraid I cannot answer it.'
        st.warning(_t5_summary_result)


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
def summarize(text, model_name, min_summary_length=32, max_summary_length=512):

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

        returned_summary = tokenizer.batch_decode(summary_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)[0]

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
        returned_summary = tokenizer_model.decode(summary[0], skip_special_tokens=True, clean_up_tokenization_spaces=True)

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


def from_html_to_summary(serp_result, clean_graded_sentences, summary_model):
    serp_details = []

    summary_result = summarize(clean_graded_sentences, summary_model)
    serp_details.append(summary_result)
    serp_details.append(serp_result)
    serp_details.append(summary_model)
    serp_details.append(clean_graded_sentences[:800])

    return serp_details


def from_url_to_html(serp_result, quora_flag, perform_sentence_quality, summary_model):
    serp_details = []
    graded_sentences = []

    # Scrape the HTML content of a given URL
    # print(f"Request2: Could you scrape the HTML for this website: {serp_result}")
    response_body = get_html_from_urls(serp_result, quora_flag)

    # Retrieve the content data from the json object
    if (not response_body) or (response_body == "Connection Error"):
        serp_details.append("Connection Error")
        serp_details.append(serp_result)
        serp_details.append("Connection Error")
        serp_details.append("Connection Error")
    else:
        # print("Request3: Now we have to clean the HTML with trafilatura")
        trafilatura_body = clean_html_with_trafilatura(response_body)

        # In some cases, the scraper returns an error. Remove it and keep the last try/part.
        # Something went wrong. Wait a moment and try again.
        response_wait_message = 'Something went wrong. Wait a moment and try again.'
        if response_wait_message in trafilatura_body:
            trafilatura_body = trafilatura_body.split(response_wait_message)[-1][1:]

        trafilatura_body = trafilatura_body.replace('\n', ' ')

        if perform_sentence_quality == 'Yes':
            graded_sentences = evaluate_sentence_quality(trafilatura_body)
        else:
            graded_sentences.append(trafilatura_body)

        clean_graded_sentences = ' '.join(graded_sentences)
        clean_graded_sentences = clean_graded_sentences.strip()

        serp_details = from_html_to_summary(serp_result, clean_graded_sentences, summary_model)

    return serp_details, clean_graded_sentences


def write_result_to_file(_queries, _summaries, _urls, _models, _initial_texts, _data_path, _search_request_count=-1):
    df_all_data = pd.DataFrame(columns=['query', 'summary', 'summarized_url', 'model', 'text_to_summarize'])

    df_all_data['query'] = _queries
    df_all_data['summary'] = _summaries
    df_all_data['summarized_url'] = _urls
    df_all_data['model'] = _models
    df_all_data['text_to_summarize'] = _initial_texts

    if _search_request_count != -1:
        file_name = 'serp_summary_{}.csv'.format(_search_request_count)
        # xlsx_filename = 'summarized_serp_tmp_{}.xlsx'.format(_search_request_count)
    else:
        file_name = 'serp_summary.csv'
        # xlsx_filename = 'summarized_serp.xlsx'

    try:
        df_all_data.to_csv(os.path.join(_data_path, file_name))

        # with pd.ExcelWriter(os.path.join(_data_path, xlsx_filename)) as writer:
        #     df_all_data.to_excel(writer, sheet_name='SerpSummaries')
        #     writer.save()
        #     st.warning('to_xlsx')

        write_message = "Result file saved to disk."
    except:
        write_message = "Nothing was saved."

    return write_message


def zip_and_download(_data_path, faq_files):
    zipObj = ZipFile(os.path.join(_data_path, "summary_files.zip"), "w")
    # Add multiple files to the zip
    for faq_file in faq_files:
        zipObj.write(os.path.join(_data_path, faq_file))
    # close the Zip File
    zipObj.close()

    ZipfileDotZip = os.path.join(_data_path, "summary_files.zip")

    with open(ZipfileDotZip, "rb") as f:
        bytes = f.read()
        b64 = base64.b64encode(bytes).decode()
        href = f"<a href=\"data:file/zip;base64,{b64}\" download='{ZipfileDotZip}'>\
            Click here to download the summary files\
        </a>"
    st.warning('****************************')
    st.markdown(href, unsafe_allow_html=True)
    st.warning('****************************')


def send_email(pwd, project_data_path, destination_email, zip_files):
    port = 465  # For SSL
    smtp_server = "smtp.gmail.com"
    sender_email = "notifywl@gmail.com"
    receiver_email = destination_email
    password = pwd

    g_message = "Summarization job has now completed. Project name: {}".format(
        project_data_path.split('/')[-1])

    msg = MIMEMultipart()
    msg.attach(MIMEText(g_message))
    msg['Subject'] = 'WL notification'
    msg['From'] = sender_email

    for f in zip_files:
        part = MIMEBase('application', "octet-stream")
        with open(os.path.join(project_data_path, f), 'rb') as file:
            part.set_payload(file.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition',
                        'attachment; filename={}'.format(Path(f).name))
        msg.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()