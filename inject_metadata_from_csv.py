import girder_client
import csv

def get_metadata_from_item(gc, item_id):
    try:
        # Retrieve the full item information, including metadata
        item = gc.get(f'item/{item_id}')
        # Extract metadata from the item
        item_user_meta = item.get('meta')
        return item_user_meta if item_user_meta else {}
    except Exception as e:
        print(f'Error retrieving metadata for item {item_id}: {e}')
        return {}

def update_metadata_for_item(gc, item_id, kpmp_participant_id, kpmp_sample_id):
    try:
        # Construct metadata object to update
        metadata = {
            "kpmp_participant_id": kpmp_participant_id,
            "kpmp_sample_id": kpmp_sample_id
        }
        
        # Make the PUT request to update the metadata
        gc.put(f'item/{item_id}/metadata', json=metadata)
        print(f"Updated metadata for item {item_id}: {metadata}")
    except Exception as e:
        print(f'Error updating metadata for item {item_id}: {e}')

def process_csv_and_update_metadata(gc, csv_file):
    try:
        # Open and read the CSV file
        with open(csv_file, mode='r') as file:
            reader = csv.DictReader(file)
            
            # Iterate through each row in the CSV file
            for row in reader:
                file_name = row['file_name']
                kpmp_participant_id = row['kpmp_participant_id']
                kpmp_sample_id = row['kpmp_sample_id']
                
                # Fetch the item_id using the file_name (assuming a method to find item by name exists)
                item_id = find_item_by_name(gc, file_name)
                
                if item_id:
                    # Update metadata for the item with the given participant and sample ID
                    update_metadata_for_item(gc, item_id, kpmp_participant_id, kpmp_sample_id)
                else:
                    print(f'Item with file name {file_name} not found.')
    except Exception as e:
        print(f'Error processing CSV file: {e}')

def find_item_by_name(gc, file_name):
    try:
        # You can filter the items by name using the `listItem` function
        # Assuming the folder_id is known, you may want to filter by file name
        folder_id = '66b667e31acc7e45f89554a2'  # Replace with actual folder ID
        files = list(gc.listItem(folder_id))
        
        for file in files:
            if file['name'] == file_name:
                return file['_id']  # Return the item ID if file name matches
        return None  # Return None if no file is found
    except Exception as e:
        print(f'Error finding item by name {file_name}: {e}')
        return None

if __name__ == '__main__':
    api_url = 'https://athena.rc.ufl.edu/api/v1'
    token = 'xGiMv9knanKDS5IY7LX3nYf7kPhPBE07yi5GcbZ6TqlYCEWjwNkcHJ8SX1o8ziXm'
    folder_id = '66b667e31acc7e45f89554a2'  # Replace with your actual folder ID
    csv_file = 'metadata.csv'  # Path to your CSV file

    gc = girder_client.GirderClient(apiUrl=api_url)
    gc.setToken(token)

    # Process the CSV and update metadata
    process_csv_and_update_metadata(gc, csv_file)
