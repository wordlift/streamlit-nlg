import google
import transformers

import streamlit as st
import re
import pandas as pd
import trafilatura

from transformers import AutoTokenizer, AutoModelWithLMHead
from transformers import PegasusTokenizer, PegasusForConditionalGeneration

PAGE_CONFIG = {
    "page_title":"Free SEO Tools by WordLift",
    "page_icon":"fav-ico.png",
    "layout":"centered"
    }
st.set_page_config(**PAGE_CONFIG)

@st.cache(allow_output_mutation=True)
def load_model():
    model = AutoModelWithLMHead.from_pretrained("mrm8488/t5-base-finetuned-summarize-news")
    return model

@st.cache(allow_output_mutation=True)
def load_pegasus_model():
    pegasus_model = PegasusForConditionalGeneration.from_pretrained("google/pegasus-xsum")
    return pegasus_model

@st.cache(allow_output_mutation=True, show_spinner=False)
def load_tokenizer():
    tokenizer = AutoTokenizer.from_pretrained("mrm8488/t5-base-finetuned-summarize-news")
    return tokenizer

@st.cache(allow_output_mutation=True, show_spinner=False)
def load_pegasus_tokenizer():
    pegasus_tokenizer = PegasusTokenizer.from_pretrained("google/pegasus-xsum")
    return pegasus_tokenizer

# Installing t5-base-finetuned-summarize-news
tokenizer = load_tokenizer()
model = load_model()

# Installing PEGASUS Summarization Model
tok = load_pegasus_tokenizer()
mod = load_pegasus_model()

# Running the query in Google
@st.cache
def getResults(uQuery, uTLD, uNum, uStart, uStop):
    try:
        from googlesearch import search
    except ImportError:
        print("No module named 'google' found")
    # what are we searching for
    query = uQuery
    # prepare the data frame to store the results
    d = []
    for j in search(query, tld=uTLD, num=uNum, start=uStart, stop=uStop, pause=2): # here you could also change tld and add language
        d.append(j)
        print(j)
    return d

# Scraping results with Trafilatura
def readResults(urls, query):
    # Prepare the data frame to store results
    x = []
    position = 0 # position on the serp
    # Loop items in results
    for page in urls:
        downloaded = trafilatura.fetch_url(page)
        if downloaded is not None: # assuming the download was successful
            result = trafilatura.extract(downloaded, include_tables=False, include_formatting=False, include_comments=False)
            x.append(result)
            return x

# the magic
def summarize(text, max_length=200):
    input_ids = tokenizer.encode(text,
                                  return_tensors="pt",
                                  add_special_tokens=True,
                                  padding='max_length',
                                  truncation=True,
                                  max_length=512)
    generated_ids = model.generate(input_ids=input_ids,
                                    num_beams=2,
                                    max_length=max_length,
                                    repetition_penalty=2.5,
                                    length_penalty=1.0,
                                    early_stopping=True)
    preds = [tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=True) for g in generated_ids]
    return preds[0]

# PEGASUS Summarization function
def pegasus_summarize(text2, max_length=200):
    batch = tok.prepare_seq2seq_batch(src_texts = [text2])

    # Hyperparameter Tuning
    gen = mod.generate(
        **batch,max_length = max_length, # max length of summary
        min_length = 100, # min length of summary
        do_sample = True,
        temperature = 3.0,
        top_k =30,
        top_p=0.70,
        repetition_penalty = 1.2,
        length_penalty = 5, # if more than 1 encourage model to generate #larger sequences
        num_return_sequences=1) # no of summary you want to generate

    summary = tok.batch_decode(gen, skip_special_tokens=True) # for forward pass: model(**batch)
    return summary

# Streamlit encourages well-structured code, like starting execution in a main() function.
def main():
    # Here comes the sidebar w/ logo, credits and navigaton
    st.sidebar.image("logo-wordlift.png", width=200)
    st.sidebar.title("Text Generator")
    options = ["WordLift BB-8", "WordLift R2-D2"]
    user_option = st.sidebar.selectbox("Chose Prefered Summerization Model 👇:", options)
    st.sidebar.subheader("About WordLift")
    st.sidebar.info("[WordLift](https://wordlift.io/) is the first semantic SEO tool that uses natural language processing and linked data publishing for automating structured data markup.")
    st.sidebar.info("Kudos to the WordLift Team")
    # Here comes the main UI components
    st.title(":fire:AI Text Generator:fire:")
    if user_option == 'WordLift BB-8':
        st.subheader("WordLift BB-8")
    if user_option == 'WordLift R2-D2':
        st.subheader("WordLift R2-D2")
    st.subheader("Prepare Your Question")
    st.markdown("""
    #### TL;DR
    This is a NLG based demo to show how modern neural network generate text.
    Type a custom snippet and hit **Generate**. If you are interested, read more on our [blog](https://wordlift.io/blog/en/).
            """)
    user_input = st.text_area("Write Your Question Here 👇")
    # 1
    if user_option == 'WordLift BB-8':
        if st.button("Generate"):
            try:
                results_1 = getResults(user_input, "com", 5, 1,5)
                d = readResults(results_1, user_input)
                d = list(filter(None.__ne__, d))
                d = [i for i in d if len(i)>= 150]
                full_body = ' '.join(d)
                summary_result = summarize(full_body, 150)
                st.subheader('💎 Answer 💎')
                if summary_result.strip():
                    st.success(summary_result)
                else:
                    st.error('I am sorry. I am afraid I cannot answer it.')
            except Exception:
                st.error('I am sorry. I am afraid I cannot answer it.')
    # 2
    if user_option == 'WordLift R2-D2':
        if st.button("Generate"):
            try:
                results_1 = getResults(user_input, "com", 3, 1,3)
                d = readResults(results_1, user_input)
                d = list(filter(None.__ne__, d))
                d = [i for i in d if len(i)>= 200]
                full_body = ' '.join(d)
                summary_result = pegasus_summarize(full_body, 150)
                summary = " ".join(summary_result) # converting list to string
                st.subheader('💎 Answer 💎')
                if summary.strip():
                    st.success(summary)
                else:
                    st.error('I am sorry. I am afraid I cannot answer it.')
            except Exception:
                st.error('I am sorry. I am afraid I cannot answer it.')

if __name__ == "__main__":
    main()
