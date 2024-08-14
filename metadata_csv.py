import os
import json
import pandas as pd
import sys

def main():
    # Get the input directory and output
    json_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    output_csv = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.getcwd(), 'metadata.csv')

    print(f"Starting metadata extraction from JSON files in directory: {json_dir}")
    print(f"Output CSV file will be saved to: {output_csv}")

    data = []

    # Loop through all the JSON files in the directory
    for json_file in os.listdir(json_dir):
        if json_file.endswith('.json'):
            file_path = os.path.join(json_dir, json_file)
            print(f"Processing file: {json_file}")

            try:
                with open(file_path, 'r') as f:
                    json_data = json.load(f)
                print(f"Successfully loaded JSON data from file: {json_file}")

                # Extract the QC data with default "N/A" if key is missing
                gloms_qc = json_data.get('gloms_qc', 'N/A')
                muscular_vessels_qc = json_data.get('muscular_vessels_qc', 'N/A')
                tubules_qc = json_data.get('tubules_qc', 'N/A')
                ptc_qc = json_data.get('ptc_qc', 'N/A')
                ifta_qc = json_data.get('ifta_qc', 'N/A')

                print(f"Extracted QC data for file: {json_file}")
                data.append({
                    'file_name': json_file,
                    'gloms_qc': gloms_qc,
                    'muscular_vessels_qc': muscular_vessels_qc,
                    'tubules_qc': tubules_qc,
                    'ptc_qc': ptc_qc,
                    'ifta_qc': ifta_qc
                })

            except json.JSONDecodeError:
                print(f"Error decoding JSON data from file '{json_file}'. Skipping file.")
                continue
            except Exception as e:
                print(f"Unexpected error processing JSON data from file '{json_file}': {e}")
                continue

    print(f"Collected data from {len(data)} files. Preparing to create DataFrame.")

    # Convert the collected data into a DataFrame
    try:
        df = pd.DataFrame(data)
        print("DataFrame created successfully.")
    except ValueError as e:
        print(f"Error creating DataFrame: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during DataFrame creation: {e}")
        sys.exit(1)

    # Save to a CSV file
    try:
        df.to_csv(output_csv, index=False)
        print(f"CSV file has been created successfully at: {output_csv}")
    except IOError as e:
        print(f"Error saving CSV file '{output_csv}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during CSV file saving: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Script execution started.")
    try:
        main()
    except Exception as e:
        print(f"An unexpected error occurred during script execution: {e}")
        sys.exit(1)
    print("Script execution completed successfully.")
