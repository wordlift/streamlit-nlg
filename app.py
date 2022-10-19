import os
import re
import time
import pandas as pd
import streamlit as st
from utils import load_css
from utils import mkdir_p, display_result
from utils import send_email
from utils import get_serp_results, from_url_to_html
from utils import summarize, evaluate_sentence_quality
from utils import write_result_to_file, zip_and_download

data_path = "./data/"  # Path where all the data will be stored
query_list_filename = 'queries.csv'  # Default name of the uploaded CSV file
# os.environ['TOKENIZERS_PARALLELISM'] = "true"

# Streamlit UI
load_css("style.css")
st.title('Search & Summarize')

# The available workflows: Query, URL, Text
st_workflow_type = st.sidebar.radio('🔘 Choose the workflow to run:', ["Query", "URL", "Text"], index=0, key='workflow')
st.sidebar.caption("**Query:** to start from one/multiple queries. <br/>"
                   "**URL:** to summarize the content of a URL. <br/>"
                   "**Text:** to summarize a text you provide.", unsafe_allow_html=True)


def validate_email_format():
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if not re.fullmatch(regex, st_destination_email):
        st.warning("Invalid email format")
        return False
    return True


# UI input to create the directory where to store the project's data
if st_workflow_type in ["Query"]:
    st_project_folder = st.sidebar.text_input('📁 Provide a project name ⬇️', "default_project",
                                              key="input_project",
                                              help="This allows you to download the data once ready (Query workflow).")

    # Default configuration that the user can customize:
    st.sidebar.header('Configuration')
    if st_workflow_type == "Query":
        st_top_serp_count = st.sidebar.slider('Enter the number of URLs on Google [1-5]:', 1, 5, 2,
                                              help="The number of top ranking URLs on Google to process and summarize.")

    languages = ["en", "it", "de", "nl", "pt", "es", "fr"]
    countries = ["US", "GB", "AU", "IN", "CA",
                 "IT",
                 "DE",
                 "NL", "BE",
                 "PT", "BR",
                 "ES",
                 "FR"]

    with st.sidebar.expander("More settings for Google Search"):
        st.write('Languages & Geos')
        target_language = st.selectbox("select Language", languages)
        target_geo = st.selectbox("Select Country", countries)

    # st_pwd = st.secrets["pwd"]  # Key for sending emails
    st_destination_email = st.sidebar.text_input('✉️Destination email address:', key='input_email',
                                                 on_change=validate_email_format)
    st_pwd = st.sidebar.text_input('App key:')

else:
    st_project_folder = 'default_project'

with st.sidebar.expander("Grammatical level evaluation (English)"):
    perform_sentence_quality = st.radio('Perform sentence quality evaluation:', ["Yes", "No"], index=0)

st.sidebar.header('🗄️ Data & 🧹 Cache')
with st.sidebar.expander("See the available actions"):

    button_clear_cache = st.button("🧹 Clear the cache (impacts all the users)")

    st.write('-----')
    dirlist = []
    for root, dirs, files in os.walk(data_path):
        for dir_folder in dirs:
            dir_name = os.path.join(root, dir_folder)
            dirlist.append(dir_name.split('/')[-1])
    if not dirlist:
        st.warning("No folder found.")
    else:
        existing_folder = st.selectbox('🗄️ Select an existing project', dirlist)
        selected_project = os.path.join(data_path, existing_folder)
    button_list_files = st.button("List the files of the selected project")
    button_download_folder = st.button("Download the data of the selected project")
    st.write('-----')

    st.markdown('⚠️**Danger zone**')
    button_clean_folder = st.button("Delete the files of the selected project")
    button_delete_folder = st.button("Delete the data and the project folder")


# Options specific to each flow. They control what to show on the front-end.
# The Query workflow
if st_workflow_type == 'Query':
    st_query_source = st.radio('How many queries?', ["One", "Multiple"], index=0,
                               help="Upload a CSV file to process multiple queries, "
                                    "otherwise use the UI to enter your query.")
    if st_query_source == 'Multiple':  # The user uploads a CSV file that contain one or more queries
        st_query_list = st.file_uploader('Upload the list of queries (CSV file)')
    else:  # The user provides the query on the front-end
        st_query = st.text_input('Enter your query', 'Can you wear blue light glasses at night?')
# The text radio box is selected
elif st_workflow_type == 'Text':
    with open(os.path.join(data_path, 'sample.txt'), "r") as f:
        sample_lines = f.readlines()
    st_user_input_text = st.text_area("Enter the text to summarize", sample_lines[0], height=500)
# URL radio box is selected
elif st_workflow_type == 'URL':
    st_user_input_url = st.text_input("Enter a URL to scrape and summarize",
                                      'https://www.medicalrecords.com/health-a-to-z/ayurveda-special', key="input_url")
else:
    st.error("Source entry error.")

if st_workflow_type == 'Query':
    # Provides the user with the option to run a default Google search or use Google's search operator (site:)
    st_search_engine = st.radio('🔎 Where to run the search?:', ["Google", "Custom"], index=0)
    st.caption('🔥 Based on your query the results below will fetch fresh results from the SERP.')
    if st_search_engine == 'Custom':
        col1, col2 = st.columns(2)
        st_search_engine = col1.text_input("Value for the site search operator:", "quora.com", help="site:example.com")

# The user can choose which summarizer to use
st_summary_model = st.radio(
    'Which summarizer to use?',
    ['T5-base', 'Roberta-med', 'Long-T5', 'Pegasus-xsum', 'German', 'Italian'], index=0)

col1, col2, col3 = st.columns(3)
button_start_flow = col2.button("Click to start", key="button_start")


def main():
    print("Starting..")

    if len(st_project_folder) > 0:

        # If not already created, create the output directory where all the data will be stored
        project_data_path = os.path.join(data_path, st_project_folder)
        mkdir_p(project_data_path)

        if button_start_flow:
            if st_workflow_type == 'Query':
                st.write('-------------------')
                if st_query_source == "Multiple":  # Multiple queries in a CSV file
                    with open(os.path.join(project_data_path, query_list_filename), "wb") as query_file:
                        query_file.write(st_query_list.getbuffer())
                elif st_query_source == "One":  # Single query on the UI
                    if not st_query:
                        st.error("Cannot process an empty query")
                        st.stop()
                    else:
                        df_queries = pd.DataFrame(data=[st_query], columns=['query'])
                        df_queries.to_csv(os.path.join(project_data_path, query_list_filename), index=False)
                st.success("**Starting the *Query* workflow. If you provided an email address, you'll be notified once "
                           "completed. Otherwise, use the list file option to check when the output is ready.**")

                search_request_count = 0  # Count the number of Google searches
                quora_flag = 1  # 1 takes only the top result, 0 takes all quora answers, -1 not a quora custom search

                # The following lists are used to create the final output CSV file
                result_summary_list = []
                result_summarized_url_list = []
                result_model_name_list = []
                result_query_list = []
                result_text_to_summarize_list = []
                # Read the query from the newly created CSV file
                df_queries = pd.read_csv(os.path.join(project_data_path, query_list_filename), usecols=[0])

                if not df_queries.empty:  # Check if there's at least one query
                    for index, row in df_queries.iterrows():  # Loop 1: Process all the queries
                        # Pause every 10 requests
                        if search_request_count % 10 == 0 and search_request_count != 0:
                            write_response = write_result_to_file(result_query_list, result_summary_list,
                                                                  result_summarized_url_list,
                                                                  result_model_name_list,
                                                                  result_text_to_summarize_list,
                                                                  project_data_path, search_request_count)
                            st.write(f"After {search_request_count} requests, let's pause for a while: {write_response}")
                            time.sleep(10)

                        # There are 3 steps for building the query
                        # Step 1: Get the text of the query
                        query_text = row[df_queries.columns[0]]  # The text of the query from the CSV file
                        # Step 2: Get the search engine with/without the site operator
                        if st_search_engine == 'Google':
                            final_query = query_text
                        else:
                            final_query = query_text + " site:{}".format(st_search_engine)
                        # Step 3: Exclude PDF files from the SERP
                        final_query = final_query + " -filetype:pdf"

                        # Send the request to Google
                        serp_results = get_serp_results(final_query, "com", 5, 0, st_top_serp_count,
                                                        target_geo, target_language)
                        search_request_count += 1

                        if serp_results:  # Check if that SERP returns at least one URL
                            combined_graded_sentences = []  # Is specific for each query but common for multiple URLs

                            for serp_result in serp_results:  # Loop 2: Process all the SERP URLs
                                # Get the HTML content and then summarize
                                serp_details, clean_graded_sentences = from_url_to_html(serp_result, quora_flag,
                                                                                        perform_sentence_quality,
                                                                                        st_summary_model)
                                # serp_details is stores specific ordered information
                                result_query_list.append(query_text)
                                result_summary_list.append(serp_details[0])
                                result_summarized_url_list.append(serp_details[1])
                                result_model_name_list.append(serp_details[2])
                                result_text_to_summarize_list.append(serp_details[3])

                                combined_graded_sentences.append(clean_graded_sentences)

                            # Summarize the content of multiple URLs
                            if len(serp_results) > 1:
                                combined_clean_graded_sentences = ' '.join(combined_graded_sentences)
                                combined_clean_graded_sentences = combined_clean_graded_sentences.strip()
                                # Summarize the combined sentences and store them
                                full_summary_result = summarize(combined_clean_graded_sentences, st_summary_model)
                                result_query_list.append(query_text)
                                result_summary_list.append(full_summary_result)
                                result_summarized_url_list.append('Combined SERP URLs')
                                result_model_name_list.append(st_summary_model)
                                result_text_to_summarize_list.append(combined_clean_graded_sentences[:800])
                        else:
                            st.error('SERP is empty.')

                    write_response = write_result_to_file(result_query_list, result_summary_list,
                                                          result_summarized_url_list,
                                                          result_model_name_list, result_text_to_summarize_list,
                                                          project_data_path)
                    st.success(write_response)
                else:
                    st.error('CSV file empty.')

                # Prepare the files to be downloaded
                zip_files = ['serp_summary.csv']  # , 'summarized_serp.xlsx']
                zip_and_download(project_data_path, zip_files)
                st.success("Workflow successfully finished. Project name: {}".format(project_data_path.split('/')[-1]))

                if st_pwd and st_destination_email:
                    st.write("Sending an email.")
                    if validate_email_format():
                        send_email(st_pwd, project_data_path, st_destination_email, zip_files)
                        st.write("Email sent.")
                    else:
                        st.warning("Email not sent.")

            # This is the URL flow section
            elif st_workflow_type == 'URL':
                # The following lists are used to create the final output CSV file
                result_summary_list = []
                result_summarized_url_list = []
                result_model_name_list = []
                result_query_list = []
                result_text_to_summarize_list = []

                st.write('-------------------')
                df_queries = pd.DataFrame(data=[''], columns=['query'])
                df_queries.to_csv(os.path.join(project_data_path, query_list_filename))

                st.success("**Starting the *URL* workflow.**")

                serp_details, clean_graded_sentences = from_url_to_html(st_user_input_url, -1,
                                                                        perform_sentence_quality,
                                                                        st_summary_model)
                result_query_list.append('URL entry')
                result_summary_list.append(serp_details[0])
                result_summarized_url_list.append(serp_details[1])
                result_model_name_list.append(serp_details[2])
                result_text_to_summarize_list.append(serp_details[3])
                # For the URL flow, display the result on the screen
                display_result(serp_details[0], st_summary_model)

            # This is the Text flow section
            else:
                graded_sentences = []
                if perform_sentence_quality == 'Yes':
                    graded_sentences = evaluate_sentence_quality(st_user_input_text)
                else:
                    st.warning('Skipping sentence quality check.')
                    graded_sentences.append(st_user_input_text)

                clean_graded_sentences = ' '.join(graded_sentences)
                clean_graded_sentences = clean_graded_sentences.strip()
                # Start summarization of the clean sentences
                summary_result = summarize(clean_graded_sentences, st_summary_model)
                # For the Text flow, display the result on the screen
                display_result(summary_result, st_summary_model)

        # Buttons for the data & cache related actions
        if button_clear_cache:
            st.experimental_memo.clear()
            st.experimental_singleton.clear()
            st.success("Cache cleared.")

        if button_list_files:
            filelist = []

            for root, dirs, files in os.walk(selected_project):
                for file in files:
                    filename = os.path.join(root, file)
                    filelist.append(filename.split('/')[-1])
            st.write("-------")
            if not filelist:
                st.warning("The selected directory is empty.")
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

            st.write("Deleting the files first.")
            for root, dirs, files in os.walk(selected_project):
                for file in files:
                    try:
                        os.remove(selected_project + "/" + file)
                    except OSError as e:
                        print("Error: %s : %s" % (data_path + "/" + file, e.strerror))

            st.write("Then deleting the project folder.")

            try:
                os.rmdir(selected_project)
            except OSError as e:
                print("Error: %s : %s" % (selected_project, e.strerror))
    else:
        st.error("Please provide a profile name in order to proceed.")


if __name__ == "__main__":
    main()
