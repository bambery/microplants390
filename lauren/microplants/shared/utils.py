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

# Here are all of the ways this has been classified over time (note extra whitespace at end):
# "Irregular (Random)", "Irregular", "Random (Irregular)"
# "Structured", "Structured (Feather)", "Regular ", "Regular (Structured)"
# "Not sure ", "No sure"
# "No Branching"
branch_classifications = { "NOT SURE":0, "REGULAR":1, "IRREGULAR": 2, "NO BRANCH": 3 }
# create a reverse lookup for display purposes
branch_reverse_classifications = { v: k for k, v in branch_classifications.items() }

# "Both Female and Male", "Both"
# "Not Sure"
# "Male"
# "Female ", "Female"
# "Sterile ", "Sterile"
repro_classifications = { "NOT SURE":0, "STERILE":1, 
        "FEMALE":2, "MALE": 3, "BOTH": 4 }
# create a reverse lookup for display purposes
repro_reverse_classifications = { v: k for k, v in repro_classifications.items() }

report_names = {"BRANCH": 0, "REPRO": 1}
report_names_reverse = { v: k for k, v in report_names.items() }

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
        return 'NO BRANCHING'
    elif 'STERILE' in normal:
        return 'STERILE'
    elif 'FEMALE AND MALE' in normal or 'BOTH' in normal:
        return 'BOTH'
    elif 'FEMALE' in normal:
        return 'FEMALE'
    elif 'MALE' in normal:
        return 'MALE'
    else:
        # something to check for if this is blowing up
        return 0
