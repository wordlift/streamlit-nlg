import os
import re
import time
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
from models import summarize_text

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def list_directories(data_path):
    dir_list = []

    # List all existing projects
    for root, dirs, files in os.walk(data_path):
        for dir_folder in dirs:
            dir_name = os.path.join(root, dir_folder)
            dir_list.append(dir_name.split('/')[-1])
    return dir_list


def delete_files(project_folder):
    print(project_folder)
    if os.path.isdir(project_folder):
        for root, dirs, files in os.walk(project_folder):
            for file in files:
                try:
                    os.remove(project_folder + "/" + file)
                except OSError as e:
                    return e
    else:
        return 'Directory not found: {}'.format(project_folder)
    return 'All files have been deleted. Project name: {}'.format(project_folder)


def delete_folder(project_folder):
    if project_folder not in ['./data/default_project']:
        if os.path.isdir(project_folder):
            st.warning(delete_files(project_folder))
            try:
                os.rmdir(project_folder)
            except OSError as e:
                return "Error: %s : %s" % (project_folder, e.strerror)
        else:
            return f"No directory to delete. {project_folder} not found."
    else:
        return "Cannot remove the default project"

    return "Project removed."


def list_project_files(project_folder):
    filelist = []
    try:
        for root, dirs, files in os.walk(project_folder):
            for file in files:
                filename = os.path.join(root, file)
                filelist.append(filename.split('/')[-1])
        if not filelist:
            return "The selected directory is empty."
        else:
            return filelist
    except:
        return "Error while listing project files"


def download_data(project_folder):
    filelist = []
    try:
        for root, dirs, files in os.walk(project_folder):
            for file in files:
                filename = os.path.join(root, file)
                if filename.split('.')[-1] in ['csv', 'xlsx']:
                    filelist.append(filename.split('/')[-1])

        if not filelist:
            return "No file to download."
        else:
            zip_and_download(project_folder + "/", filelist)
    except:
        return "Error while downloading the data."


def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


def build_the_query(main_query, custom_search, search_engine):
    # There are 2 steps for building the query
    # Step 1: Get the search engine with/without the site operator
    if custom_search:
        final_query = main_query
    else:
        final_query = main_query + " site:{}".format(search_engine)
    # Step 2: Exclude PDF files from the SERP
    final_query = final_query + " -filetype:pdf"

    return final_query


# Run Google search
@st.cache
def get_serp_results(uQuery, uTLD, uNum, uStart, uStop, uCountry, uLanguage):
    d = []
    for j in search(query=uQuery, tld=uTLD, lang=uLanguage, num=uNum, start=uStart, stop=uStop,
                    pause=2, country=uCountry):
        d.append(j)
    return d


# Scraping results with Wordlift. Trafilatura can be an option.
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
    try:
        trafilatura_body = trafilatura.extract(response_body,
                                               favor_precision=True,
                                               include_tables=True,
                                               include_formatting=False,
                                               include_comments=False,
                                               include_links=False)
    except:
        trafilatura_body = ''
    return trafilatura_body


def check_grammar(_sentences):
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
        _summary_result = 'I am sorry. I am afraid I cannot answer it.'
        st.warning(_summary_result)


def summarize_html(serp_result, clean_sentences, summary_model):
    summarization_details = []
    if clean_sentences:
        summary_result = summarize_text(clean_sentences, summary_model)
    else:
        summary_result = 'I am sorry. I am afraid I cannot answer it.'

    summarization_details.append(summary_result)
    summarization_details.append(serp_result)
    summarization_details.append(summary_model)
    summarization_details.append(clean_sentences[:800])

    return summarization_details


def summarize_url(serp_result, quora_flag, perform_sentence_quality, summary_model):
    summarization_details = []
    sentences = []

    # Scrape the HTML content of a given URL
    response_body = get_html_from_urls(serp_result, quora_flag)

    # Retrieve the content data from the json object
    if (not response_body) or (response_body == "Connection Error"):
        clean_sentences = ''
        summarization_details.append("Connection Error")
        summarization_details.append(serp_result)
        summarization_details.append("Connection Error")
        summarization_details.append("Connection Error")
    else:
        trafilatura_body = clean_html_with_trafilatura(response_body)

        # In some cases, the scraper returns an error. Remove it and keep the last try/part.
        response_wait_message = 'Something went wrong. Wait a moment and try again.'
        if response_wait_message in trafilatura_body:
            trafilatura_body = trafilatura_body.split(response_wait_message)[-1][1:]

        trafilatura_body = trafilatura_body.replace('\n', ' ')

        if perform_sentence_quality == 'Yes':
            sentences = check_grammar(trafilatura_body)
        else:
            sentences.append(trafilatura_body)

        clean_sentences = ' '.join(sentences)
        clean_sentences = clean_sentences.strip()
        summarization_details = summarize_html(serp_result, clean_sentences, summary_model)
    return summarization_details, clean_sentences


def loop_and_summarize(df_queries, project_data_path, summarizer_name, grammar_check, search_location, search_language,
                       search_engine, custom_search_id, count_urls):
    count_search_requests = 0  # Count the number of Google searches
    quora_flag = 1  # 1 takes only the top result, 0 takes all quora answers, -1 not a quora custom search

    # The following lists are used to create the final output CSV file
    result_summary_list = []
    result_summarized_url_list = []
    result_model_name_list = []
    result_query_list = []
    result_text_to_summarize_list = []

    for index, row in df_queries.iterrows():  # Loop 1: Process all the queries
        # Pause every 10 requests
        if count_search_requests % 10 == 0 and count_search_requests != 0:
            write_response = write_result_to_file(result_query_list, result_summary_list,
                                                  result_summarized_url_list,
                                                  result_model_name_list,
                                                  result_text_to_summarize_list,
                                                  project_data_path, count_search_requests)
            st.write(
                f"After {count_search_requests} requests, let's pause for a while. {write_response}")
            time.sleep(30)

        # Build the search query that will be sent to Google
        final_query = build_the_query(row[df_queries.columns[0]], custom_search_id, search_engine)

        # Send the search query to Google
        serp_results = get_serp_results(final_query, "com", 5, 0, count_urls, search_location, search_language)
        count_search_requests += 1

        if serp_results:  # Check that SERP returns at least one URL
            multiple_urls_sentences = []  # Is specific for each query but common for multiple URLs

            for serp_result in serp_results:  # Loop 2: Process all the SERP URLs
                # Get the HTML content and then summarize
                summarization_details, single_url_sentences = summarize_url(serp_result, quora_flag,
                                                                            grammar_check,
                                                                            summarizer_name)
                # summarization_details is stores specific ordered information
                result_query_list.append(row[df_queries.columns[0]])
                result_summary_list.append(summarization_details[0])
                result_summarized_url_list.append(summarization_details[1])
                result_model_name_list.append(summarization_details[2])
                result_text_to_summarize_list.append(summarization_details[3])

                multiple_urls_sentences.append(single_url_sentences)

            # Summarize the content of multiple URLs
            if len(serp_results) > 1:
                clean_multiple_urls_sentences = ' '.join(multiple_urls_sentences)
                clean_multiple_urls_sentences = clean_multiple_urls_sentences.strip()
                # Summarize the combined sentences and store them
                if clean_multiple_urls_sentences:
                    multiple_urls_summary = summarize_text(clean_multiple_urls_sentences, summarizer_name)
                else:
                    multiple_urls_summary = 'I am sorry. I am afraid I cannot answer it.'
                result_query_list.append(row[df_queries.columns[0]])
                result_summary_list.append(multiple_urls_summary)
                result_summarized_url_list.append('Combined SERP URLs')
                result_model_name_list.append(summarizer_name)
                result_text_to_summarize_list.append(clean_multiple_urls_sentences[:800])
        else:
            return 'SERP is empty.'

    write_response = write_result_to_file(result_query_list, result_summary_list,
                                          result_summarized_url_list,
                                          result_model_name_list, result_text_to_summarize_list,
                                          project_data_path)
    return write_response


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
        write_message = f"Result file saved to disk: {_data_path}"
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


def prepare_email(st_pwd, st_destination_email, project_data_path, zip_files):
    if st_pwd and st_destination_email:
        try:
            if validate_email_format():
                send_email(st_pwd, project_data_path, st_destination_email, zip_files)
                return "Email sent."
            else:
                return "Email not sent."
        except:
            return "Error while sending the email."


def validate_email_format(st_destination_email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if not re.fullmatch(regex, st_destination_email):
        st.warning("Invalid email format")
        return False
    return True


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
