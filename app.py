import os
import time
import pandas as pd
import streamlit as st
from utils import load_css
from utils import mkdir_p, delete_files
from utils import send_email, validate_email_format
from utils import get_serp_results, from_url_to_html
from utils import summarize, check_grammar, display_result
from utils import write_result_to_file, zip_and_download
from st_on_hover_tabs import on_hover_tabs

st.set_page_config(layout="wide")
st.sidebar.image("img/fav-ico.png", width=50)
load_css("style.css")

data_path = "./data/"  # Path where all the data will be stored
query_list_filename = 'queries.csv'  # Default name of the uploaded CSV file
# os.environ['TOKENIZERS_PARALLELISM'] = "true"


def create_or_select():
    if st.session_state.selected_project == "Create a new project":
        st.session_state.create_select_project = 'create'
    else:
        st.session_state.create_select_project = st.session_state.selected_project


if 'create_select_project' not in st.session_state:
    st.session_state.create_select_project = 'select'

if 'new_project_name' not in st.session_state:
    st.session_state.new_project_name = 'default_project'

if 'summary_model' not in st.session_state:
    st.session_state.summary_model = 'T5-base'

if 'grammar_check' not in st.session_state:
    st.session_state.grammar_check = 'Yes'

if 'search_engine' not in st.session_state:
    st.session_state.search_engine = 'Google'

if 'search_number_url' not in st.session_state:
    st.session_state.search_number_url = 2

if 'search_language' not in st.session_state:
    st.session_state.search_language = 'en'

if 'search_location' not in st.session_state:
    st.session_state.search_location = 'US'

# Streamlit UI
with st.sidebar:
    tabs = on_hover_tabs(tabName=['Dashboard', 'Configuration', 'Data', 'Advanced Settings'],
                         iconName=['dashboard', 'search', 'file_open', 'settings'],
                         styles={'navtab': {
                             'background-image': 'radial-gradient(farthest-corner at 40px 40px, rgb(66, 88, 249) 0%, #007AFF 50%)',
                             'border': '2px',
                             'color': '#fff',
                             'font-size': '18px',
                             'transition': '.3s',
                             'white-space': 'nowrap',
                             'text-transform': 'uppercase'},
                             'tabOptionsStyle': {':hover :hover': {'color': '#00C48C',
                                                                   'cursor': 'pointer'}},
                             'iconStyle': {'position': 'fixed',
                                           'left': '7.5px',
                                           'text-align': 'left'},
                             'tabStyle': {'list-style-type': 'none',
                                          'margin-bottom': '30px',
                                          'padding-left': '30px'}},
                         default_choice=0)

st.title('Search & Summarize')

if tabs == 'Dashboard':
    col1, col2 = st.columns(2)

    # The available workflows: Query, URL, Text
    st_workflow_type = col1.radio('Summarize a text from a long text, from a URL or by using the SERP',
                                  ["Create FAQ", "URL", "Text"], index=0, key='workflow')

    # Options specific to each flow. They control what to show on the front-end.
    # The Query workflow
    if st_workflow_type == 'Create FAQ':
        dirlist = []

        # List all existing projects
        for root, dirs, files in os.walk(data_path):
            for dir_folder in dirs:
                dir_name = os.path.join(root, dir_folder)
                dirlist.append(dir_name.split('/')[-1])

        if not dirlist:
            st.warning("No folder found.")
        else:
            sorted_list = sorted(dirlist)
            sorted_list.insert(0, "Create a new project")

            # UI input to create the directory where to store the project's data
            existing_folder = col1.selectbox('🗄️ Project name', sorted_list, index=1,
                                             on_change=create_or_select, key="selected_project")

            if st.session_state.create_select_project == 'create':
                st.session_state.new_project_name = col1.text_input('📁 Create a new project ⬇️',
                                                                    help="Project name to download the data once ready.")
            else:
                st.session_state.new_project_name = existing_folder

        st_pwd = 'xxx'  # st.secrets["pwd"]  # Key for sending emails st_pwd = st.sidebar.text_input('App key:')
        st_destination_email = col1.text_input('✉️Send me the results', value="email@address.com", key='input_email',
                                               on_change=validate_email_format)

        st_query_list = col1.file_uploader('Upload the list of queries (CSV file)')
        # else:  # The user provides the query on the front-end
        #     st_query = st.text_input('Enter your query', 'Can you wear blue light glasses at night?')
    # The text radio box is selected
    elif st_workflow_type == 'Text':
        with open(os.path.join(data_path, 'sample.txt'), "r") as f:
            sample_lines = f.readlines()
        st_user_input_text = col1.text_area("Enter the text to summarize", sample_lines[0], height=500)
    # URL radio box is selected
    elif st_workflow_type == 'URL':
        st_user_input_url = col1.text_input("Enter a URL to scrape and summarize",
                                            'https://www.medicalrecords.com/health-a-to-z/ayurveda-special',
                                            key="input_url")
    else:
        st.error("Source entry error.")

    col1.empty()
    # col1, col2, col3 = st.columns(3)
    button_start_flow = col1.button("Click to start", key="button_start")

elif tabs == 'Data':
    col1, col2 = st.columns(2)
    col1.header('🗄️ Data')
    col1.markdown(
        f'<div style="font-size:24px; color:#FF0000">Current project name is: <b>{st.session_state.new_project_name}</b></div><br />',
        unsafe_allow_html=True)
    col1.subheader('List the files of the selected project')
    button_list_files = col1.button("Click to list")
    col1.subheader('Download the data of the selected project')
    button_download_folder = col1.button("Click to download")
    col1.subheader('⚠️**Danger zone**')
    col1.subheader("Delete the files of the selected project")
    button_clean_folder = col1.button("Delete the files")
    col1.subheader("Delete the data and the project folder")
    button_delete_folder = col1.button("Delete the project")


elif tabs == 'Configuration':
    col1, col2, col3 = st.columns(3)
    # Default configuration that the user can customize:
    col1.header('Configuration')

    # with st.expander("Settings for Google Search"):
    # if st_workflow_type == "Create FAQ":
    st.session_state.search_number_url = col1.slider('Number of URLs to analyse:', 1, 5, 2,
                                                     help="The number of top ranking URLs on Google to process and summarize.")

    languages = ["en", "it", "de", "nl", "pt", "es", "fr"]
    countries = ["US", "GB", "AU", "IN", "CA",
                 "IT",
                 "DE",
                 "NL", "BE",
                 "PT", "BR",
                 "ES",
                 "FR"]

    target_language = col1.selectbox("Select language", languages)
    target_geo = col1.selectbox("Select country", countries)

    st.session_state.search_engine = col1.radio('🔎 Use site operator:', ["Google", "Custom"], index=0)
    if st.session_state.search_engine == 'Custom':
        st.session_state.search_engine = col1.text_input("Value for the site operator:", "quora.com",
                                                         help="site:example.com")

elif tabs == 'Advanced Settings':
    col1, col2 = st.columns(2)
    col1.header('🧹 Advanced settings')

    # Provides the user with the option to run a default Google search or use Google's search operator (site:)

    # st.caption('🔥 Based on your query the results below will fetch fresh results from the SERP.')

    # The user can choose which summarizer to use
    col1.subheader("Available summarizers")
    st.session_state.summary_model = col1.selectbox(
        'Options',
        ['T5-base', 'Roberta-med', 'Long-T5', 'Pegasus-xsum', 'German', 'Italian'], index=0)

    col1.subheader("Perform grammar check")
    st.session_state.grammar_check = col1.radio('Options', ["Yes", "No"], index=0)

    col1.subheader("Clear the cache (impacts all the users)")
    button_clear_cache = col1.button("Clear the cache")


def main():
    print("Starting..")
    if tabs == 'Dashboard':
        if button_start_flow:
            if st_workflow_type == 'Create FAQ':

                if st.session_state.create_select_project == 'create':
                    if len(st.session_state.new_project_name) > 0:
                        pass
                    else:
                        st.error("Please provide a name to your new project in order to proceed.")
                        st.stop()

                search_request_count = 0  # Count the number of Google searches
                quora_flag = 1  # 1 takes only the top result, 0 takes all quora answers, -1 not a quora custom search

                # The following lists are used to create the final output CSV file
                result_summary_list = []
                result_summarized_url_list = []
                result_model_name_list = []
                result_query_list = []
                result_text_to_summarize_list = []

                # If not already created, create the output directory where all the data will be stored
                project_data_path = os.path.join(data_path, st.session_state.new_project_name)
                mkdir_p(project_data_path)

                # Upload the data
                with open(os.path.join(project_data_path, query_list_filename), "wb") as query_file:
                    query_file.write(st_query_list.getbuffer())

                st.success("**Starting the *Query* workflow.**")
                st.success("If you provided an email address, the results will be mailed to you. "
                           "Otherwise, they'll be stored under the provided project name for you to download.")

                # Read the query from the newly created CSV file
                df_queries = pd.read_csv(os.path.join(project_data_path, query_list_filename), usecols=[0])

                if not df_queries.empty:  # At least one query is needed to run

                    for index, row in df_queries.iterrows():  # Loop 1: Process all the queries
                        # Pause every 10 requests
                        if search_request_count % 10 == 0 and search_request_count != 0:
                            write_response = write_result_to_file(result_query_list, result_summary_list,
                                                                  result_summarized_url_list,
                                                                  result_model_name_list,
                                                                  result_text_to_summarize_list,
                                                                  project_data_path, search_request_count)
                            st.write(
                                f"After {search_request_count} requests, let's pause for a while. {write_response}")
                            time.sleep(10)

                        # There are 3 steps for building the query
                        # Step 1: Get the text of the query
                        query_text = row[df_queries.columns[0]]  # The text of the query from the CSV file
                        # Step 2: Get the search engine with/without the site operator
                        if st.session_state.search_engine == 'Google':
                            final_query = query_text
                        else:
                            final_query = query_text + " site:{}".format(st.session_state.search_engine)
                        # Step 3: Exclude PDF files from the SERP
                        final_query = final_query + " -filetype:pdf"

                        # Send the request to Google
                        serp_results = get_serp_results(final_query, "com", 5, 0, st.session_state.search_number_url,
                                                        st.session_state.search_location,
                                                        st.session_state.search_language)
                        search_request_count += 1

                        if serp_results:  # Check if that SERP returns at least one URL
                            combined_graded_sentences = []  # Is specific for each query but common for multiple URLs

                            for serp_result in serp_results:  # Loop 2: Process all the SERP URLs
                                # Get the HTML content and then summarize
                                serp_details, clean_checked_sentences = from_url_to_html(serp_result, quora_flag,
                                                                                         st.session_state.grammar_check,
                                                                                         st.session_state.summary_model)
                                # serp_details is stores specific ordered information
                                result_query_list.append(query_text)
                                result_summary_list.append(serp_details[0])
                                result_summarized_url_list.append(serp_details[1])
                                result_model_name_list.append(serp_details[2])
                                result_text_to_summarize_list.append(serp_details[3])

                                combined_graded_sentences.append(clean_checked_sentences)

                            # Summarize the content of multiple URLs
                            if len(serp_results) > 1:
                                combined_clean_graded_sentences = ' '.join(combined_graded_sentences)
                                combined_clean_graded_sentences = combined_clean_graded_sentences.strip()
                                # Summarize the combined sentences and store them
                                if combined_clean_graded_sentences:
                                    full_summary_result = summarize(combined_clean_graded_sentences,
                                                                    st.session_state.summary_model)
                                else:
                                    full_summary_result = 'I am sorry. I am afraid I cannot answer it.'
                                result_query_list.append(query_text)
                                result_summary_list.append(full_summary_result)
                                result_summarized_url_list.append('Combined SERP URLs')
                                result_model_name_list.append(st.session_state.summary_model)
                                result_text_to_summarize_list.append(combined_clean_graded_sentences[:800])
                        else:
                            st.error('SERP is empty.')

                    write_response = write_result_to_file(result_query_list, result_summary_list,
                                                          result_summarized_url_list,
                                                          result_model_name_list, result_text_to_summarize_list,
                                                          project_data_path)
                    st.success(write_response)
                else:
                    st.error('CSV file is empty.')

                # Prepare the files to be downloaded
                zip_files = ['serp_summary.csv']  # , 'summarized_serp.xlsx']
                zip_and_download(project_data_path, zip_files)
                st.success("Workflow successfully finished. Project name: {}".format(project_data_path.split('/')[-1]))

                if st_pwd and st_destination_email:
                    st.write("Sending an email.")
                    try:
                        if validate_email_format():
                            send_email(st_pwd, project_data_path, st_destination_email, zip_files)
                            st.write("Email sent.")
                        else:
                            st.warning("Email not sent.")
                    except:
                        st.error("Error while sending the email.")

            # This is the URL flow section
            elif st_workflow_type == 'URL':
                # The following lists are used to create the final output CSV file
                result_summary_list = []
                result_summarized_url_list = []
                result_model_name_list = []
                result_query_list = []
                result_text_to_summarize_list = []

                st.write('-------------------')
                st.success("**Starting the *URL* workflow.**")

                serp_details, clean_checked_sentences = from_url_to_html(st_user_input_url, -1,
                                                                         st.session_state.grammar_check,
                                                                         st.session_state.summary_model)
                result_query_list.append('URL entry')
                result_summary_list.append(serp_details[0])
                result_summarized_url_list.append(serp_details[1])
                result_model_name_list.append(serp_details[2])
                result_text_to_summarize_list.append(serp_details[3])
                # For the URL flow, display the result on the screen
                display_result(serp_details[0], st.session_state.summary_model)

            # This is the Text flow section
            else:
                checked_sentences = []
                if st.session_state.grammar_check == 'Yes':
                    checked_sentences = check_grammar(st_user_input_text)
                else:
                    st.warning('Skipping sentence quality check.')
                    checked_sentences.append(st_user_input_text)

                clean_checked_sentences = ' '.join(checked_sentences)
                clean_checked_sentences = clean_checked_sentences.strip()
                # Start summarization of the clean sentences
                summary_result = summarize(clean_checked_sentences, st.session_state.summary_model)
                # For the Text flow, display the result on the screen
                display_result(summary_result, st.session_state.summary_model)

    elif tabs == 'Data':
        col1, col2 = st.columns(2)
        project_folder = os.path.join(data_path, st.session_state.create_select_project)

        if button_list_files:
            filelist = []
            for root, dirs, files in os.walk(project_folder):
                for file in files:
                    filename = os.path.join(root, file)
                    filelist.append(filename.split('/')[-1])
            if not filelist:
                col1.warning("The selected directory is empty.")
            else:
                col1.write(filelist)

        if button_download_folder:
            filelist = []
            for root, dirs, files in os.walk(project_folder):
                for file in files:
                    filename = os.path.join(root, file)
                    if filename.split('.')[-1] in ['csv', 'xlsx']:
                        filelist.append(filename.split('/')[-1])

            if not filelist:
                st.warning("No file to download.")
            else:
                zip_and_download(project_folder + "/", filelist)

        if button_clean_folder:
            st.warning(delete_files(project_folder))

        if button_delete_folder:
            if os.path.isdir(project_folder):
                st.warning(delete_files(project_folder))

                try:
                    col1.warning("Removing the project folder.")
                    os.rmdir(project_folder)
                except OSError as e:
                    col1.error("Error: %s : %s" % (project_folder, e.strerror))
            else:
                st.warning(f"No directory to delete. {project_folder} not found.")

    elif tabs == 'Advanced Settings':
        col1, col2 = st.columns(2)

        if button_clear_cache:
            st.runtime.legacy_caching.clear_cache()
            st.experimental_memo.clear()
            st.experimental_singleton.clear()
            col1.success("Cache cleared.")


if __name__ == "__main__":
    main()
