import os
import time
import pandas as pd
from argparse import ArgumentParser
from utils import write_result_to_file, send_email
from utils import get_serp_results, get_html_from_urls
from utils import evaluate_sentence_quality
from utils import summarize, zip_and_download
from utils import clean_html_with_trafilatura


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--destination_email', default='email@XXX.com', type=str, required=False)
    parser.add_argument('--perform_sentence_quality', default=True, type=str)
    parser.add_argument('--project_data_path', default='./data/', type=str, required=False)
    parser.add_argument('--pwd', default='pwd', type=str, required=False)
    parser.add_argument('--search_engine', default='Google', type=str)
    parser.add_argument('--source_entry', default='Query', type=str, required=False)
    parser.add_argument('--summary_model', default='English-T5', type=str, required=False)
    parser.add_argument('--target_geo', default='US', type=str)
    parser.add_argument('--target_language', default='en', type=str)
    parser.add_argument('--top_serp_count', default='1', type=int)
    parser.add_argument('--user_input_url', default='url_flow', type=str, required=False)

    args = parser.parse_args()

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

    summary_models = [args.summary_model]
    # For the Query and URL options, read the query from the newly created CSV file
    df_queries = pd.read_csv(os.path.join(args.project_data_path, query_list_filename))

    if not df_queries.empty:
        for index, row in df_queries.iterrows():
            # Pause every 10 Google search requests
            if search_request_count % 10 == 0 and search_request_count != 0:
                write_response = write_result_to_file(result_query_list, result_summary_list,
                                                      result_summarized_url_list,
                                                      result_model_name_list, result_text_to_summarize_list,
                                                      args.project_data_path, search_request_count)
                print(f"Pausing for a while: {write_response}")
                time.sleep(10)

            query_text = row[df_queries.columns[0]]

            if args.source_entry == 'Query':
                if args.search_engine == 'Google':
                    final_query = query_text
                else:
                    final_query = query_text + " site:{}".format(args.search_engine)

                final_query = final_query + " -filetype:pdf"

                # Request the top URLs from Google
                print(f'args.top_serp_count {args.top_serp_count}')
                serp_result_list = get_serp_results(final_query, "com", 5, 0, args.top_serp_count,
                                                    args.target_geo, args.target_language)
                search_request_count += 1

            else:  # Only process the URL given by the user as part of the URL flow
                serp_result_list = [args.user_input_url]

            combined_graded_sentences = []
            if serp_result_list:
                for serp_result_page in serp_result_list:  # Loop items in results

                    # Scrapes the HTML content of a given URL
                    response_body = get_html_from_urls(serp_result_page, quora_flag)

                    # Retrieving the content property from the json object
                    if (not response_body) or (response_body == "Connection Error"):
                        if args.source_entry == 'Query':
                            result_query_list.append(final_query)
                        else:
                            result_query_list.append('UI entry')

                        result_summary_list.append("Connection Error")
                        result_summarized_url_list.append(serp_result_page)
                        result_model_name_list.append("Connection Error")
                        result_text_to_summarize_list.append("Connection Error")
                    else:
                        trafilatura_body = clean_html_with_trafilatura(response_body)
                        # st.warning('trafilatura processed')
                        # In some cases, the scraper returns: Something went wrong. Wait a moment and try again.
                        # Remove it and keep the last try
                        response_wait_message = 'Something went wrong. Wait a moment and try again.'
                        if response_wait_message in trafilatura_body:
                            trafilatura_body = trafilatura_body.split(response_wait_message)[-1][1:]

                        trafilatura_body = trafilatura_body.replace('\n', ' ')

                        if args.perform_sentence_quality == 'Yes':
                            graded_sentences = evaluate_sentence_quality(trafilatura_body)
                        else:
                            graded_sentences.append(trafilatura_body)

                        clean_graded_sentences = ' '.join(graded_sentences)
                        clean_graded_sentences = clean_graded_sentences.strip()

                        combined_graded_sentences.append(clean_graded_sentences)

                        for summary_model in summary_models:
                            summary_result = summarize(clean_graded_sentences, summary_model,
                                                       default_min_summary_length, default_max_summary_length)

                            result_query_list.append(query_text)
                            result_summary_list.append(summary_result)
                            result_summarized_url_list.append(serp_result_page)
                            result_model_name_list.append(summary_model)
                            result_text_to_summarize_list.append(clean_graded_sentences[:800])

                # Summarize the content of multiple URLs
                if (len(serp_result_list) > 1) and (args.source_entry == 'Query'):
                    combined_clean_graded_sentences = ' '.join(combined_graded_sentences)
                    combined_clean_graded_sentences = combined_clean_graded_sentences.strip()

                    for summary_model in summary_models:
                        full_summary_result = summarize(combined_clean_graded_sentences, summary_model,
                                                        default_min_summary_length, default_max_summary_length)

                        result_query_list.append(query_text)
                        result_summary_list.append(full_summary_result)
                        result_summarized_url_list.append('Combined SERP URLs')
                        result_model_name_list.append(summary_model)
                        result_text_to_summarize_list.append(combined_clean_graded_sentences[:800])
            else:
                print("SERP empty")
    else:
        pass

    print(result_summarized_url_list)

    if args.source_entry == 'Query':
        write_response = write_result_to_file(result_query_list, result_summary_list,
                                              result_summarized_url_list,
                                              result_model_name_list, result_text_to_summarize_list,
                                              args.project_data_path)

        print("##################################")
        print(f"project {args.project_data_path}")
        print("##################################")

        # Prepare the files to be downloaded
        zip_files = ['serp_summary.csv']  # , 'summarized_serp.xlsx']
        zip_and_download(args.project_data_path, zip_files)
        print("Workflow successfully finished. Project name: {}".format(args.project_data_path.split('/')[-1]))

        if args.pwd and args.destination_email:
            print("Sending an email.")
            send_email(args.pwd, args.project_data_path, args.destination_email, zip_files)
            print("Email sent.")

        print("Workflow done!")

    return result_summary_list


def main():
    x = parse_args()
    x = " ".join(x).replace("\n", " ")
    print(f"{x}")


if __name__ == "__main__":
    main()