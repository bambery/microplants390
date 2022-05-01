import ast
import os
import pandas as pd
import pathlib as Path
import time

#csv processing
import csv

from shared import utils

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


def process_subjects():
    # note: the same subject_id can appear multiple times in this file. There are at least 100 duplicate subject_ids

    subjects_path = data_sources_dir.joinpath(subjects_file)

    subjects = {}
    unique_images = { }
    uid_tracker = 0

    with open(subjects_path, "r", newline='') as file:
        reader = csv.reader(file, delimiter=",")
        header = next(reader)
        for row in reader:
            subject_id = int(row[0])
            orig_img_name = ast.literal_eval(row[4])['Filename']
            img_url = ast.literal_eval(row[5])['0']

            cleaned_name = orig_img_name.lstrip("Copy of ")

            if cleaned_name in unique_images: # if image is dupe
                curr = unique_images[cleaned_name]
                img_id = curr['uid']
                if subject_id not in curr['subject_ids']:
                    curr['subject_ids'].append(subject_id)
            else: # add new entry
                uid_tracker+=1
                img_id = uid_tracker
                unique_images[cleaned_name] = {
                        'subject_ids': [subject_id],
                        'uid': img_id,
                        'img_url': img_url
                }

            if subject_id not in subjects:
                subjects[subject_id] = { 'uid': img_id }

    # reindex unique_images to use the uid as index and call it uids
    uids = {}
    for key, val in unique_images.items():
        uids[val['uid']] = {
            'img_url': val['img_url'],
            'img_name': key,
            'subject_ids': val['subject_ids'],
            'expert_classifications': []
        }
        
    return subjects, unique_images, uids

def process_classifications(subjects, uids):

    def process_tasks(tasks, task_classifications):
        for task in tasks:
            task_id = task["task"]
            boxes = {}
            # desperately trying to extract consistent data that has been very inconsistently labeled.
            if task_id == 'T0':
                try:
                    value = utils.normalize_name( task["value"] )
                except:
                    # skip the one null classification (and any future ones)
                    null_classifications.append(classification_id)
                    continue

                value = utils.normalize_name( task["value"] )
                classification = task_classifications.get(value)  

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
                        return 0, 0 # an error - drop this record
                    new_box['x'] = box['x']
                    new_box['y'] = box['y']
                    new_box['width'] = box['width']
                    new_box['height'] = box['height']

                    my_list.append(new_box)

                # if someone has submitted a gender classification without boxes, drop them
                if ( len(boxes["male"]) == 0 ) and ( len(boxes["female"]) == 0 ):
                    return 0, 0 # an error - drop this record

        return boxes, classification 

    public_file = data_sources_dir.joinpath(classifications_public_file) 
    experts = utils.expert_user_ids
    all_classifications = {}

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
            classification_id = int(row[0])
            user_name = row[1]
            workflow_id = int(row[4])
            annotations = row[11]
            subject_id = int(row[13])
            test_subject = None
            

            
            if subject_id in subjects:
                test_subject = subjects[subject_id]
                uid = test_subject['uid']
            # we have some missing subjects - throw out these classifications
            else:
                missing_subjects.append(subject_id)
                continue
            
            logged_in = not user_name.startswith("not-logged-in")

            if logged_in:
                user_id = int(row[2])
            else:
                user_id = 0

            if user_id in experts:
                expert = True
                uids[uid]['expert_classifications'].append(classification_id)
            else:
                expert = False

            if workflow_id == utils.workflow_id_branch:
                task_classifications = utils.branch_classifications
            elif workflow_id == utils.workflow_id_repro:
                task_classifications = utils.repro_classifications
            else:
                continue # not handling other workflows right now


            annotations = annotations.replace('null', 'None')
            annotations = ast.literal_eval(annotations)
            boxes, classification = process_tasks(annotations, task_classifications)

            if not (boxes and classification):
                continue # something was wrong with this entry

            all_classifications[classification_id] = {
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

    return all_classifications


def build_reports():
    subjects, unique_images, uids = process_subjects()

    #classifications, process_classifications
    all_classifications = process_classifications(subjects, uids) 

    breakpoint()
    # do something
    return 1
