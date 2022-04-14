# generally want to avoid anything with "eval" in the name, but these inputs have zero user generated input and thus are safe to consume. The reports are not given in json and it fails on some fields, so ast.literal_eval is selected over json.loads
import ast
import csv
import os
# why am I using pandas? I'm only using it to rearrange columns and write to csv, is this necessary?
import pandas as pd
import pathlib as Path
import time

from shared import utils

data_sources_dir = utils.get_resource_dir() 
output_dir = utils.get_project_root().parent.joinpath("generated_reports")

# header for subjects
# 0: subject_id, 1: project_id, 2: workflow_id, 3: subject_set_id, 4: metadata, 5: locations, 
# 6: classifications_count, 7: retired_at, 8: retirement_reason, 9: created_at, 10: updated_at
subjects_file = "unfolding-of-microplant-mysteries-subjects.csv"

# header for classification files
# the expert classifications were given to us in two files
# 0: classification_id, 1: user_name, 2:user_id, 3:user_ip, 4: workflow_id, 5: workflow_name, 6: workflow_version, 
# 7: created_at, 8: gold_standard, 9: expert, 10: metadata, 11: annotations, 12: subject_data, 13: subject_ids
expert_branch_file  = "MattvonKonrat-stem-and-branching-patterns-classifications.csv"
expert_repro_file   = "MattvonKonrat-determining-the-reproductive-structure-of-a-liverwort-classifications.csv"
classifications_public_file = "unfolding-of-microplant-mysteries-classifications.csv"

workflow_id_branch  = 19282
workflow_id_repro   = 19279

# will need to handle these as lists if mult versions for one WF need to be considered
workflow_version_branch = "17.51"
workflow_version_repro = "87.147"

# encoding classifications in case the strings change
# note that "Not Sure" is capitalized
branch_classifications = { "Not Sure":0, "Regular (Structured)":1, 
        "Irregular (Random)":2 }
# create a reverse lookup for display purposes
branch_reverse_classifications = { v: k for k, v in branch_classifications.items() }

# note that "Not sure" does not capitalize "sure"
# note that "Female " has a SPACE at the end of the string 
repro_classifications = { "Not sure":0, "Sterile":1, 
        "Female ":2, "Male": 3, "Both Female and Male": 4 }
# create a reverse lookup for display purposes
repro_reverse_classifications = { v: k for k, v in repro_classifications.items() }
# method: process expert classifications and outputs the initial report
# inputs:
#   report type: string of either "repro" or "branch"
# returns:
#   dict object representing the beginning of the report to be generated

def process_expert_classifications( report_type ):
    if report_type == "branch":
        expert_file = data_sources_dir.joinpath(expert_branch_file) 
        classifications = branch_classifications
    elif report_type == "repro":
        expert_file = data_sources_dir.joinpath(expert_repro_file) 
        classifications = repro_classifications
    
    report = {}
    with open( expert_file, "r", newline='') as file:
        reader = csv.reader(file, delimiter=",")
        header = next(reader)
        for row in reader:
            rating = ast.literal_eval(row[11])[0].get("value") # turns string into a list of dicts 
            subject_id = int(row[13])
            # both reports share many fields
            report[ subject_id ] = {
                # grab & encode expert classification
                "expert_classification": classifications.get(rating),
                # grab the classification id for this expert classification
                "expert_classification_id": row[0],
                # grab Matt's user id
                "expert_user_id": int(row[2]),
                # grab the worklfow id for clarity
                "workflow_id": int(row[4]),
                # grab the timestamp of the completed classification 
                "expert_classified_at": row[7],
                # in case we ever see value in trying to dedup, this is the original uploaded filename, the only possibility we have for identifying dupes 
                "subject_filename": ast.literal_eval(row[12].replace('null', 'None')) 
            }
            # each workflow has different classifications 
            if report_type == "branch":
                # initialize counts for the 3 branch classifications
                report[ subject_id ]["public_counts"] = {0:0, 1:0, 2:0}
                # collect the classification ids for each individual classification 
                report[subject_id]["public_classification_ids"] = { 0:[], 1:[], 2:[] }
            elif report_type == "repro": 
                # initialize counts for the 4 reproductive classifications
                report[ subject_id ]["public_counts"] = {0:0, 1:0, 2:0, 3:0, 4:0}
                # collect the classification ids for each individual classification 
                report[subject_id]["public_classification_ids"] ={ 0:[], 1:[], 2:[], 3:[], 4:[] }
    return report

# method: processes the subjects file to add data not contained in the other files: in
#   this case, only the url for the images is being added
# inputs: 
#   reports: List containing BOTH reports is required 
# NOTE: it will probably soon be "all 3 reports"
# returns: List containing the modified reports

def attach_subject_data( reports ):
    if len(reports) < 2:
        raise Exception("nah girl u must send me at least 2 reports, 1: branch 2: repro")
    subjects_path = data_sources_dir.joinpath(subjects_file)
    with open(subjects_path, "r", newline='') as file:
        reader = csv.reader(file, delimiter=",")
        header = next(reader)
        for row in reader:
            # note: subject_ids are unique across all workflows in zooniverse
            subject_id = int(row[0]) 
            img_url = ast.literal_eval(row[5])
            # subjects file contains many test subjects that were not used in classification
            if subject_id in reports[0]: 
                reports[0][subject_id]["image_url"] = img_url['0']
            if subject_id in reports[1]:
                reports[1][subject_id]["image_url"] = img_url['0']
    return reports

# method: for each expertly classified subject_id, attach how the public classified the same item 
def count_public_classifications( reports ):
    public_file = data_sources_dir.joinpath(classifications_public_file) 
    with open(public_file, "r", newline='') as file:
        reader = csv.reader(file, delimiter=",")
        header = next(reader)
        for row in reader:
            # not all rows have an expert classification
            subject_id = int(row[13])
            workflow_id = int(row[4])

            if (workflow_id == workflow_id_branch) and (subject_id in reports[0]):  
                report = reports[0]
                classifications = branch_classifications
            elif(workflow_id == workflow_id_repro):
                classifications = repro_classifications
                if len(reports) == 1 and subject_id in reports[0]:
                    report = reports[0]
                elif subject_id in reports[1]:
                    report = reports[1]
                else:
                    continue # not interested in this one
            else: 
                continue # pass on this classification
            rating = ast.literal_eval(row[11])[0].get("value")
            # increment the count for this rating
            curr_class = classifications.get(rating)
            classification_id = row[0]
            report[ subject_id ]["public_counts"][curr_class] += 1 
            report[ subject_id ]["public_classification_ids"].get(curr_class).append(classification_id)
    return reports 

# generate two reports: all classifications for branch, all classifications for reproduction
# classifications : dict with 2 keys, "branch" and "repro"
#   report: dict
#       keys: classification ids 
#       values: classification object for this subject
# HELLO FUN NEWS: the workflow_version is NOW IMPORTANT. classifications from versions prior to 
# the ones selected here ask different questions in a different order   
# the following must be true for this function to work:
#       - "T0" MUST have a "value" attr which corresponds to the *classification*, ie "Sterile", "Female". note: if this is the only task on a repro, (ie len(attr==1)) then the classification is either sterile or not sure
#       - "T3" refers to a "male" classification and contains the boxes 
#       - "T4" is both
#       - "T5" is "female" 

# workflow_version_repro = 87.147
# workflow_version_branch = 17.51

def all_public_classifications(reports):
    public_file = data_sources_dir.joinpath(classifications_public_file) 
    with open(public_file, "r", newline='') as file:

        public = { "branch": {}, "repro":{} }

        reader = csv.reader(file, delimiter=",")
        header = next(reader)

        for row in reader:
            expert_classified = False

            workflow_id = int(row[4]) 
            workflow_version = row[6] # keeping it a string, death to floats
            subject_id = int(row[13])
            classification_id = int(row[0])
            user_name = row[1]

            # set vars for each workflow type
            if (workflow_id == workflow_id_branch):
                #TODO: here she is, fix her
                if workflow_version != workflow_version_branch:
                    continue # pass on earlier versions of workflows
                # note: wf is set here
                wf = public["branch"] 
                classifications = branch_classifications
                if subject_id in reports[0]:
                    expert_classified = True
            elif(workflow_id == workflow_id_repro):
                #TODO here she is again, needs to be not in [list of versions]
                if workflow_version != workflow_version_repro:
                    continue # pass on earlier versions of workflows
                classifications = repro_classifications
                # note: wf is set here
                wf = public["repro"]
                if subject_id in reports[1]:
                    expert_classified = True
            else: 
                continue # dunno what to do with a mystery workflow id, so skip

            wf[classification_id] ={
                "subject_id": subject_id,
                "workflow_id": workflow_id,
                "expert_classified": expert_classified
                }

            # This is the proper place to collect and process additional "tasks" that get thrown into 
            # annotations. I am doing the minimum for our needs. 
            annotations = ast.literal_eval(row[11])
            for task in annotations:
                task_id = task["task"]
                value = task["value"]

                if task_id == 'T0':
                    wf[classification_id]['classification'] = classifications.get(value)
                elif task_id in ['T3', 'T4', 'T5']: # no clue why genders have different tasks, these are repro boxes
                    box_list = value
                    boxes = { "male": [], "female":[] }
                    for box in box_list:
                        new_box = {} 
                        if box['tool_label'] == 'Female Identifier ': # note mystery ending whitespace
                            my_list = boxes["female"]
                        else:
                            my_list = boxes['male']
                        new_box['x'] = box['x']
                        new_box['y'] = box['y']
                        new_box['width'] = box['width']
                        new_box['height'] = box['height']

                        my_list.append(new_box)

                    # if someone has submitted a gender classification without boxes, drop them
                    if ( len(boxes["male"]) == 0 ) and ( len(boxes["female"]) == 0 ):
                        continue
                    wf[classification_id]['boxes'] = boxes

            # keeping the number of attr the same for both workflows for now
            if 'boxes' not in wf[classification_id]:
                wf[classification_id]['boxes'] = {}

            if user_name.startswith("not-logged-in"):
                wf[classification_id]['logged_in'] = False
                wf[classification_id]['user_id'] = 0
            else:
                wf[classification_id]['logged_in'] = True
                wf[classification_id]['user_id'] = int(row[2])

    return public 

# Now that we are done adding new data to the report, we can do some calculations and 
# also make the labels readable
# pull out the label beautification into a separate helper
def beautify( report_type, report ):
    for subject, data in report.items():
        total_classifications = 0
        for classification, count in data["public_counts"].items():
            total_classifications += count
        correct_answers = data["public_counts"][data["expert_classification"]] 
        data["percent_match"] = round(correct_answers/total_classifications * 100, 2)
        data["percent_sure"] = round( (data["public_counts"][1] + data["public_counts"][2]) / total_classifications * 100, 2 )
        data["percent_not_sure"] = round( data["public_counts"][0] / total_classifications * 100, 2)
        data["total_classifications"] = total_classifications

        if report_type == "branch":
            reverse_classifications = branch_reverse_classifications

            data["total_not_sure"] = data["public_counts"][0]
            data["total_regular"] = data["public_counts"][1]
            data["total_irregular"] = data["public_counts"][2]
            #
            data["ids_not_sure"] = data["public_classification_ids"][0]
            data["ids_regular"] = data["public_classification_ids"][1]
            data["ids_irregular"] = data["public_classification_ids"][2]
        elif report_type == "repro":
            reverse_classifications = repro_reverse_classifications

            data["total_not_sure"] = data["public_counts"][0]
            data["total_sterile"] = data["public_counts"][1]
            data["total_female"] = data["public_counts"][2]
            data["total_male"] = data["public_counts"][3]
            data["total_both"] = data["public_counts"][4]
            #
            data["ids_not_sure"] = data["public_classification_ids"][0]
            data["ids_sterile"] = data["public_classification_ids"][1]
            data["ids_female"] = data["public_classification_ids"][2]
            data["ids_male"] = data["public_classification_ids"][3]
            data["ids_both"] = data["public_classification_ids"][4]

        public_keys = list(data["public_counts"].keys())
        for key in public_keys:
            data["public_counts"][ reverse_classifications[key] ] = data["public_counts"].pop(key)
        data["expert_classification"] = reverse_classifications[ data["expert_classification"] ]
    return report

# perform branch specific processing for report for external consumption 
def generate_branch_report(display=[]):
    # not sure how to name the index col on creation, adding second
    display.index.names=['subject_id']
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
    # rearrange display order of columns
    # https://stackoverflow.com/questions/41968732/set-order-of-columns-in-pandas-dataframe
    new_order = display_order + (display.columns.drop(display_order).tolist())
    display = display[new_order]
    generate_csv("branch", display)
    return display

# perform repro-specific processing for making the report nice
def generate_repro_report(display=[]):
    # not sure how to name the index col on creation, adding second
    display.index.names=['subject_id']
    display_order = ['expert_classification', 
        'total_classifications', 
        'public_counts', 
        'percent_match', 
        'percent_sure', 
        'percent_not_sure', 
        'total_not_sure', 
        'ids_not_sure', 
        'total_sterile', 
        'ids_sterile',
        'total_female', 
        'ids_female',
        'total_male', 
        'ids_male',
        'total_both',
        'ids_both'] 
    # rearrange display order of columns
    # https://stackoverflow.com/questions/41968732/set-order-of-columns-in-pandas-dataframe
    new_order = display_order + (display.columns.drop(display_order).tolist())
    display = display[new_order]
    generate_csv("repro", display)
    return display

# actually generates csv report on file system
def generate_csv(report_type, df):
    new_report_name = report_type + "-report_"
    timestamp = time.strftime('%b-%d-%Y_%H-%M', time.localtime()) 
    new_report_extension = ".csv"

    new_generated_report = output_dir.joinpath(new_report_name + timestamp + new_report_extension) 
    df.to_csv(new_generated_report)

# generates reports before preparation for printing (used for data processing)
def create_all_reports():
    reports = []
    reports.append( process_expert_classifications("branch") )
    reports.append( process_expert_classifications("repro") )
    reports = attach_subject_data(reports)
    reports = count_public_classifications(reports)
    return reports

# creates classification report - currently being done separately
def create_classifications():
    reports = []
    reports.append( process_expert_classifications("branch") )
    reports.append( process_expert_classifications("repro") )
    reports = attach_subject_data(reports)
    mine = all_public_classifications(reports)
    breakpoint()
    return mine

# write csvs to the file system
def export_all_reports(reports):
    reports[0] = beautify("branch", reports[0])
    reports[0] = pd.DataFrame.from_dict(reports[0], orient='index')

    reports[1] = beautify("repro", reports[1])
    reports[1] = pd.DataFrame.from_dict(reports[1], orient='index')

    generate_branch_report(reports[0])
    generate_repro_report(reports[1])

# this is the big kahuna that does it all
def create_and_export_all_reports():
    reports = create_all_reports()
    export_all_reports( reports )
