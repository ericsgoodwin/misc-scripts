""" This script backs up hosted feature layers to a local drive if they have been modified since the last backup date. 
It takes five inputs: the AGOL username/password, the location of the .json file storing the layer names and their last
modified dates, the path to the working directory, and the dictionary of layer names and urls to be backed up.

If this is the first time backing up files to the directory, and the .json does not yet exist,
the script will create the .json file. The .json file is the reference the script uses to check the previous date the
feature service was modified. You may add or remove feature services from the "fs_dict" variable.

The script will only check files in this dictionary. Feature services are backed up in .gdb format with the
following naming convention: [Layer Name]_[Modification Date Time]_[Download Date Time].gdb
They are organized into folders by the year the file was backed up, and subfolders for each layer name. 
e.g. .../2024/Points_of_Interest/Points_of_Interest_20231227_1406_20240112_1702.gdb
For the above example, the Points_of_Interest layer was last modified on Dec 27, 2023 at 2:06 p.m. and the script
downloaded it on Jan 12, 2024 at 5:02 p.m.

IMPORTANT: This script relies on creating replicas. If the creation of replicas is not permitted on a feature service,
the script will fail for that service.
Please ensure replicas can be created in the "capabilities" property of the feature service.
"""

import os
import time
import datetime
import arcgis
from arcgis.gis import GIS
from arcgis.features import FeatureLayer
import zipfile
import json
import logging


# Please provide ArcGIS Online credentials
username = "xxxxxxx"
password = "xxxxxxx"

# Please provide the location of the JSON backup logging file that already exists (or that will be created)
last_modified_file = r'D:\working_temp\NHT\Scripts\AGOL_Backup_Folder\last_modified.json'

# Please provide the location of the folder the backups will be placed
workspace_path = r'D:\working_temp\NHT\Scripts\AGOL_Backup_Folder'

# Please check the dictionary below to verify the feature services you want to check for changes and backup.
# Layer names are set by the user, but they should not be modified once backups have been made.
# Elements may be added or removed at any time.  
fs_dict = {"Points_of_Interest" : "https://services1.arcgis.com/2exN3kG1f2h7coIQ/arcgis/rest/services/Points_of_Interest/FeatureServer",
            "nps_boundary" : "https://services1.arcgis.com/2exN3kG1f2h7coIQ/arcgis/rest/services/nps_boundary/FeatureServer",
            "elte_nht_100k_line": "https://services1.arcgis.com/2exN3kG1f2h7coIQ/arcgis/rest/services/elte_nht_100k_line/FeatureServer",
            "test_attachment_feature_class" : "https://services1.arcgis.com/2exN3kG1f2h7coIQ/arcgis/rest/services/test_attachment_feature_class/FeatureServer"}


log_file_path = os.path.join(workspace_path, "backup_script_log.txt")

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt = '%Y-%m-%d %H:%M:%S',
                    handlers=[logging.FileHandler(log_file_path, mode='a'), 
                              logging.StreamHandler()])

def update_last_modified_and_backup(username, password, fs_dict, last_modified_file, workspace_path):
    
    # Login to ArcGIS Online
    gis = GIS("https://www.arcgis.com", username, password)

    # Function to access the feature service's last modified date property, if it exists. 
    def get_layer_modified_date(layer, gis):
        try:
            flayer_collection = arcgis.features.FeatureLayerCollection(layer['url'], gis)
            flayer = FeatureLayer(flayer_collection.layers[0].url)
            return datetime.datetime.fromtimestamp(flayer.properties['editingInfo']['lastEditDate']/1000)
        except Exception as e:
            logging.info(f"Error getting modified date for layer {layer['title']}: {str(e)}")
            return None
    
    # Function to download a hosted feature service layer in GDB format
    def downloadFS(title, url, workspace_path, mod_date):
        try:
            timestamp = time.strftime("%Y%m%d_%H%M", time.localtime())
            mod_date = datetime.datetime.strptime(mod_date, '%Y-%m-%d %H:%M:%S')
            mod_date = mod_date.strftime('%Y%m%d_%H%M%S')
            gdb_rename = f"{title.strip()}_{mod_date}_{timestamp}"  
            feature_service_flc = arcgis.features.FeatureLayerCollection(url, gis)
            result = feature_service_flc.replicas.create(replica_name='temp',
                                                         layers='0',
                                                         data_format='filegdb',
                                                         out_path = workspace_path,
                                                         return_attachments=True,
                                                         attachments_sync_direction='bidirectional')
            
            # Create year//layer specific directories
            year = datetime.datetime.now().strftime("%Y")
            layer_dir = os.path.join(workspace_path,year,title)
            
            if not os.path.exists(layer_dir):
                os.makedirs(layer_dir)
            
            # Path of downloaded zip folder
            path = os.path.realpath(result)
            myzip = zipfile.ZipFile(str(path), 'r')
            # Get names of content in zipfile
            zipPath = zipfile.ZipFile.namelist(myzip)
            # Get the randomized GDB name from the zip folder
            gdbName = os.path.dirname(zipPath[0])
            # Extract zip archive
            myzip.extractall(layer_dir)
            # Rename GDB to an identifiable name
            os.rename(os.path.join(layer_dir, gdbName), os.path.join(layer_dir, gdb_rename + ".gdb"))
            # Close zip archive in order to delete
            myzip.close()
            os.remove(myzip.filename)
            logging.info(f"{title} was backed up.")
            return True 
        except Exception as e:
            logging.info(f"{title} could not be backed up. {e}. Please check attributes to verify the feature service can be replicated.")
            return False
    
    # Initialize a dictionary to store the layer's name as key and the layer's most recent modified date as value
    # Only values successfully obtained via the "get_layer_modified_date" function will be put into the dict.
    last_modified_dates = {}

    # If the edit properties cannot be accessed, the name and url of the feature service will be stored here.  
    error_layers = {}
    
    # Adds each feature service to its respective dictionary based on whether a date was retrieved or not. 
    for fs_name, fs_url in fs_dict.items():
        modified_date = get_layer_modified_date({'title': fs_name, 'url': fs_url}, gis)
        
        if modified_date:
            last_modified_dates[fs_name] = modified_date.strftime('%Y-%m-%d %H:%M:%S')
        else:
            error_layers[fs_name] = fs_url
    if len(error_layers) > 0:
        logging.info(f"The last modified dates of the following layers could not be accessed: {error_layers}")
    
    # Dictionary to store the titles and dates that will go into the JSON. Dates will only be updated if "downloadFS()" successfully runs on the feature service.   
    existing_data = {}
    
    if os.path.exists(last_modified_file):
        
        with open(last_modified_file, 'r') as file:
            existing_data = json.load(file)  

        for fs_title, new_date in last_modified_dates.items():
            existing_date = existing_data.get(fs_title)
            current_url = fs_dict.get(fs_title)
            if not existing_date:
                logging.info(f"{fs_title} has no existing backup. It will be backed up now.")
            elif datetime.datetime.strptime(new_date, '%Y-%m-%d %H:%M:%S') > datetime.datetime.strptime(existing_date, '%Y-%m-%d %H:%M:%S'):
                logging.info(f"{fs_title} has been modified since the last backup. {existing_date} --> {new_date}")

            if not existing_date or datetime.datetime.strptime(new_date, '%Y-%m-%d %H:%M:%S') > datetime.datetime.strptime(existing_date, '%Y-%m-%d %H:%M:%S'):          
                if downloadFS(fs_title, current_url, workspace_path, new_date):
                    existing_data[fs_title] = new_date
                else:
                    if existing_date:
                        existing_data[fs_title] = existing_date
            else:
                logging.info(f"We don't need to back up {fs_title}")
    else:
         # if the file does not exist, all layers from the fs_dict dictionary will be backed up.
        logging.info("An existing JSON log does not exist. It will be created following backup of all layers.")
        existing_data = last_modified_dates.copy()
        for fs_title, new_date in last_modified_dates.items():
            logging.info(f"{fs_title} does not have an existing backup and will be backed up.")
            if not downloadFS(fs_title, fs_dict[fs_title], workspace_path, new_date):
                existing_data.pop(fs_title)
    
    # Update the backup log JSON file. Dates will only be updated if the data successfully backed up. 
    with open(last_modified_file, "w") as file:
         json.dump(existing_data, file, indent=4)
            

    logging.info(f"The backup log '{last_modified_file}' has been updated and all modified data has been backed up.")


try:
    update_last_modified_and_backup(username, password, fs_dict, last_modified_file, workspace_path)

except Exception as e:
    logging.critical(f"Script failed due to an unhandled exception: {e}")
    raise
else:
    timestamp = time.strftime("%Y%m%d_%H%M", time.localtime())
    logging.info(f"Script successfully completed.")