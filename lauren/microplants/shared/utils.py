import os
from pathlib import Path

workflow_id_branch  = 19282
workflow_id_repro   = 19279

def get_project_root() -> Path:
    return Path(__file__).parent.parent

def get_resource_dir() -> Path:
    root = get_project_root()
    inputs = root.parent.parent.joinpath("inputs")
    return inputs 

# Matt - "mvonkonrat" - 675706
# drtcam - 1910812
# Heaven - "wade_h1" - 2317803
expert_user_ids = [675706, 1910812, 2317803]

#workflow_classifications = {
#        workflow_id_branch: { "NOT SURE":0, "REGULAR":1, "IRREGULAR": 2, "NO BRANCH": 3 },
#        workflow_id_repro: { "NOT SURE":0, "STERILE":1, "FEMALE":2, "MALE": 3, "BOTH": 4 }
#        }
#
#branch_classifications = { "NOT SURE":0, "REGULAR":1, "IRREGULAR": 2, "NO BRANCH": 3 }
#repro_classifications = { "NOT SURE":0, "STERILE":1, 
#        "FEMALE":2, "MALE": 3, "BOTH": 4 }
#
#branch_reverse_classifications = { v: k for k, v in branch_classifications.items() }
#repro_reverse_classifications = { v: k for k, v in repro_classifications.items() }
#
wf_config = {
    'counts_template': {
        workflow_id_branch: { 0:0, 1:0, 2:0, 3:0 },
        workflow_id_repro: { 0:0, 1:0, 2:0, 3:0, 4:0 }
        },
    'ids_template': { 
        workflow_id_branch: { 0:[], 1:[], 2:[], 3:[] },
        workflow_id_repro: { 0:[], 1:[], 2:[], 3:[], 4:[]}
        },
    'classifications': {
        workflow_id_branch: { "NOT SURE":0, "REGULAR":1, "IRREGULAR": 2, "NO BRANCH": 3 },
        workflow_id_repro: { "NOT SURE":0, "STERILE":1, "FEMALE":2, "MALE": 3, "BOTH": 4 }
        },
    'reverse_classifications': {
        workflow_id_branch: { 0:"NOT SURE", 1:"REGULAR", 2:"IRREGULAR", 3:"NO BRANCH" },
        workflow_id_repro: { 0:"NOT SURE", 1:"STERILE", 2:"FEMALE", 3:"MALE", 4:"BOTH" }
        }
    }

# Here are all of the ways this has been classified over time (note extra whitespace at end):
#### branch classification text
# "Irregular (Random)", "Irregular", "Random (Irregular)"
# "Structured", "Structured (Feather)", "Regular ", "Regular (Structured)"
# "Not sure ", "No sure"
# "No Branching"
#### repro classification text
# "Both Female and Male", "Both"
# "Not Sure"
# "Male"
# "Female ", "Female"
# "Sterile ", "Sterile"
# note that the order of the reproductive classifications is important to make sure the correct one is captured
def normalize_name(name):

    normal = name.upper().strip()
    if 'IRREGULAR' in normal:
        return "IRREGULAR"     
    elif 'NO' in normal and 'SURE' in normal:
        return 'NOT SURE'
    elif 'REGULAR' in normal or 'STRUCTURED' in normal:
        return 'REGULAR'
    elif 'NO' in normal and 'BRANCH' in normal:
        return 'NO BRANCH'
    elif 'STERILE' in normal:
        return 'STERILE'
    elif 'FEMALE AND MALE' in normal or 'BOTH' in normal:
        return 'BOTH'
    elif 'FEMALE' in normal:
        return 'FEMALE'
    elif 'MALE' in normal:
        return 'MALE'
    else:
        raise Exception("Unknown classification: " + normal)
