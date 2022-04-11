import os
import csv
# note: I did not document at the time why json.loads ended up failing my needs here, something about force casting things to strings to get at the innards and ast.literal_eval ended up being less work. 
# note 2: generally want to avoid anything with "eval" in the name, but these inputs have zero user generated input and thus are safe to consume
import ast
import pathlib as Path

from shared import utils

data_sources_dir = utils.get_resource_dir() 
output_dir = utils.get_project_root().joinpath("generated_reports")

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
classifications_public_file = "stem-and-branching-patterns-classifications-1.28-2.1.csv"

workflow_id_branch  = "19282"
workflow_id_repro   = "19279"

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
#   expert_classifications_file: Path object to expert classifications file
#   report type: string of either "repro" or "branch"
# returns:
#   dict object representing the beginning of the report to be generated

def process_expert_classifications( report_type ):
    if report_type == "branch":
        expert_file = data_sources_dir.joinpath(expert_branch_file) 
        classifications = branch_classifications
    else:
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
            else: 
                # initialize counts for the 4 reproductive classifications
                report[ subject_id ]["public_counts"] = {0:0, 1:0, 2:0, 3:0, 4:0},
                    # collect the classification ids for each individual classification 
                report[subject_id]["public_classification_ids"] ={ 0:[], 1:[], 2:[], 3:[], 4:[] }
    return report

# method: processes the subjects file to add data not contained in the other files: i
#   this case, only the url for the images is being added
# inputs: 
#   report_type: string of either "branch", "repro", or "both"
#   reports: List containing the partly assembled reports as specified by report_type
# returns: List containing the modified reports

def attach_subject_data( report_type, reports ):
    subjects_path = data_sources_dir.joinpath(subjects_file)
    with open(subjects_path, "r", newline='') as file:
        reader = csv.reader(file, delimiter=",")
        header = next(reader)
        for row in reader:
            # note: subject_ids are unique across all workflows in zooniverse
            subject_id = int(row[0]) 
            locations = ast.literal_eval(row[5])
            if subject_id in report: # subjects file contains many test subjects that were not used in classification
                #breakpoint()
                report[subject_id]["image_url"] = locations['0']





def generate_csv():
    new_report_name = "branching-report_"
    timestamp = time.strftime('%b-%d-%Y_%H-%M', time.localtime()) 
    new_report_extension = ".csv"
