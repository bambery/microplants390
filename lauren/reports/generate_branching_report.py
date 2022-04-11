import os
import csv
import pandas as pd
import json
import copy
import re
import ast
import time

data_sources_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "inputs" ))
output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "generated_reports" ))

# header for classification files
# 0: classification_id, 1: user_name, 2:user_id, 3:user_ip, 4: workflow_id, 5: workflow_name, 6: workflow_version, 
# 7: created_at, 8: gold_standard, 9: expert, 10: metadata, 11: annotations, 12: subject_data, 13: subject_ids
expert_data_file = "MattvonKonrat-stem-and-branching-patterns-classifications.csv"
classifications_public = "stem-and-branching-patterns-classifications-1.28-2.1.csv"

# header for subjects
# 0: subject_id, 1: project_id, 2: workflow_id, 3: subject_set_id, 4: metadata, 5: locations, 
# 6: classifications_count, 7: retired_at, 8: retirement_reason, 9: created_at, 10: updated_at

subjects_data = "unfolding-of-microplant-mysteries-subjects.csv"

new_report_name = "branching-report_"
timestamp = time.strftime('%b-%d-%Y_%H-%M', time.localtime()) 
new_report_extension = ".csv"


# a dictionary whose key is the subject
classifications = { "Not Sure":0, "Regular (Structured)":1, 
        "Irregular (Random)":2 }

# create a reverse lookup for display purposes
reverse_classifications = { v: k for k, v in classifications.items() }
#print(reverse_classifications)
report = {}

# process expert ratings
expert_classifications_file = os.path.abspath(os.path.join(data_sources_dir, expert_data_file))

with open( expert_classifications_file, "r", newline='') as file:
    reader = csv.reader(file, delimiter=",")
    header = next(reader)
    for row in reader:
        rating = json.loads( row[11].strip('[]') ).get('value')
        report[ int(row[13]) ] = {
                "expert_classification": classifications.get(rating),
                "expert_user_id": int(row[2]),
                "workflow_id": int(row[4]),
                "expert_classified_at": row[7],
                "subject_filename": json.loads( row[12] ).get( row[13] ).get("Filename"),
                # initialize counts for the 3 classifications
                "public_counts": {0:0, 1:0, 2:0},
                "public_classification_ids": { 0:[], 1:[], 2:[] }
                }

# header for subjects_data file - currently only used to grab the subject's image url
# 0: subject_id, 1: project_id, 2: workflow_id, 3: subject_set_id, 4: metadata, 5: locations, 
# 6: classifications_count, 7: retired_at, 8: retirement_reason, 9: created_at, 10: updated_at

subjects_file = os.path.abspath(os.path.join(data_sources_dir, subjects_data))
# attach the image url for each subject
with open(subjects_file, "r", newline='') as file:
    reader = csv.reader(file, delimiter=",")
    header = next(reader)
    for row in reader:
        subject_id = int(row[0]) 
        locations = ast.literal_eval(row[5])
        if subject_id in report: # subjects file contains many test subjects that were not used in classification
            #breakpoint()
            report[subject_id]["image_url"] = locations['0']

###################################
# count public classifications
###################################
public_classifications_file = os.path.abspath(os.path.join(data_sources_dir, classifications_public))
with open( public_classifications_file, "r", newline='') as file:
    reader = csv.reader(file, delimiter=",")
    header = next(reader)
    for row in reader:
        # not all rows have an expert classification
        subject_id = int(row[13])
        if subject_id in report:
            rating = json.loads( row[11].strip('[]') ).get('value')
            # increment the count for this rating
            curr_class = classifications.get(rating)
            classification_id = row[0]
            report[ subject_id ]["public_counts"][curr_class] += 1 
            report[ subject_id ]["public_classification_ids"].get(curr_class).append(classification_id)

## making it pretty
for subject, sub in report.items():
    total_classifications = 0
    for classification, count in sub["public_counts"].items():
            total_classifications += count
    correct_answers = sub["public_counts"][sub["expert_classification"]] 
    sub["percent_match"] = round(correct_answers/total_classifications * 100, 2)
    sub["percent_sure"] = round( (sub["public_counts"][1] + sub["public_counts"][2]) / total_classifications * 100, 2 )
    sub["percent_not_sure"] = round( sub["public_counts"][0] / total_classifications * 100, 2)
    sub["total_classifications"] = total_classifications
    sub["total_not_sure"] = sub["public_counts"][0]
    sub["total_regular"] = sub["public_counts"][1]
    sub["total_irregular"] = sub["public_counts"][2]
    #
    sub["ids_not_sure"] = sub["public_classification_ids"][0]
    sub["ids_regular"] = sub["public_classification_ids"][1]
    sub["ids_irregular"] = sub["public_classification_ids"][2]
 

    ##### this is all for making a nice report #######
    # display classifications nicely
    public_keys = list(sub["public_counts"].keys())
    for key in public_keys:
        sub["public_counts"][ reverse_classifications[key] ] = sub["public_counts"].pop(key)
    #sub["public_counts"][ reverse_classifications[key] ] = sub["public_counts"].pop(key)
    sub["expert_classification"] = reverse_classifications[ sub["expert_classification"] ]

# rearrange display order of columns
# https://stackoverflow.com/questions/41968732/set-order-of-columns-in-pandas-dataframe

display = pd.DataFrame.from_dict(report, orient='index')
display_order = ['expert_classification', 
        'total_classifications', 
        'public_counts', 
        'percent_match', 
        'percent_sure', 
        'percent_not_sure',
        'total_not_sure',
        'ids_not_sure',
        'total_regular',
        'ids_regular',
        'total_irregular',
        'ids_irregular'] 
new_order = display_order + (display.columns.drop(display_order).tolist())
display = display[new_order]
new_generated_report = os.path.abspath(os.path.join( output_dir, (new_report_name + timestamp + new_report_extension) ))
display.to_csv(new_generated_report)
