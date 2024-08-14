import girder_client
import json
import os
import sys
import argparse
import common

def remove_all_extensions(filename):
    print(f"Removing all extensions from filename: {filename}")
    while os.path.splitext(filename)[1]:
        filename = os.path.splitext(filename)[0]
    print(f"Filename after removing extensions: {filename}")
    return filename

def download_user_meta_data(api_url, api_key, dest_root_dir, log_file, cookie, UserOrCollectionIDs=None, folderIDs=None):
    print(f"Starting download_user_meta_data with api_url={api_url}, dest_root_dir={dest_root_dir}")
    json_file_path = os.path.join(dest_root_dir, 'logs', 'tracking_data.json')

    # Log files
    user_metadata_log = os.path.join(dest_root_dir, 'logs', 'user_meta_data_log.txt')
    tracking_data = {}

    # Check if the JSON file exists
    if os.path.exists(json_file_path):
        print(f"Loading existing tracking data from {json_file_path}")
        with open(json_file_path, 'r') as json_file:
            tracking_data = json.load(json_file)

    try:
        gc = girder_client.GirderClient(apiUrl=api_url)
        print("GirderClient initialized.")

        # Creating session to add cookie for dev athena
        with gc.session() as session:
            with open(os.path.join(dest_root_dir, 'logs', log_file), "a") as log:
                print("Session started and log file opened.")

                # Authenticate user
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

                all_items = []
                all_base_parents = []
                folder_name = None

                # Process multiple folderIDs if provided
                if folderIDs:
                    folderIDs = folderIDs.split(',')
                    for folderID in folderIDs:
                        print(f"Fetching all items under the given folderID: {folderID}")
                        try:
                            # Fetch all items under the given folderID
                            folder_items = list(gc.listItem(folderID))
                            print(f"Got all items in the folder: {len(folder_items)} items found.")

                            # Get the folder name for directory creation
                            folder_info = gc.getFolder(folderID)
                            folder_name = folder_info['name']
                            print(f"Folder name retrieved: {folder_name}")

                            # Create a separate folder for each folderID
                            path_without_file = os.path.join(dest_root_dir, folder_name)
                            os.makedirs(path_without_file, exist_ok=True)
                            print(f"Directory created for folderID {folderID}: {path_without_file}")

                            # Process items
                            for item in folder_items:
                                item_id = item['_id']
                                print(f"Processing item: {item_id} - {item['name']}")

                                # Get Item Path
                                try:
                                    item_path = gc.get(f"/resource/{item_id}/path?type=item")
                                    print(f"Retrieved item path: {item_path}")
                                except Exception as e:
                                    print(f"Error retrieving item path for {item_id}: {e}")
                                    log.write(f"Error item_path {item_id}: {item['name']} {e}\n")
                                    continue

                                # Retrieve metadata from the item
                                item_user_meta = item.get('meta')
                                if item_user_meta:
                                    print(f"User metadata found for item: {item_id}")

                                    # Tracking each item that is retrieved
                                    tracking_data[item_id] = {'user_metadata': []}

                                    file_name = item['name']
                                    file_name_without_extensions = remove_all_extensions(file_name)
                                    print(f"File name without extensions: {file_name_without_extensions}")

                                    try:
                                        user_meta_path = os.path.join(path_without_file, 'UserMetaData')
                                        os.makedirs(user_meta_path, exist_ok=True)
                                        print(f"Directory created: {user_meta_path}")
                                        file_path = os.path.join(user_meta_path, file_name_without_extensions + '.json')
                                        print(f"Saving metadata to: {file_path}")
                                        with open(file_path, 'w') as json_file:
                                            json.dump(item_user_meta, json_file)
                                        tracking_data[item_id]['user_metadata'].append(item_id)
                                        print(f"Metadata saved and tracking data updated for item: {item_id}")
                                        with open(user_metadata_log, "a") as user_log:
                                            user_log.write(item_path + '\n')
                                    except Exception as e:
                                        print(f"Error saving metadata for {item_id}: {e}")
                                        log.write(f"[Saving User MetaData] {item_id}: {item['name']} {e}\n")

                                    # Write tracking data to a JSON file
                                    with open(json_file_path, 'w') as json_file:
                                        json.dump(tracking_data, json_file, indent=4)
                                        print(f"Tracking data updated in JSON file.")

                        except Exception as e:
                            print(f"Error fetching items for folderID {folderID}: {e}")
                            log.write(f"Error fetching items for folderID {folderID}: {e}\n")

                # Process multiple UserOrCollectionIDs if provided
                if UserOrCollectionIDs:
                    UserOrCollectionIDs = UserOrCollectionIDs.split(',')
                    print(f"Fetching all items, users, and collections for UserOrCollectionIDs: {UserOrCollectionIDs}")
                    try:
                        # Fetch all items, users, and collections
                        all_items = gc.get(f'item/query?query={{}}&limit=0')
                        all_users = list(gc.listUser())
                        all_collections = list(gc.listCollection())
                        all_base_parents = all_users + all_collections
                        print('Got all details.')

                        # Filter based on UserOrCollectionIDs
                        print(f"Filtering based on UserOrCollectionIDs: {UserOrCollectionIDs}")
                        all_base_parents = [base_parent for base_parent in all_base_parents if base_parent['_id'] in UserOrCollectionIDs]
                        all_items = [item for item in all_items if item['baseParentId'] in UserOrCollectionIDs]
                        print(f"Filtered items: {len(all_items)} items remaining.")
                    except Exception as e:
                        print(f"Error fetching users/collections: {e}")
                        log.write(f"Error fetching users/collections: {e}\n")

                    # Iterate over each item and get associated user metadata
                    try:
                        for item in all_items:
                            item_id = item['_id']
                            print(f"Processing item: {item_id} - {item['name']}")

                            # Get Item Path
                            try:
                                item_path = gc.get(f"/resource/{item_id}/path?type=item")
                                print(f"Retrieved item path: {item_path}")
                            except Exception as e:
                                print(f"Error retrieving item path for {item_id}: {e}")
                                log.write(f"Error item_path {item_id}: {item['name']} {e}\n")
                                continue

                            # Retrieve metadata from the item
                            item_user_meta = item.get('meta')
                            if item_user_meta:
                                print(f"User metadata found for item: {item_id}")

                                # Tracking each item that is retrieved
                                tracking_data[item_id] = {'user_metadata': []}

                                # Original logic for UserOrCollectionID
                                item_associated_parent = next(
                                    (item_parent for item_parent in all_base_parents if item['baseParentId'] == item_parent['_id']), None)

                                # Handle the case where no associated parent is found
                                if item_associated_parent is None:
                                    print(f"No associated parent found for item {item_id}, skipping.")
                                    continue

                                if item_associated_parent['_modelType'] == "user":
                                    baseFolderName = item_associated_parent['firstName'] + '_' + item_associated_parent['lastName']
                                else:
                                    baseFolderName = item_associated_parent['name']

                                print(f"Base folder name determined: {baseFolderName}")

                                item_path = item_path.replace('\\-', '_')
                                path_parts = item_path.split('/')
                                path_parts[2] = baseFolderName
                                path_without_file = os.path.join(dest_root_dir, *path_parts[:-1])
                                print(f"Path without file for UserOrCollectionID: {path_without_file}")

                                file_name = item['name']
                                file_name_without_extensions = remove_all_extensions(file_name)
                                print(f"File name without extensions: {file_name_without_extensions}")

                                try:
                                    user_meta_path = os.path.join(path_without_file, 'UserMetaData')
                                    os.makedirs(user_meta_path, exist_ok=True)
                                    print(f"Directory created: {user_meta_path}")
                                    file_path = os.path.join(user_meta_path, file_name_without_extensions + '.json')
                                    print(f"Saving metadata to: {file_path}")
                                    with open(file_path, 'w') as json_file:
                                        json.dump(item_user_meta, json_file)
                                    tracking_data[item_id]['user_metadata'].append(item_id)
                                    print(f"Metadata saved and tracking data updated for item: {item_id}")
                                    with open(user_metadata_log, "a") as user_log:
                                        user_log.write(item_path + '\n')
                                except Exception as e:
                                    print(f"Error saving metadata for {item_id}: {e}")
                                    log.write(f"[Saving User MetaData] {item_id}: {item['name']} {e}\n")

                                # Write tracking data to a JSON file
                                with open(json_file_path, 'w') as json_file:
                                    json.dump(tracking_data, json_file, indent=4)
                                    print(f"Tracking data updated in JSON file.")

                    except Exception as e:
                        print(f"Error while processing all items: {e}")
                        log.write(f"Error while processing all items: {e}\n")
                        return
    except Exception as e:
        print(f"Error occurred in session/GirderClient: {e}\n")

def chooseInstance():
    print("Parsing command line arguments.")
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Download user metadata.')
    parser.add_argument('instance', type=str, help='Instance name (e.g., athena, devathena)')
    parser.add_argument('--UserOrCollection', type=str, help='Comma-separated list of UserOrCollectionIDs')
    parser.add_argument('--folder', type=str, help='Comma-separated list of FolderIDs')
    parser.add_argument('--dest', type=str, default=os.getcwd(), help='Optional destination directory to save the output')

    args = parser.parse_args()

    instance = args.instance
    UserOrCollectionIDs = args.UserOrCollection
    folderIDs = args.folder
    dest_dir = args.dest
    print(f"Arguments received - instance: {instance}, UserOrCollection: {UserOrCollectionIDs}, folder: {folderIDs}, dest: {dest_dir}")
    err_log = 'error_log_UserMeta.txt'

    print(f"Fetching URL and credentials for instance: {instance}")
    api_url, api_key, _, cookie, _ = common.urlAndCredentials(instance)
    print(f"API URL: {api_url}")

    os.makedirs(os.path.join(dest_dir, 'logs'), exist_ok=True)
    print(f"Logs directory created or already exists: {os.path.join(dest_dir, 'logs')}")

    download_user_meta_data(api_url, api_key, dest_dir, err_log, cookie, UserOrCollectionIDs, folderIDs)

if __name__ == "__main__":
    print("Starting script execution.")
    chooseInstance()
    print("Script execution completed.")
