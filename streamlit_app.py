import google
import transformers

import streamlit as st
import re
import pandas as pd
import trafilatura

"""
# Welcome to WordLift NLG!
"""

st.set_page_config(
    page_title="WordLift NLG",
    page_icon="🔥",
    layout="centered"
)

# Installing t5-base-finetuned-summarize-news
from transformers import AutoTokenizer, AutoModelWithLMHead
tokenizer = AutoTokenizer.from_pretrained("mrm8488/t5-base-finetuned-summarize-news")
model = AutoModelWithLMHead.from_pretrained("mrm8488/t5-base-finetuned-summarize-news")

# running the query in Google
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
    st.title("WordLift NLG")
    st.subheader("Prepare Your Question")
    user_input = st.text_area("Write Your Question Here")
    language_choice = st.selectbox("Language Choice", ["English","German"])
    if st.button("Submit"):
        if language_choice == "English":
            results_1 = getResults(user_input, "com", 3, 1,3)
            d = readResults(results_1, user_input)
            d = list(filter(None.__ne__, d))
            d = [i for i in d if len(i)>= 200]
            full_body = ' '.join(d)
            summary_result = summarize(full_body, 150)
            st.write(summary_result)
        # elif language_choice == "German":
 
if __name__ == "__main__":
    main()