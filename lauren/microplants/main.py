from microplants import process_inputs as pi

#pi.create_and_export_all_reports()
cdt = pi.create_classifications()
'''
worried = {}
uhoh={}
count_gender = 0
for classification_id, data in cdt['repro'].items():
#    breakpoint()
    if data['classification'] in [2, 3, 4]: 
        count_gender +=1
        total_boxes = len(data['boxes']['male']) + len(data['boxes']['female'])
        if( total_boxes == 0): 
            worried[classification_id] = data
            if(data['expert_classified'] == True):
                uhoh[classification_id] = data
                '''
