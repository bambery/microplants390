#from microplants import process_inputs as pi
from microplants import build_reports as br
from microplants import generate_reports as gr

#pi.attach_subject_data_special()
#pi.create_and_export_all_reports()
#cdt = pi.create_classifications()

br.build_reports()

subjects = br.subjects
uids = br.uids
classifications = br.classifications
unique_images = br.unique_images

#subjects_expert = gr.all_subjects_with_expert(uids, subjects)

uids_classifications = gr.all_classifications_by_uid(uids, subjects, classifications)


breakpoint()
