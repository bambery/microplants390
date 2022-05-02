# things this script depends on:

task numbers refer to this trello (task numbers are not visible by default, blame trello):
https://trello.com/b/fe3WnMFG/microplants

These mappings can be updated in the normalize_name function

1. tool_labels for box drawing must contain the words "male" or "female" - if the tool is missing either of these labels, the classification will be ignored

2. the classification display names for branching are something like the following (captialization does not matter):

IRREGULAR: must contain the phrase "irregular" in some form

REGULAR: must contain either the phrase "regular" or the phrase "structured" in some form

NO BRANCH: must contain the phrase "no branch" in some form, "no branching" will also count, but the check is the exact sequence of characters "no branch"

NOT SURE: must contain the phrase "not sure" in some form

3. The classification display names for reproduction must be something like the following (capitalization does not matter)

STERILE: must have the phrase "sterile"

FEMALE: must have the phrase "female"

MALE: must have the phrase "male"

FEMALE AND MALE: either the phrase "female and male" or the phrase "both"

NOT SURE: must contain the phrase "not sure" in some form

When these mappings are changed, the old mappings are NOT updated. If a classification is created with the title "Male " and the classification name gets updated to remove the whitespace and become "Male", the old classification continues to have the classification of "Male "
