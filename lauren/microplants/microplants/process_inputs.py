# generally want to avoid anything with "eval" in the name, but these inputs have zero user generated input and thus are safe to consume. The reports are not given in json and it fails on some fields, so ast.literal_eval is selected over json.loads
import ast
import os
import pandas as pd
import pathlib as Path
import time

# csv processing
import csv
import openpyxl
import xlsxwriter

# local imports
from shared import utils

data_sources_dir = utils.get_resource_dir() 
output_dir = utils.get_project_root().parent.joinpath("generated_reports")

# header for subjects
# 0: subject_id, 1: project_id, 2: workflow_id, 3: subject_set_id, 4: metadata, 5: locations, 
# 6: classifications_count, 7: retired_at, 8: retirement_reason, 9: created_at, 10: updated_at
subjects_file = "unfolding-of-microplant-mysteries-subjects.csv"

special_file = "101841and103857.csv"

# header for classification files
# the expert classifications were given to us in two files
# 0: classification_id, 1: user_name, 2:user_id, 3:user_ip, 4: workflow_id, 5: workflow_name, 6: workflow_version, 
# 7: created_at, 8: gold_standard, 9: expert, 10: metadata, 11: annotations, 12: subject_data, 13: subject_ids
expert_branch_file  = "MattvonKonrat-stem-and-branching-patterns-classifications.csv"
expert_repro_file   = "MattvonKonrat-determining-the-reproductive-structure-of-a-liverwort-classifications.csv"
classifications_public_file = "unfolding-of-microplant-mysteries-classifications.csv"

workflow_id_branch  = 19282
workflow_id_repro   = 19279

# Matt - "mvonkonrat" - 675706
# drtcam - 1910812
# Heaven - "wade_h1" - 2317803
expert_user_ids: [675706, 1910812, 2317803]

# deciding to consume all workflow versions due to configuration not resetting classified counts when version changes
# workflow_version_branch = "17.51"
# workflow_version_repro = "87.147"

# encoding classifications in case the strings change
# note that "Not Sure" is capitalized
branch_classifications = { "Not Sure":0, "Regular (Structured)":1, 
        "Irregular (Random)":2, "No Branching":3 }
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
            subject_filename = ast.literal_eval(row[12].replace('null', 'None'))
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
                "subject_filename": subject_filename[str(subject_id)]['Filename'] 
            }
            # each workflow has different classifications 
            if report_type == "branch":
                # initialize counts for the 3 branch classifications
                report[ subject_id ]["public_counts"] = {0:0, 1:0, 2:0, 3:0}
                # collect the classification ids for each individual classification 
                report[subject_id]["public_classification_ids"] = { 0:[], 1:[], 2:[], 3:[] }
            elif report_type == "repro": 
                # initialize counts for the 4 reproductive classifications
                report[ subject_id ]["public_counts"] = {0:0, 1:0, 2:0, 3:0, 4:0}
                # collect the classification ids for each individual classification 
                report[subject_id]["public_classification_ids"] ={ 0:[], 1:[], 2:[], 3:[], 4:[] }
    return report

# method: processes the subjects file to add data not contained in the other files
#   - real clickable uploaded url for the images is being added
#   - subject_set_id
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
            subject_set_id = int(row[3])
            img_url = ast.literal_eval(row[5])
            # subjects file contains many test subjects that were not used in classification
            if subject_id in reports[0]: 
                reports[0][subject_id]["image_url"] = img_url['0']
                reports[0][subject_id]["subject_set_id"] = subject_set_id
            if subject_id in reports[1]:
                reports[1][subject_id]["image_url"] = img_url['0']
                reports[1][subject_id]["subject_set_id"] = subject_set_id
    return reports

def attach_subject_data_special():
    special_path = data_sources_dir.joinpath(special_file)
    special={ 101841:[], 103857:[] }
    with open(special_path, "r", newline='') as file:
        reader = csv.reader(file, delimiter=",")
        header = next(reader)
#        special[101841].append(header)
#        special[103857].append(header)
        for row in reader:
            my_row = row
            # note: subject_ids are unique across all workflows in zooniverse
            subject_id = int(row[0]) 
            subject_set_id = int(row[3])
            img_url = ast.literal_eval(row[5])
            old_file_name= ast.literal_eval(row[4])["Filename"]
            # subjects file contains many test subjects that were not used in classification
            my_row[5] = img_url['0']
            my_row[4] = old_file_name

            if subject_set_id == 101841:
                special[101841].append(my_row)
            elif subject_set_id == 103857:
                special[103857].append(my_row)

    dfreports = {}
    dfreports[101841] = pd.DataFrame(special[101841], columns=header)
    dfreports[103857] = pd.DataFrame(special[103857], columns=header)

    new_report_name = "101841_and_103857-reports_"
    timestamp = time.strftime('%b-%d-%Y_%H-%M', time.localtime()) 
    new_report_extension = ".xlsx"
    new_generated_report = output_dir.joinpath(new_report_name + timestamp + new_report_extension) 

    # https://www.easytweaks.com/pandas-save-to-excel-mutiple-sheets/
    Excelwriter = pd.ExcelWriter(new_generated_report, engine="xlsxwriter")
    for report_type, df in dfreports.items():
        df.to_excel(Excelwriter, sheet_name=str(report_type), index=False)
    Excelwriter.save()

    return special

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
# the following must be true for this function to work:
#       - "T0" MUST have a "value" attr which corresponds to the *classification*, ie "Sterile", "Female". note: if this is the only task on a repro, (ie len(attr==1)) then the classification is either sterile or not sure
#       - "T3" refers to a "male" classification and contains the boxes 
#       - "T4" is both
#       - "T5" is "female" 

# workflow_version_repro = 87.147
# workflow_version_branch = 17.51

def all_public_classifications(reports):
    #grab all expert classifications:

    public_file = data_sources_dir.joinpath(classifications_public_file) 
    with open(public_file, "r", newline='') as file:

        public = {}

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

                # not filtering by workflow version right now
                #if workflow_version != workflow_version_branch:
                #    continue # pass on earlier versions of workflows

                # note: wf is set here
                wf = public["branch"] 
                classifications = branch_classifications
                if subject_id in reports[0]:
                    expert_classified = True
            elif(workflow_id == workflow_id_repro):

                #if workflow_version != workflow_version_repro:
                #    continue # pass on earlier versions of workflows
                
                # note: wf is set here
                wf = public["repro"]
                classifications = repro_classifications
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
# TODO: make fxn accept 2 or more reports at a time
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
            data["total_no_branching"] = data["public_counts"][3]
            #
            data["ids_not_sure"] = data["public_classification_ids"][0]
            data["ids_regular"] = data["public_classification_ids"][1]
            data["ids_irregular"] = data["public_classification_ids"][2]
            data["ids_no_branching"] = data["public_classification_ids"][3]
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
        public_classification_ids = list(data["public_classification_ids"].keys())
        for key in public_classification_ids:
            data["public_classification_ids"][ reverse_classifications[key] ] = data["public_classification_ids"].pop(key)
        data["expert_classification"] = reverse_classifications[ data["expert_classification"] ]
    return report

# input: dict with report names as keys, dataframe reports as vals 
def prepare_for_export(for_display):
    # not sure how to name the index col on creation, adding second
    for report_type, dfreport in for_display.items():
        dfreport.index.names=['subject_id']
        if report_type == "branch":
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
        elif report_type == "repro":
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
                'ids_both'] # rearrange display order of columns
        # https://stackoverflow.com/questions/41968732/set-order-of-columns-in-pandas-dataframe
        new_order = display_order + (dfreport.columns.drop(display_order).tolist())
        dfreport = dfreport[new_order]
    return for_display 

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
    return mine

# write csvs to the file system
# TODO: update input to be dict not arr
def export_all_reports(reports):
    dfreports = {}
    reports[0] = beautify("branch", reports[0])
    dfreports["branch"] = pd.DataFrame.from_dict(reports[0], orient='index')

    reports[1] = beautify("repro", reports[1])
    dfreports["repro"] = pd.DataFrame.from_dict(reports[1], orient='index')

    dfreports = prepare_for_export(dfreports)
    # this is where the reports are added as sheets
    # replacing the following:
    #generate_export("branch", display)

    # convert to list for processing
    new_report_name = "microplants-reports_"
    timestamp = time.strftime('%b-%d-%Y_%H-%M', time.localtime()) 
    new_report_extension = ".xlsx"
    new_generated_report = output_dir.joinpath(new_report_name + timestamp + new_report_extension) 

    # https://www.easytweaks.com/pandas-save-to-excel-mutiple-sheets/
    Excelwriter = pd.ExcelWriter(new_generated_report, engine="xlsxwriter")
    for report_type, df in dfreports.items():
        df.to_excel(Excelwriter, sheet_name=report_type, index=False)
    Excelwriter.save()

# this is the big kahuna that does it all
def create_and_export_all_reports():
    reports = create_all_reports()
    export_all_reports( reports )
