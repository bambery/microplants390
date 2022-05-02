from collections import Counter
from copy import deepcopy

# local imports
from shared import utils

def all_subjects_with_expert(uids, subjects):
    # 2 lists, by workflow, of subjects with experts
    sub_expert = [] 
    for uid, vals in uids.items():
        if (len(vals['expert_classifications'][utils.workflow_id_branch]) + len(vals['expert_classifications'][utils.workflow_id_repro]) > 0):
            sub_expert = list(set(vals['subject_ids'] + sub_expert))

    return sub_expert

def has_expert(vals, workflow_id):
    return( len( vals['expert_classifications'][workflow_id] ) > 0 )

# returns a dict with: 
#   uid:
#       branch_wf_id:
#           classification_id: list of classifications
def all_classifications_by_uid(uids, subjects, classifications):
    branch = utils.workflow_id_branch
    repro = utils.workflow_id_repro

    report_types = [branch, repro]

    uids_classifications = {}

    this_class = {}

    for uid, vals in uids.items():
        for report_type in report_types:
            class_ids = {}
            this_class[report_type] = deepcopy(utils.wf_config['ids_template'][report_type]) 

            for subject_id in vals['subject_ids']:
                class_ids = subjects[subject_id]['class_ids'][report_type]
                for class_id_sub, classifications_sub in class_ids.items():
                    this_class[report_type][class_id_sub] += classifications_sub
        uids_classifications[uid] = deepcopy(this_class)
    return uids_classifications
