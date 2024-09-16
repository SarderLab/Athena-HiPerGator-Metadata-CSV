import girder_client
import json
import os
import argparse
import common

def remove_all_extensions(filename):
    print(f"Removing all extensions from filename: {filename}")
    while os.path.splitext(filename)[1]:
        filename = os.path.splitext(filename)[0]
    print(f"Filename after removing extensions: {filename}")
    return filename

def download_metadata(api_url, api_key, dest_root_dir, log_file, cookie, folderIDs=None, metadata_types=None):
    print(f"Starting download_metadata with api_url={api_url}, dest_root_dir={dest_root_dir}")
    json_file_path = os.path.join(dest_root_dir, 'logs', 'tracking_data.json')
    metadata_log = os.path.join(dest_root_dir, 'logs', 'metadata_log.txt')
    tracking_data = {}

    if os.path.exists(json_file_path):
        print(f"Loading existing tracking data from {json_file_path}")
        with open(json_file_path, 'r') as json_file:
            tracking_data = json.load(json_file)

    try:
        gc = girder_client.GirderClient(apiUrl=api_url)
        print("GirderClient initialized.")

        with gc.session() as session:
            with open(os.path.join(dest_root_dir, 'logs', log_file), "a") as log:
                print("Session started and log file opened.")

                try:
                    if cookie:
                        session.headers.update({'Cookie': f'auth_tkt={cookie}'})
                        print(f"Cookie set for authentication: {cookie}")
                    gc.authenticate(apiKey=api_key)
                    print("Authenticated successfully.")
                except Exception as e:
                    print(f"Error during GirderClient initialization or authentication: {e}")
                    log.write(f"Error during GirderClient initialization or authentication: {e}\n")
                    return

                folder_name = None

                if folderIDs:
                    folderIDs = folderIDs.split(',')
                    for folderID in folderIDs:
                        print(f"Fetching all items under the given folderID: {folderID}")
                        try:
                            folder_items = list(gc.listItem(folderID))
                            print(f"Got all items in the folder: {len(folder_items)} items found.")

                            folder_info = gc.getFolder(folderID)
                            folder_name = folder_info['name']
                            print(f"Folder name retrieved: {folder_name}")

                            path_without_file = os.path.join(dest_root_dir, folder_name)
                            os.makedirs(path_without_file, exist_ok=True)
                            print(f"Directory created for folderID {folderID}: {path_without_file}")

                            for item in folder_items:
                                item_id = item['_id']
                                print(f"Processing item: {item_id} - {item['name']}")

                                try:
                                    item_path = gc.get(f"/resource/{item_id}/path?type=item")
                                    print(f"Retrieved item path: {item_path}")
                                except Exception as e:
                                    print(f"Error retrieving item path for {item_id}: {e}")
                                    log.write(f"Error item_path {item_id}: {item['name']} {e}\n")
                                    continue

                                item_metadata = {}

                                if 'user_metadata' in metadata_types:
                                    item_user_meta = item.get('meta')
                                    if item_user_meta:
                                        print(f"User metadata found for item: {item_id}")
                                        item_metadata['user_metadata'] = item_user_meta

                                if 'annotations' in metadata_types:
                                    try:
                                        item_annotations = gc.get(f"annotation/item/{item_id}")
                                        print(f"Annotations found for item: {item_id}")
                                        item_metadata['annotations'] = item_annotations
                                    except Exception as e:
                                        print(f"Error retrieving annotations for {item_id}: {e}")
                                        log.write(f"[Annotation] GET {item_id}: {item['name']} {e}\n")

                                if 'large_image_metadata' in metadata_types:
                                    item_large_image_metadata = False
                                    if item.get('largeImage'):
                                        try:
                                            item_large_image_metadata = gc.get(f"item/{item_id}/tiles")
                                            print(f"Large image metadata found for item: {item_id}")
                                            item_metadata['large_image_metadata'] = item_large_image_metadata
                                        except Exception as e:
                                            print(f"Error retrieving large image metadata for {item_id}: {e}")
                                            log.write(f"[Large Image] GET {item_id}: {item['name']} {e}\n")
                                            
                                if 'downloadfiles' in metadata_types:
                                    print("downloadfiles")
                                    # List all files within the item using the GET /item/{id}/files API
                                    item_files = gc.get(f'/item/{item_id}/files')
                                    for file in item_files:
                                        file_name = file['name']
                                        file_id = file['_id']
                                        print(f"File: {file_name} (ID: {file_id})")

                                        # Only download files with .svs extension (can extend this logic to .tiff, .tif files)
                                        if file_name.lower().endswith('.svs'):
                                            print(f"Attempting to download .svs file: {file_name} (ID: {file_id})")
                                            try:
                                                # Download the .svs file using GET /file/{id}/download API
                                                metadata_path = os.path.join(path_without_file, 'File')
                                                os.makedirs(metadata_path, exist_ok=True)
                                                file_download_url = f'/file/{file_id}/download'
                                                response = gc.get(file_download_url, jsonResp=False)
                                                with open(os.path.join(metadata_path, file_name), 'wb') as f:
                                                    f.write(response.content)
                                                print(f"Downloaded file: {file_name} successfully.")
                                            except Exception as e:
                                                log.write(f"Error downloading file {file_name}: {e}\n")
                                                print(f"Error downloading file {file_name}: {e}")
                                        else:
                                            print(f"Skipping non-.svs file: {file_name}")
                                

                                if item_metadata:
                                    # Only create a JSON file if the metadata is not empty
                                    if any(item_metadata.values()):
                                        tracking_data[item_id] = item_metadata

                                        file_name = item['name']
                                        file_name_without_extensions = remove_all_extensions(file_name)
                                        print(f"File name without extensions: {file_name_without_extensions}")

                                        try:
                                            if 'annotations' in metadata_types and item_metadata.get('annotations'):
                                                metadata_path = os.path.join(path_without_file, 'Annotations')
                                                os.makedirs(metadata_path, exist_ok=True)
                                                file_path = os.path.join(metadata_path, file_name_without_extensions + '.json')
                                                print(f"Saving annotations metadata to: {file_path}")
                                            elif 'large_image_metadata' in metadata_types and item_metadata.get('large_image_metadata'):
                                                metadata_path = os.path.join(path_without_file, 'LargeImageMetadata')
                                                os.makedirs(metadata_path, exist_ok=True)
                                                file_path = os.path.join(metadata_path, file_name_without_extensions + '.json')
                                                print(f"Saving large image metadata to: {file_path}")
                                            elif 'user_metadata' in metadata_types and item_metadata.get('user_metadata'):
                                                metadata_path = os.path.join(path_without_file, 'UserMetadata')
                                                os.makedirs(metadata_path, exist_ok=True)
                                                file_path = os.path.join(metadata_path, file_name_without_extensions + '.json')
                                                print(f"Saving user metadata to: {file_path}")
                                        
                                            with open(file_path, 'w') as json_file:
                                                json.dump(item_metadata, json_file)
                                            print(f"Metadata saved and tracking data updated for item: {item_id}")
                                            with open(metadata_log, "a") as user_log:
                                                user_log.write(item_path + '\n')
                                        except Exception as e:
                                            print(f"Error saving metadata for {item_id}: {e}")
                                            log.write(f"[Saving Metadata] {item_id}: {item['name']} {e}\n")
                                    else:
                                        print(f"No relevant metadata for item {item_id}. Skipping file creation.")


                                    with open(json_file_path, 'w') as json_file:
                                        json.dump(tracking_data, json_file, indent=4)
                                        print(f"Tracking data updated in JSON file.")

                        except Exception as e:
                            print(f"Error fetching items for folderID {folderID}: {e}")
                            log.write(f"Error fetching items for folderID {folderID}: {e}\n")

    except Exception as e:
        print(f"Error occurred in session/GirderClient: {e}\n")

def chooseInstance():
    print("Parsing command line arguments.")
    parser = argparse.ArgumentParser(description='Download metadata.')
    parser.add_argument('instance', type=str, help='Instance name (e.g., athena, devathena)')
    parser.add_argument('--folder', type=str, help='Comma-separated list of FolderIDs')
    parser.add_argument('--dest', type=str, default=os.getcwd(), help='Optional destination directory to save the output')
    parser.add_argument('--user_metadata', action='store_true', help='Download user metadata')
    parser.add_argument('--large_image_metadata', action='store_true', help='Download large image metadata')
    parser.add_argument('--annotations', action='store_true', help='Download annotations')
    parser.add_argument('--file', action='store_true', help='Download files')

    args = parser.parse_args()

    instance = args.instance
    folderIDs = args.folder
    dest_dir = args.dest
    metadata_types = []

    if args.user_metadata:
        metadata_types.append('user_metadata')
    if args.large_image_metadata:
        metadata_types.append('large_image_metadata')
    if args.annotations:
        metadata_types.append('annotations')
    if args.file:
        metadata_types.append('downloadfiles')
    print(metadata_types)

    print(f"Arguments received - instance: {instance}, folder: {folderIDs}, dest: {dest_dir}, metadata_types: {metadata_types}")
    err_log = 'error_log_Metadata.txt'

    print(f"Fetching URL and credentials for instance: {instance}")
    api_url, api_key, _, cookie, _ = common.urlAndCredentials(instance)
    print(f"API URL: {api_url}")

    os.makedirs(os.path.join(dest_dir, 'logs'), exist_ok=True)
    print(f"Logs directory created or already exists: {os.path.join(dest_dir, 'logs')}")

    download_metadata(api_url, api_key, dest_dir, err_log, cookie, folderIDs, metadata_types)

if __name__ == "__main__":
    print("Starting script execution.")
    chooseInstance()
    print("Script execution completed.")