import google
import transformers
import streamlit as st
import re
import pandas as pd
import trafilatura
from transformers import AutoTokenizer, AutoModelWithLMHead
from transformers import PegasusTokenizer, PegasusForConditionalGeneration

from Interface import *

PAGE_CONFIG = {
    "page_title":"Free SEO Tools by WordLift",
    "page_icon":"img/fav-ico.png",
    "layout":"centered"
    }
st.set_page_config(**PAGE_CONFIG)

# This will hide the hamburger menu of streamlit completely.
hide_streamlit_style = """
<style>
    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

@st.cache(allow_output_mutation=True, show_spinner = False)
def load_model():
    model = AutoModelWithLMHead.from_pretrained("mrm8488/t5-base-finetuned-summarize-news")
    return model

@st.cache(allow_output_mutation=True, show_spinner = False)
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

# Running the query in Google
@st.cache(allow_output_mutation=True, show_spinner=False)
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
@st.cache(allow_output_mutation=True, show_spinner=False)
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
@st.cache(allow_output_mutation=True, show_spinner=False)
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
@st.cache(allow_output_mutation=True, show_spinner=False)
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

    local_css("style.css")
    set_png_as_page_bg('img/pattern.png')

    # Here comes the sidebar w/ logo, credits and navigaton
    st.sidebar.image("img/logo-wordlift.png", width=200)
    st.sidebar.title("Navigation")

    options = ["WordLift BB-8", "WordLift R2-D2"]
    user_option = st.sidebar.selectbox("Chose Prefered Summerization Model 👇:", options)

    # st.sidebar.subheader("About WordLift")
    # st.sidebar.info("[WordLift](https://wordlift.io/) is the first semantic SEO tool that uses natural language processing and linked data publishing for automating structured data markup.")
    # st.sidebar.info("Kudos to the WordLift Team")
    st.sidebar.info("You will need a WordLift key. You can [get one for free](https://wordlift.io/checkout/) for 14 days.")

    # Here comes the main UI components
    # st.title(":fire:AI Text Generator:fire:")
    st.markdown('<p class="subject"> 🔥 AI Text Generator 🔥</p>', unsafe_allow_html=True)
    st.markdown('<p class="payoff"> Prepare Your Question </p>', unsafe_allow_html=True)
    
    st.write("---")

    st.markdown('<p class="question"> How it works? </p>', unsafe_allow_html=True)
    st.markdown(""" <span style = "color:grey; font-size:20px;">
                        This is an NLG based demo to show how modern neural network generate text.
                        Type a custom snippet and hit
                    </span>
                    <span style = "color:grey; font-size:20px; font-weight:bold;">
                        Generate.
                    </span>
                    <span style = "color:grey; font-size:20px;">
                        If you are interested, read more on our
                    </span>
                    <a href="https://wordlift.io/blog/en/">
                        <span style = "font-size:20px;">
                            blog
                        </span>
                    </a>

                """, unsafe_allow_html=True)
    st.write("---")

    # if user_option == 'WordLift BB-8':
    #     st.subheader("WordLift BB-8")
    # if user_option == 'WordLift R2-D2':
    #     st.subheader("WordLift R2-D2")

    # st.subheader("Prepare Your Question")
    # st.markdown("""
    # #### TL;DR
    # This is an NLG based demo to show how modern neural network generate text.
    # Type a custom snippet and hit **Generate**. If you are interested, read more on our [blog](https://wordlift.io/blog/en/).
    #         """)

    WL_key_ti = st.text_input("Enter your WordLift key")

    user_input = st.text_area("Write Your Question Here 👇")

    button_generate = st.button("Generate")

    # Installing t5-base-finetuned-summarize-news
    tokenizer = load_tokenizer()
    model = load_model()

    # Installing PEGASUS Summarization Model
    tok = load_pegasus_tokenizer()
    mod = load_pegasus_model()

    # 1
    if user_option == 'WordLift BB-8':
        if button_generate:
            if WL_key_ti:
                WL_key = WL_key_ti
            elif not WL_key_ti:
                st.error("Please provide your WordLift key to proceed.")
                st.stop()
            try:
                results_1 = getResults(user_input, "com", 3, 1,3)
                d = readResults(results_1, user_input)
                d = list(filter(None.__ne__, d))
                d = [i for i in d if len(i)>= 200]
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
        if button_generate:
            if state.WL_key_ti:
                WL_key = state.WL_key_ti
            elif not state.WL_key_ti:
                st.error("Please provide your WordLift key to proceed.")
                st.stop()
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
