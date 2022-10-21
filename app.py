import os
import pandas as pd
import streamlit as st
from st_on_hover_tabs import on_hover_tabs
from utils import load_css
from utils import mkdir_p, delete_files, list_directories, delete_folder
from utils import list_project_files, display_result
from utils import prepare_email, validate_email_format
from utils import download_data, zip_and_download
from utils import check_grammar
from utils import summarize_url, loop_and_summarize
from models import summarize_text

st.set_page_config(layout="wide")
st.sidebar.image("img/fav-ico.png", width=50)
load_css("style.css")

data_path = "./data/"  # Path where all the data will be stored
query_list_filename = 'queries.csv'  # Default name of the uploaded CSV file


# os.environ['TOKENIZERS_PARALLELISM'] = "true"


# Session state section
def create_or_select():
    if st.session_state.selected_project == "Create a new project":
        st.session_state.create_select_project = 'create'
    else:
        st.session_state.create_select_project = st.session_state.selected_project


if 'create_select_project' not in st.session_state:
    st.session_state.create_select_project = 'select'
if 'new_project_name' not in st.session_state:
    st.session_state.new_project_name = 'default_project'
if 'summary_model_id' not in st.session_state:
    st.session_state.summary_model_id = 1
if 'grammar_check_id' not in st.session_state:
    st.session_state.grammar_check_id = 0
if 'custom_search_id' not in st.session_state:
    st.session_state.custom_search_id = 1
if 'search_engine' not in st.session_state:
    st.session_state.search_engine = 'quora.com'
if 'count_urls' not in st.session_state:
    st.session_state.count_urls = 2
if 'search_language_id' not in st.session_state:
    st.session_state.search_language_id = 0
if 'search_country_id' not in st.session_state:
    st.session_state.search_country_id = 0
if 'show_email_field' not in st.session_state:
    st.session_state.send_results = False

# Streamlit UI
with st.sidebar:
    tabs = on_hover_tabs(tabName=['Dashboard', 'Search', 'Data', 'Advanced Settings'],
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

# Options to populate widgets on the UI
grammar_check_options = ('Yes', 'No')
summarizer_options = ('T5-base', 'Roberta-med', 'Long-T5', 'Pegasus-xsum', 'German', 'Italian')
language_options = ("en", "it", "de", "nl", "pt", "es", "fr")
country_options = ("US", "GB", "AU", "IN", "CA", "IT", "DE", "NL", "BE", "PT", "BR", "ES", "FR")

st.title('Search & Summarize')

if tabs == 'Dashboard':
    col1, col2 = st.columns(2)

    # The available workflows
    st_workflow_type = col1.radio('⚝ Workflows', ["Summarize a text", "Create FAQ"], index=0, key='workflow')

    if st_workflow_type == 'Summarize a text':
        st_workflow_subtype = col1.radio('📜 Summarize a text from a long text, from a URL or by using the SERP',
                                         ["SERP", "URL", "Long text"], index=0)
    else:
        st_workflow_subtype = 'not_valid_flow'

    # Options specific to each flow.
    if (st_workflow_type == 'Create FAQ') or (st_workflow_subtype == 'SERP'):
        # Create the default folder if it doesn't exist and return the list of existing directories
        mkdir_p(data_path + "default_project")
        dir_list = list_directories(data_path)
        if not dir_list:
            st.warning("No folder found.")
            st.stop()
        else:
            sorted_list = sorted(dir_list)
            sorted_list.insert(0, "Create a new project")

            # Create the directory where the project's data is stored
            existing_folder = col1.selectbox('🗄️ Project name', sorted_list, index=1,
                                             on_change=create_or_select, key="selected_project")
            # Show/Hide the field to create a new project. Otherwise, select an existing one.
            if st.session_state.create_select_project == 'create':
                st.session_state.new_project_name = col1.text_input('📁 Create a new project ⬇️',
                                                                    help="Project name to download the data.")
            else:
                st.session_state.new_project_name = existing_folder

        st_pwd = 'xxx'  # todo this needs to be pushed as a secret key st.secrets["pwd"] not as text_input('App key:')
        # Show/Hide email address based on the user's choice to receive a notification email at the end of the workflow
        st.session_state.send_results = col1.checkbox('✉️Send me the results', key="show_email_field")
        if st.session_state.send_results:
            st_destination_email = col1.text_input('Email address', value="email@address.com", key='input_email',
                                                   on_change=validate_email_format)
        # The upload option appears only when a user wants to create an FAQ
        if st_workflow_type == 'Create FAQ':
            st_query_list = col1.file_uploader('Upload the list of queries (CSV file)')
        else:  # The user provides the query on the front-end
            st_query = col1.text_input('Provide your search query', 'Can you wear blue light glasses all day?')
    # UI elements when the Long text radio box is selected
    elif st_workflow_type == 'Summarize a text':
        if st_workflow_subtype == 'Long text':
            with open(os.path.join(data_path, 'sample.txt'), "r") as f:
                sample_lines = f.readlines()
            st_user_input_text = col1.text_area("Enter the text to summarize", sample_lines[0], height=300)
        elif st_workflow_subtype == 'URL':
            st_user_input_url = col1.text_input("Enter a URL to scrape and summarize",
                                                'https://www.medicalrecords.com/health-a-to-z/ayurveda-special',
                                                key="input_url")
        else:
            col1.error("No such workflow subtype.")
    else:
        st.error("No such workflow type.")

    st.markdown(
        """<style>
            button:first-child {
                padding: 20px 50px 20px 50px;
                margin: 30px auto 0;
                padding-left: 40px;
                padding-right: 40px;
            }
            </style>""", unsafe_allow_html=True,
    )
    button_start_flow = col1.button("Summarize", key="button_start")

elif tabs == 'Search':
    col1, col2, col3 = st.columns(3)
    col1.header('Search options')
    st.session_state.count_urls = col1.slider('Number of URLs to analyse', 1, 5, st.session_state.count_urls,
                                              help="The number of top ranking URLs on Google to summarize.")

    index_target_language = col1.selectbox("Select language", range(len(language_options)),
                                           index=st.session_state.search_language_id,
                                           format_func=lambda x: language_options[x])
    st.session_state.search_language_id = index_target_language

    index_target_geo = col1.selectbox("Select country", range(len(country_options)),
                                      index=st.session_state.search_country_id,
                                      format_func=lambda x: country_options[x])
    st.session_state.search_country_id = index_target_geo

    custom_search_options = ('Yes', 'No')
    index_custom_search = col1.selectbox('Custom search:', range(len(custom_search_options)),
                                         index=st.session_state.custom_search_id,
                                         format_func=lambda x: custom_search_options[x])
    st.session_state.custom_search_id = index_custom_search

    if st.session_state.custom_search_id == 0:
        st.session_state.search_engine = col1.text_input("Value for the site operator:", st.session_state.search_engine,
                                                         help="site:example.com")
elif tabs == 'Data':
    col1, col2 = st.columns(2)
    col1.header('🗄️ Data')
    col1.markdown(
        f'<div style="font-size:24px; color:#FF0000">Current project name is: <b>{st.session_state.new_project_name}</b></div><br />',
        unsafe_allow_html=True)
    col1.subheader('List the files of the selected project')
    button_list_files = col1.button("List files")
    col1.subheader('Download the data of the selected project')
    button_download_folder = col1.button("Download data")
    col1.subheader('⚠️**Danger zone**')
    col1.subheader("Delete the files of the selected project")
    button_clean_folder = col1.button("Delete files")
    col1.subheader("Delete the data and the project folder")
    button_delete_folder = col1.button("Delete project")

elif tabs == 'Advanced Settings':
    col1, col2, col3 = st.columns(3)
    col1.header('⚙️Advanced settings')
    index_summary_model = col1.selectbox('Available summarizers', range(len(summarizer_options)),
                                         index=st.session_state.summary_model_id,
                                         format_func=lambda x: summarizer_options[x])
    st.session_state.summary_model_id = index_summary_model

    index_grammar_check = col1.selectbox('Enable grammar check', range(len(grammar_check_options)),
                                         index=st.session_state.grammar_check_id,
                                         format_func=lambda x: grammar_check_options[x])
    st.session_state.grammar_check_id = index_grammar_check

    col1.subheader("🧹 Cache files")
    button_clear_cache = col1.button("Clear the cache")


def main():
    print("Starting..")

    if tabs == 'Dashboard':
        if button_start_flow:

            # The starting point is a single query (UI) or multiple queries (CSV file)
            if (st_workflow_type == 'Create FAQ') or (st_workflow_subtype == 'SERP'):
                if st.session_state.create_select_project == 'create':
                    if len(st.session_state.new_project_name) > 0:
                        pass
                    else:
                        st.error("Please provide a name to your new project in order to proceed.")
                        st.stop()

                # If not already created, create the output directory where all the data will be stored
                project_data_path = os.path.join(data_path, st.session_state.new_project_name)
                mkdir_p(project_data_path)

                # Create a df with the single query so that both workflows share the same code
                if st_workflow_subtype == 'SERP':
                    df_queries = pd.DataFrame(data=[st_query], columns=['query'])
                    df_queries.to_csv(os.path.join(project_data_path, query_list_filename), index=False)
                else:
                    # Upload the data
                    with open(os.path.join(project_data_path, query_list_filename), "wb") as query_file:
                        query_file.write(st_query_list.getbuffer())

                st.success("**Starting the workflow.**")
                # Read the query from the newly created/uploaded CSV file
                df_queries = pd.read_csv(os.path.join(project_data_path, query_list_filename), usecols=[0])

                if not df_queries.empty:  # At least one query is needed to run
                    summary_message = loop_and_summarize(df_queries, project_data_path,
                                                         summarizer_options[st.session_state.summary_model_id],
                                                         grammar_check_options[st.session_state.grammar_check_id],
                                                         country_options[st.session_state.search_country_id],
                                                         language_options[st.session_state.search_language_id],
                                                         st.session_state.search_engine,
                                                         st.session_state.custom_search_id,
                                                         st.session_state.count_urls
                                                         )
                    st.markdown(f'**{summary_message}**')

                    # Prepare the files to be downloaded
                    zip_files = ['serp_summary.csv']  # , 'summarized_serp.xlsx']
                    zip_and_download(project_data_path, zip_files)
                    st.success(
                        "Workflow successfully finished. Project name: {}".format(project_data_path.split('/')[-1]))
                    if st.session_state.send_results:
                        st.write("Sending an email.")
                        email_message = prepare_email(st_pwd, st_destination_email, project_data_path, zip_files)
                        st.markdown(f'{email_message}')
                else:
                    st.error('CSV file is empty.')

            # Summarize one URL or one long text
            elif st_workflow_type == "Summarize a text":
                if st_workflow_subtype == 'URL':
                    st.success("**Starting the *URL* workflow.**")
                    summarization_details, single_url_sentences = summarize_url(st_user_input_url, -1,
                                                                                grammar_check_options[
                                                                                    st.session_state.grammar_check_id],
                                                                                summarizer_options[
                                                                                    st.session_state.summary_model_id])
                    # For the URL flow, display the result on the screen
                    display_result(summarization_details[0], summarizer_options[st.session_state.summary_model_id])
                elif st_workflow_subtype == 'Long text':
                    checked_sentences = []
                    if grammar_check_options[st.session_state.grammar_check_id] == 'Yes':
                        checked_sentences = check_grammar(st_user_input_text)
                    else:
                        st.warning('Skipping sentence quality check.')
                        checked_sentences.append(st_user_input_text)

                    single_url_sentences = ' '.join(checked_sentences)
                    single_url_sentences = single_url_sentences.strip()
                    # Start summarization of the clean sentences
                    summary_result = summarize_text(single_url_sentences,
                                                    summarizer_options[st.session_state.summary_model_id])
                    # For the Text flow, display the result on the screen
                    display_result(summary_result, summarizer_options[st.session_state.summary_model_id])

    elif tabs == 'Data':
        col1, col2 = st.columns(2)
        project_folder = os.path.join(data_path, st.session_state.new_project_name)

        if button_list_files:
            st.markdown(list_project_files(project_folder))

        if button_download_folder:
            download_data(project_folder)

        if button_clean_folder:
            st.warning(delete_files(project_folder))

        if button_delete_folder:
            st.warning(delete_folder(project_folder))

    elif tabs == 'Advanced Settings':
        col1, col2 = st.columns(2)

        if button_clear_cache:
            st.runtime.legacy_caching.clear_cache()
            st.experimental_memo.clear()
            st.experimental_singleton.clear()
            col1.success("Cache cleared.")


if __name__ == "__main__":
    main()
