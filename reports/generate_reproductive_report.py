import os
import csv
import pandas as pd
import json # for parsing strings into dicts
import re # for regex, for the filenames
import ast # for parsing strings into lists - may also do dicts, may not need json package 
import bisect # for sorting list of classification ids
import time # for timestamping filenames

data_sources_dir = "./inputs/"
output_dir = "./generated_reports/"

# header for classification files
# 0: classification_id, 1: user_name, 2:user_id, 3:user_ip, 4: workflow_id, 5: workflow_name, 6: workflow_version, 
# 7: created_at, 8: gold_standard, 9: expert, 10: metadata, 11: annotations, 12: subject_data, 13: subject_ids
expert_data_file = "expert-reproductive-classifications.csv"
#classifications_public = "public-reproductive-classifications-1.28-2.1.csv"
#that file does not have enough classifications
classifications_public = "unfolding-of-microplant-mysteries-classifications-3-22-22.csv"
#ALSO NOTE: the subject ids are NOT UNIQUE to each project - they repeat
wf_reproductive_id = 19279 # this is the id for reproductive project

new_report_name = "reproductive-report_"
timestamp = time.strftime('%b-%d-%Y_%H-%M', time.localtime()) 
new_report_extension = ".csv"

# header for subjects
# 0: subject_id, 1: project_id, 2: workflow_id, 3: subject_set_id, 4: metadata, 5: locations, 
# 6: classifications_count, 7: retired_at, 8: retirement_reason, 9: created_at, 10: updated_at

subjects_data = "unfolding-of-microplant-mysteries-subjects.csv"


# a dictionary whose key is the subject
# NOTE that "Not sure" is capitalized as "Not Sure" in the branching files grrrrrrr
# NOTE that "Female " has a SPACE at the end of the string
classifications = { "Not sure":0, "Sterile":1, 
        "Female ":2, "Male": 3, "Both Female and Male": 4 }

# create a reverse lookup for display purposes
reverse_classifications = { v: k for k, v in classifications.items() }
#print(reverse_classifications)
report = {}

# process expert ratings

with open( data_sources_dir + expert_data_file, "r", newline='') as file:
    reader = csv.reader(file, delimiter=",")
    header = next(reader)
    for row in reader:
        #rating = json.loads( row[11].strip('[]') ).get('value')
        rating = ast.literal_eval(row[11]) # turns string into a list of dicts as desired - should consider using this instead of json.loads in other files
        report[ int(row[13]) ] = {
                "expert_classification": classifications.get(rating[0].get("value")),
                "expert_classification_id": row[0],
                "expert_user_id": int(row[2]),
                "workflow_id": int(row[4]),
                "expert_classified_at": row[7],
                "subject_filename": json.loads( row[12] ).get( row[13] ).get("Filename"),
                # initialize counts for the 3 classifications
                "public_counts": {0:0, 1:0, 2:0, 3:0, 4:0},
                "public_classification_ids": { 0:[], 1:[], 2:[], 3:[], 4:[] }
                }

# header for subjects_data file - currently only used to grab the subject's image url
# 0: subject_id, 1: project_id, 2: workflow_id, 3: subject_set_id, 4: metadata, 5: locations, 
# 6: classifications_count, 7: retired_at, 8: retirement_reason, 9: created_at, 10: updated_at

# attach the image url for each subject
#### IN PROGRESS, not functional ####
with open(data_sources_dir + subjects_data, "r", newline='') as file:
    pattern = 'ab*'
    #pattern = '\{"0":(.*)'
    #pattern = '\{"0":("https://panoptes-uploads-zooniverse.org/subject_location/*)'
    #pattern = '\{"0":("https://panoptes-uploads-zooniverse.org/subject_location/[a-z0-9-.]*)"}'
    reader = csv.reader(file, delimiter=",")
    header = next(reader)
    for row in reader:
        subject_id = row[0] 
        locations = row[5]
        regex = re.compile(pattern)
        result = regex.match( locations )
#        print(locations)

###################################
# count public classifications
###################################
with open( data_sources_dir + classifications_public, "r", newline='') as file:
    reader = csv.reader(file, delimiter=",")
    header = next(reader)
    tracker = 0
    print(tracker)
    for row in reader:
        # not all rows have an expert classification
        subject_id = int(row[13])
        workflow_id = int(row[4])
        if subject_id in report and workflow_id == wf_reproductive_id:
            rating = ast.literal_eval(row[11])[0].get("value")
            tracker = tracker+1
            print(tracker)
#            if(tracker == 22):
#                breakpoint()
            # increment the count for this rating
            curr_class = classifications.get(rating)
#            breakpoint()
            classification_id = row[0]
            report[ subject_id ]["public_counts"][curr_class] += 1 
#            breakpoint()
            report[ subject_id ]["public_classification_ids"].get(curr_class).append(classification_id)
        
print(report)
for subject, sub in report.items():
    total_classifications = 0
    for classification, count in sub["public_counts"].items():
            total_classifications += count
    correct_answers = sub["public_counts"][sub["expert_classification"]] 
    sub["percent_match"] = round(correct_answers/total_classifications * 100, 2)
    sub["percent_sure"] = round( (sub["public_counts"][1] + sub["public_counts"][2]) / total_classifications * 100, 2 )
    sub["percent_not_sure"] = round( sub["public_counts"][0] / total_classifications * 100, 2)
    sub["total_classifications"] = total_classifications
    sub["num_not_sure"] = sub["public_counts"][0]
#    sub["percent_not_sure"] = dd
    sub["num_sterile"] = sub["public_counts"][1]
    sub["num_female"] = sub["public_counts"][2]
    sub["num_male"] = sub["public_counts"][3]
    sub["num_both"] = sub["public_counts"][4]
    #
    sub["ids_not_sure"] = sub["public_classification_ids"][0]
    sub["ids_sterile"] = sub["public_classification_ids"][1]
    sub["ids_female"] = sub["public_classification_ids"][2]
    sub["ids_male"] = sub["public_classification_ids"][3]
    sub["ids_both"] = sub["public_classification_ids"][4]

    ##### this is all for making a nice report #######
    # display classifications nicely
    public_keys = list(sub["public_counts"].keys())
    for key in public_keys:
        sub["public_counts"][ reverse_classifications[key] ] = sub["public_counts"].pop(key)
    sub["expert_classification"] = reverse_classifications[ sub["expert_classification"] ]

    # need to pull this out into a fxn 

    # display classifications nicely
    public_keys = list(sub["public_classification_ids"].keys())
    for key in public_keys:
        sub["public_classification_ids"][ reverse_classifications[key] ] = sub["public_classification_ids"].pop(key)

# rearrange display order of columns
# https://stackoverflow.com/questions/41968732/set-order-of-columns-in-pandas-dataframe

display = pd.DataFrame.from_dict(report, orient='index')
# not sure how to name the index col on creation, adding second
display.index.names=['subject_id']
display_order = ['expert_classification', 
        'total_classifications', 
        'public_counts', 
        'percent_match', 
        'percent_sure', 
        'percent_not_sure', 
        'num_not_sure', 
        'ids_not_sure', 
        'num_sterile', 
        'ids_sterile',
        'num_female', 
        'ids_female',
        'num_male', 
        'ids_male',
        'num_both',
        'ids_both'] 
new_order = display_order + (display.columns.drop(display_order).tolist())
display = display[new_order]
print(display)
display.to_csv(output_dir + new_report_name + timestamp + new_report_extension)
