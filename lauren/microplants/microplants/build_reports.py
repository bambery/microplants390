import ast
import os
import pandas as pd
import pathlib as Path
import time
from copy import deepcopy

#csv processing
import csv

from shared import utils as utils

data_sources_dir = utils.get_resource_dir() 
output_dir = utils.get_project_root().parent.joinpath("generated_reports")

# header for subjects
# 0: subject_id, 1: project_id, 2: workflow_id, 3: subject_set_id, 4: metadata, 5: locations, 
# 6: classifications_count, 7: retired_at, 8: retirement_reason, 9: created_at, 10: updated_at
subjects_file = "unfolding-of-microplant-mysteries-subjects.csv"

# header for classification files
# 0: classification_id, 1: user_name, 2:user_id, 3:user_ip, 4: workflow_id, 5: workflow_name, 6: workflow_version, 
# 7: created_at, 8: gold_standard, 9: expert, 10: metadata, 11: annotations, 12: subject_data, 13: subject_ids
classifications_public_file = "unfolding-of-microplant-mysteries-classifications.csv"

# pulling out the structures everything uses, too difficult to pass everywhere
subjects = {}
classifications = {}
unique_images = {}
uids = {}
uid_tracker = 0

def add_or_update_img(raw_img_name, subject_id, img_url = None):
    global subjects, classifications, unique_images, uids, uid_tracker

    cleaned_name = raw_img_name.lstrip("Copy of ")

    if cleaned_name in unique_images: # if image is dupe
        curr = unique_images[cleaned_name]
        img_id = curr['uid']
        if subject_id not in curr['subject_ids']:
            curr['subject_ids'].append(subject_id)
            uids[img_id]['subject_ids'].append(subject_id)
    else: # add new entry in tables
        uid_tracker+=1
        img_id = uid_tracker
        unique_images[cleaned_name] = {
                'subject_ids': [subject_id],
                'uid': img_id
        }
        uids[img_id] = {
            'img_name': cleaned_name,
            'subject_ids': [subject_id],
            'expert_classifications': { 
                utils.workflow_id_branch: [], 
                utils.workflow_id_repro:[] 
                }
            }

        # if the subject has an entry in the subjects table, add the img link
        if img_url:
            unique_images[cleaned_name]['img_url']= img_url
            uids[img_id]['img_url'] = img_url
            
    # add lookup entry for subjects
    if subject_id not in subjects:
        subjects[subject_id] = {
                'uid': img_id,
                'class_counts': { 
                    utils.workflow_id_branch: deepcopy(utils.wf_config['counts_template'][utils.workflow_id_branch]),
                    utils.workflow_id_repro: deepcopy(utils.wf_config['counts_template'][utils.workflow_id_repro])
                    },
                'class_ids': {
                    utils.workflow_id_branch: deepcopy(utils.wf_config['ids_template'][utils.workflow_id_branch]),
                    utils.workflow_id_repro: deepcopy(utils.wf_config['ids_template'][utils.workflow_id_repro])
                    }
        }
        # if there is no link provided, we are creating this ourselves to make up for a missing subject
        if not img_url:
            subjects[subject_id]['user_added'] = True
        else:
            subjects[subject_id]['user_added'] = False 

    return img_id

def process_subjects():
    # note: the same subject_id can appear multiple times in this file. There are at least 100 duplicate subject_ids
    global subjects, unique_images, uids

    subjects_path = data_sources_dir.joinpath(subjects_file)

    with open(subjects_path, "r", newline='') as file:
        reader = csv.reader(file, delimiter=",")
        header = next(reader)
        for row in reader:
            subject_id = int(row[0])
            orig_img_name = ast.literal_eval(row[4])['Filename']
            img_url = ast.literal_eval(row[5])['0']

            add_or_update_img(orig_img_name, subject_id, img_url)

    return 

# I just can't make this method shorter or subdivide it any more without causing even more chaos
def process_classifications():

    global subjects, classifications, unique_images

    def process_tasks(tasks, task_classifications):
        classification = -1
        for task in tasks:
            task_id = task["task"]
            boxes = {}
            # desperately trying to extract consistent data that has been very inconsistently labeled.
            if task_id == 'T0':
                try:
                    value = utils.normalize_name( task["value"] )
                except:
                    # skip the one null classification (and any future ones)
                    return -1, -1

                value = utils.normalize_name( task["value"] )
                classification = task_classifications[value] 

            elif task_id in ['T3', 'T4', 'T5']: # these are repro boxes, the task name refers to the gender selection the user made
                box_list = task["value"]
                boxes = { "male": [], "female":[] }
                for box in box_list:
                    new_box = {} 
                    # female can be either "Female" or "Female Identifier "
                    if 'FEMALE' in box['tool_label'].upper(): # note mystery ending whitespace
                        my_list = boxes["female"]
                    # male can be either "Male" or "Male Identifier "
                    elif 'MALE' in box['tool_label'].upper():
                        my_list = boxes['male']
                    else:
                        # skip any classifications with deficient box metadata
                        mystery_labels.append( classification_id )
                        return -2, -2 # an error - drop this record
                    new_box['x'] = box['x']
                    new_box['y'] = box['y']
                    new_box['width'] = box['width']
                    new_box['height'] = box['height']

                    my_list.append(new_box)

                # if someone has submitted a gender classification without boxes, drop them
                if ( len(boxes["male"]) == 0 ) and ( len(boxes["female"]) == 0 ):
                    return -3, -3 # an error - drop this record

        return boxes, classification 

    public_file = data_sources_dir.joinpath(classifications_public_file) 
    experts = utils.expert_user_ids

    with open(public_file, "r", newline='') as file:
        i = 0
        # skip first 120 lines, they have unstable formatting
        while i < 121:
            i = i+1
            next(file)

        public = { "branch":{}, "repro": {} }

        # collecting for examination if it comes up again
        mystery_labels = []
        null_classifications = []
        missing_subjects = []

        reader = csv.reader(file, delimiter=",")
        header = next(reader)

        for row in reader:
            classification = None

            classification_id = int(row[0])
            user_name = row[1]
            workflow_id = int(row[4])
            annotations = row[11]
            subject_data = row[12]
            subject_id = int(row[13])
            test_subject = None

            if workflow_id not in [utils.workflow_id_branch, utils.workflow_id_repro]:
                continue # not handling misc workflows

            # grab data about subject
            if subject_id in subjects:
                test_subject = subjects[subject_id]
                uid = test_subject['uid']
            else:
                # if there is no matching entry for the classified subject_id,
                # construct partial subject: see task #29 for more details

                # keep a list of missing subject_ids
                if subject_id not in missing_subjects:
                    missing_subjects.append(subject_id)

                # often nulls in this field: need None
                subject_data = ast.literal_eval(subject_data.replace('null', 'None'))
                img_name = subject_data[str(subject_id)]["Filename"]
                uid = add_or_update_img(img_name, subject_id)
            
            # guess if user is logged in (nothing prevents a sneaky name)
            logged_in = not user_name.startswith("not-logged-in")

            # logged in users will have user ids
            if logged_in:
                user_id = int(row[2])
            else:
                user_id = 0

            # is this classification by one of our expert?
            if user_id in experts:
                expert = True
                uids[uid]['expert_classifications'][workflow_id].append(classification_id)
            else:
                expert = False

            # grab all boxes drawn for this classification
            annotations = annotations.replace('null', 'None')
            annotations = ast.literal_eval(annotations)
            task_classifications = utils.wf_config['classifications'][workflow_id]
            boxes, classification = process_tasks(annotations, task_classifications)

            if boxes == -1:
                null_classifications.append(classification_id)
                continue
            if boxes in [-2, -3]: 
                continue # something was wrong with this classification: drop it

            # if we made it this far, we have a quality classification
            classifications[classification_id] = {
                'uid': uid,
                'subject_id': subject_id,
                'workflow_id': workflow_id,
                'user_id': user_id,
                'user_name': user_name,
                'expert': expert,
                'logged_in': logged_in,
                'classification': classification,
                'boxes': boxes
                }

            
            subjects[subject_id]['class_counts'][workflow_id][classification] += 1
            subjects[subject_id]['class_ids'][workflow_id][classification].append(classification_id)

    return 


def build_reports():
    process_subjects()

    #classifications, process_classifications
    process_classifications() 

    breakpoint()
    # develop reports for display 
    return 1
