import google
import transformers

import streamlit as st
import re
import pandas as pd
import trafilatura
from transformers import AutoTokenizer, AutoModelWithLMHead

@st.cache(show_spinner=False)
def load_tokenizer():
    tokenizer = AutoTokenizer.from_pretrained("mrm8488/t5-base-finetuned-summarize-news")
    return tokenizer

@st.cache(show_spinner=False)
def load_model():
    model = AutoModelWithLMHead.from_pretrained("mrm8488/t5-base-finetuned-summarize-news")
    return model

# Installing t5-base-finetuned-summarize-news
tokenizer = load_tokenizer()
model = load_model()

# st.set_page_config has graduated out of beta. On 2021-01-06, the beta_ version will be removed.
PAGE_CONFIG = {
    "page_title":"Free SEO Tools by WordLift",
    "page_icon":"🔥",
    "layout":"centered"
    }
st.set_page_config(**PAGE_CONFIG)

# running the query in Google
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
                                    early_stopping=False)
    preds = [tokenizer.decode(g, skip_special_tokens=True, clean_up_tokenization_spaces=True) for g in generated_ids]
    return preds[0]

# Streamlit encourages well-structured code, like starting execution in a main() function.
def main():

    # Here comes the sidebar w/ logo, credits and navigaton
    st.sidebar.image("logo-wordlift.png", width=200)
    st.sidebar.subheader("Text Generator")
    st.sidebar.info("Cudos to the WordLift Team")

    # st.title("NLG Streamlit App")
    st.title(":fire:AI Text Generator:fire:")
    st.subheader("Prepare Your Question")
    st.markdown("""
    #### TL;DR
    This is a NLG based demo to show how modern neural network generate text. 
    Type a custom snippet and hit **Generate**. If you are interested, read more on our [blog](https://wordlift.io/blog/en/). 
            """)
    user_input = st.text_area("Write Your Question Here 👇")

    if st.button("Generate"):
        results_1 = getResults(user_input, "com", 3, 1,3)
        d = readResults(results_1, user_input)
        d = list(filter(None.__ne__, d))
        d = [i for i in d if len(i)>= 200]
        full_body = ' '.join(d)
        summary_result = summarize(full_body, 150)

        st.subheader('💎 Answer 💎')

        st.success(summary_result)

 
if __name__ == "__main__":
    main()