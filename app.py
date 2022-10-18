import os
import sys
import subprocess
import pandas as pd
import streamlit as st
from utils import load_css
from utils import mkdir_p, send_email
from utils import display_result, clean_html_with_trafilatura
from utils import summarize, evaluate_sentence_quality
from utils import write_result_to_file, zip_and_download
from utils import get_serp_results, get_html_from_urls
import time

data_path = "./data/"
os.environ['TOKENIZERS_PARALLELISM'] = "true"

# Streamlit UI
load_css("style.css")
st.title('Search & Summarize')

# The set of available flow options for the user: Flow, URL, Text
st.sidebar.header('Choose what do you want to do:')
st.sidebar.markdown("*Flow:* to start from single/multiple queries. <br/>"
                    "*URL:* to summarize the content of a URL. <br/>"
                    "*Text:* to summarize a text you provide. <br/>",
                    unsafe_allow_html=True)
st_source_entry = st.sidebar.radio('Options:', ["Flow", "URL", "Text"], index=0, key='workflow')

# UI input to create the directory where to store the project's data
if st_source_entry in ["Flow"]:
    st.sidebar.header('Project name (important)')
    st_project_folder = st.sidebar.text_input('Provide a name to your project', "default_project", key="input_project",
                                              help="This allows you to download the data (Flow option).")

    # Default configuration that the user can customize:
    st.sidebar.header('Configuration')
    if st_source_entry == "Flow":
        st_top_serp_count = st.sidebar.slider('Enter # of URLs [1-5]:', 1, 5, 2)

    # st_pwd = st.secrets["pwd"]  # Key for sending emails
    st_pwd = st.sidebar.text_input('App key:')
    st_destination_email = st.sidebar.text_input('Email address:', key='input_email')

    languages = ["en", "it", "de", "nl", "pt", "es", "fr"]
    countries = ["US", "GB", "AU", "IN", "CA",
                 "IT",
                 "DE",
                 "NL", "BE",
                 "PT", "BR",
                 "ES",
                 "FR"]

    with st.sidebar.expander("Languages & Geos"):
        st.write('Settings for Google Search')
        target_language = st.selectbox("select Language", languages)
        target_geo = st.selectbox("Select Country", countries)
else:
    st_project_folder = 'default_project'


with st.sidebar.expander("Sentence evaluation"):
    perform_sentence_quality = st.radio('Perform sentence quality evaluation:', ["Yes", "No"], index=0)

st.sidebar.header('Download or clean my data')
with st.sidebar.expander("List all"):
    dirlist = []

    for root, dirs, files in os.walk(data_path):
        for dir_folder in dirs:
            dir_name = os.path.join(root, dir_folder)
            dirlist.append(dir_name.split('/')[-1])
    st.write("-------")
    if not dirlist:
        st.warning("No folder found.")
    else:
        existing_folder = st.selectbox('Existing folders', dirlist)
        selected_project = os.path.join(data_path, existing_folder)

    button_list_files = st.button("List files of a project")
    button_download_folder = st.button("Download the project data")
    button_clean_folder = st.button("⚠️ Clean the project files")
    button_delete_folder = st.button("⚠️ Delete the project folder")

# Options specific to each flow. They control what to show on the front-end.
# The flow radio box is selected
if st_source_entry == 'Flow':
    st_user_input_url = 'url_from_the_flow'  # Not needed as the input urls are returned from search

    st_query_source = st.radio('How many queries?', ["Single", "Multiple"], index=0)
    if st_query_source == 'Multiple':  # Upload a csv file that can contain one or more queries
        st.subheader('The query csv file.')
        st_query_list = st.file_uploader('Upload the token details file (CSV format)')
        st_query = ''  # Not needed as the query values are read from the csv file
    else:  # The user provides the query on the front-end
        st.subheader('Provide your search query')
        st.caption('🔥 Based on your query the results below will fetch fresh results from the SERP.')
        st_query = st.text_input('Enter your query',
                                 'Can you wear blue light glasses all day?')
# The text radio box is selected
elif st_source_entry == 'Text':
    st_user_input_text = st.text_area("Enter the text to summarize",
                                  "BERLIN—Germany’s political parties on Monday began what could"
                                  "be a monthslong bargaining process to form the next government, with two smaller parties"
                                  "in a position to decide who will succeed Angela Merkel as chancellor."
                                  "Sunday’s election marked a leftward shift for the country, with the center-left"
                                  "Social Democratic Party, or SPD, coming first and the Greens scoring strong gains."
                                  "But together they don’t hold enough seats in parliament to form a government and "
                                  "would need to bring in the pro-market Free Democratic Party as a third partner, "
                                  "forcing them to dilute their agenda. "
                                  "Other constellations are arithmetically possible, some of them involving the "
                                  "defeated conservatives, complicating talks. "
                                  "Whatever the shape of the next government, it will likely be broadly centrist—like "
                                  "the Merkel-led left-right alliance that preceded it—because many of the partners’ "
                                  "more radical or controversial proposals could cancel each other out. "
                                  "It is also likely to have a strong focus on measures to combat climate "
                                  "change, which all four parties highlighted in their campaigns and opinion polls "
                                  "show is the dominant concern for German voters. Such a focus could have far-reaching "
                                  "implications for an economy where manufacturing, especially car making, "
                                  "plays an outsize role. "
                                  "Yet the negotiations to get there could take months. And for the first time "
                                  "they will hinge on the Greens and the FDP, Germany’s new kingmakers. The two "
                                  "parties said on Sunday that they would talk to each other before entering "
                                  "negotiations with the bigger conservative bloc and the SPD. "
                                  "The center-left Greens stand for climate policies and social justice while the FDP "
                                  "is a pro-business group that has called for tax cuts and a smaller state. While "
                                  "they both qualify as centrist parties, their platforms have little overlap. "
                                  "Courting them are Olaf Scholz, the SPD candidate who secured a narrow victory "
                                  "with 25.7% of the vote, and Armin Laschet, the conservative candidate who "
                                  "delivered his party’s worst-ever result of 24.1%.", height=500)
# URL radio box is selected
elif st_source_entry == 'URL':
    st_user_input_url = st.text_input("Enter a URL to scrape and summarize",
                                      'https://www.medicalrecords.com/health-a-to-z/ayurveda-special', key="input_url")
else:
    st.error("Source entry error.")

if st_source_entry == 'Flow':
    # Provides the user with the option to run a default Google search or use Google's search operator (site:)
    st_search_engine = st.radio('🔎 Where to run the search?:', ["Google", "Custom"], index=0)
    if st_search_engine == 'Custom':
        st_search_engine = st.text_input("Value for the site search operator:", "quora.com")

# The user can choose which summarizer to use
st_summary_model = st.radio(
    'Which summarizer to use?',
    ['T5-base', 'Roberta-med', 'Long-T5', 'German', 'Italian'], index=0)

summary_models = [st_summary_model]
col1, col2, col3 = st.columns(3)
button_start = col2.button("Click to start", key="button_start")


def main():
    print("Starting..")

    query_list_filename = 'queries.csv'
    default_min_summary_length = 32
    default_max_summary_length = 512

    if len(st_project_folder) > 0:  # check if the provided client profile isn't an empty value

        # First we create the output directory where all the data will be stored
        project_data_path = os.path.join(data_path, st_project_folder)
        mkdir_p(project_data_path)  # create local path for data

        if button_start:
            graded_sentences = []

            # For both Flow and URL options a live Google search has to be run
            if st_source_entry == 'Flow':

                st.write('-------------------')

                if st_query_source == "Multiple":
                    with open(os.path.join(project_data_path, query_list_filename), "wb") as f:
                        f.write(st_query_list.getbuffer())
                elif st_query_source == "Single":
                    df_queries = pd.DataFrame(data=[st_query], columns=['query'])
                    df_queries.to_csv(os.path.join(project_data_path, query_list_filename), index=False)

                st.success("**Starting the workflow. If you provided an email address, "
                           "you'll be notified once completed. "
                           "Otherwise, use the list file option to check when the output is ready.**")

                search_request_count = 0
                # 1 to select the top quora result, 0 to take all quora answers, -1 not a quora custom search
                quora_flag = 1
                default_min_summary_length = 64
                default_max_summary_length = 512
                query_list_filename = 'queries.csv'

                graded_sentences = []
                # The following lists are used to create the final output CSV file
                result_summary_list = []
                result_summarized_url_list = []
                result_model_name_list = []
                result_query_list = []
                result_text_to_summarize_list = []

                # For the Flow and URL options, read the query from the newly created CSV file
                df_queries = pd.read_csv(os.path.join(project_data_path, query_list_filename))

                if not df_queries.empty:
                    for index, row in df_queries.iterrows():
                        # Pause every 10 Google search requests
                        if search_request_count % 10 == 0 and search_request_count != 0:
                            write_response = write_result_to_file(result_query_list, result_summary_list,
                                                                  result_summarized_url_list,
                                                                  result_model_name_list,
                                                                  result_text_to_summarize_list,
                                                                  project_data_path, search_request_count)
                            print(f"Pausing for a while: {write_response}")
                            time.sleep(10)

                        query_text = row[df_queries.columns[0]]

                        if st_source_entry == 'Flow':
                            # Build the query as per the user's options
                            if st_search_engine == 'Google':
                                final_query = query_text
                            else:
                                final_query = query_text + " site:{}".format(st_search_engine)

                            final_query = final_query + " -filetype:pdf"

                            print(f"Request1: I'd like to initiate a search for this query {final_query}")
                            # Request the top URLs from Google
                            serp_result_list = get_serp_results(final_query, "com", 5, 0, st_top_serp_count,
                                                                target_geo, target_language)
                            search_request_count += 1
                        else:  # Only process the URL given by the user as part of the URL flow
                            serp_result_list = [st_user_input_url]

                        combined_graded_sentences = []
                        if serp_result_list:
                            for serp_result_page in serp_result_list:  # Loop items in results

                                # Scrapes the HTML content of a given URL
                                print(f"Request2: Could you scrape the HTML for this website: {serp_result_page}")
                                response_body = get_html_from_urls(serp_result_page, quora_flag)

                                # Retrieving the content property from the json object
                                if (not response_body) or (response_body == "Connection Error"):
                                    # st.write("Empty HTML.")
                                    if st_source_entry == 'Flow':
                                        result_query_list.append(final_query)
                                    else:
                                        result_query_list.append('UI entry')

                                    result_summary_list.append("Connection Error")
                                    result_summarized_url_list.append(serp_result_page)
                                    result_model_name_list.append("Connection Error")
                                    result_text_to_summarize_list.append("Connection Error")
                                else:
                                    print("Request3: Now we have to clean the HTML with trafilatura")
                                    trafilatura_body = clean_html_with_trafilatura(response_body)
                                    # In some cases, the scraper returns:
                                    # Something went wrong. Wait a moment and try again.
                                    # Remove it and keep the last try
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

                                    combined_graded_sentences.append(clean_graded_sentences)

                                    for summary_model in summary_models:
                                        print("Request4: let's summarize")
                                        summary_result = summarize(clean_graded_sentences, summary_model,
                                                                   default_min_summary_length,
                                                                   default_max_summary_length)

                                        result_query_list.append(query_text)
                                        result_summary_list.append(summary_result)
                                        result_summarized_url_list.append(serp_result_page)
                                        result_model_name_list.append(summary_model)
                                        result_text_to_summarize_list.append(clean_graded_sentences[:800])

                            # Summarize the content of multiple URLs
                            if len(serp_result_list) > 1:
                                st.success("Summary of the combined SERP URLs")
                                combined_clean_graded_sentences = ' '.join(combined_graded_sentences)
                                combined_clean_graded_sentences = combined_clean_graded_sentences.strip()

                                for summary_model in summary_models:
                                    print("Request5: Last thing let's do the combined summarization")
                                    full_summary_result = summarize(combined_clean_graded_sentences, summary_model,
                                                                    default_min_summary_length,
                                                                    default_max_summary_length)

                                    result_query_list.append(query_text)
                                    result_summary_list.append(full_summary_result)
                                    result_summarized_url_list.append('Combined SERP URLs')
                                    result_model_name_list.append(summary_model)
                                    result_text_to_summarize_list.append(combined_clean_graded_sentences[:800])
                        else:
                            st.error('Serp empty.')

                    print(result_query_list[:3])
                    write_response = write_result_to_file(result_query_list, result_summary_list,
                                                          result_summarized_url_list,
                                                          result_model_name_list, result_text_to_summarize_list,
                                                          project_data_path)
                else:
                    pass

                # Prepare the files to be downloaded
                zip_files = ['serp_summary.csv']  # , 'summarized_serp.xlsx']
                zip_and_download(project_data_path, zip_files)
                print("Workflow successfully finished. Project name: {}".format(project_data_path.split('/')[-1]))

                if st_pwd and st_destination_email:
                    print("Sending an email.")
                    send_email(st_pwd, project_data_path, st_destination_email, zip_files)
                    print("Email sent.")
            # This is the URL flow section
            elif st_source_entry == 'URL':
                st.write('-------------------')
                df_queries = pd.DataFrame(data=[''], columns=['query'])
                df_queries.to_csv(os.path.join(project_data_path, query_list_filename))

                st.success("**Starting the workflow. If you provided an email address, "
                           "you'll be notified once completed. "
                           "Otherwise, use the list file option to check when the output is ready.**")

                process = subprocess.Popen([f"{sys.executable}", "script.py",
                                            '--perform_sentence_quality', f"{perform_sentence_quality}",
                                            '--source_entry', f"{st_source_entry}",
                                            '--summary_model', f"{st_summary_model}",
                                            '--user_input_url', f"{st_user_input_url}",
                                            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                st.warning(f"1) URL process started.")
                data, err = process.communicate()
                st.success(f"{data}")
                st.warning(f"2) URL process finished.")
            # This is the Text flow section
            else:
                if perform_sentence_quality == 'Yes':
                    graded_sentences = evaluate_sentence_quality(st_user_input_text)
                else:
                    st.warning('Skipping sentence quality check.')
                    graded_sentences.append(st_user_input_text)

                clean_graded_sentences = ' '.join(graded_sentences)
                clean_graded_sentences = clean_graded_sentences.strip()

                # Currently, only one model can be selected
                for summary_model in summary_models:
                    # Start summarization of the clean sentences
                    summary_result = summarize(clean_graded_sentences, summary_model,
                                               default_min_summary_length, default_max_summary_length)

                    # For the Text flow, display the result on the screen
                    # Results aren't written to a CSV file
                    display_result(summary_result, summary_model)

        if button_list_files:
            filelist = []

            for root, dirs, files in os.walk(selected_project):
                for file in files:
                    filename = os.path.join(root, file)
                    filelist.append(filename.split('/')[-1])
            st.write("-------")
            if not filelist:
                st.warning("Empty directory.")
            else:
                st.write(filelist)

        if button_download_folder:
            filelist = []

            for root, dirs, files in os.walk(selected_project):
                for file in files:
                    filename = os.path.join(root, file)
                    if filename.split('.')[-1] in ['csv', 'xlsx']:
                        filelist.append(filename.split('/')[-1])

            st.sidebar.write(filelist)
            if not filelist:
                st.warning("No file to download.")
            else:
                zip_and_download(selected_project + "/", filelist)

        if button_clean_folder:
            st.write("Deleting the files.")
            for root, dirs, files in os.walk(selected_project):
                for file in files:
                    try:
                        os.remove(selected_project + "/" + file)
                    except OSError as e:
                        print("Error: %s : %s" % (data_path + "/" + file, e.strerror))

        if button_delete_folder:

            st.write("Deleting the files.")
            for root, dirs, files in os.walk(selected_project):
                for file in files:
                    try:
                        os.remove(selected_project + "/" + file)
                    except OSError as e:
                        print("Error: %s : %s" % (data_path + "/" + file, e.strerror))

            st.write("Deleting the project folder")

            try:
                os.rmdir(selected_project)
            except OSError as e:
                print("Error: %s : %s" % (selected_project, e.strerror))

    else:
        st.error("Please provide a profile name in order to proceed.")


if __name__ == "__main__":
    main()
