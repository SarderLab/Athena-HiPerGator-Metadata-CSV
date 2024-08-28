# Athena To HiPerGator Metadata-CSV (Automation)

## Description
This repo helps in automating the transfer of usermetada from anthena to HiPerGator. It has one python file executables "Metadata.py" which when executed transfers all the user metadata content from athena/devathena to HiPerGator. 

It uses the girder-client which is a python client library and a CLI to allow for programatic interaction with Girder server, and also to workaround limitations of the web client.

The Metadata file focuses on the detailed, often supplementary data elements essential for a complete dataset representation. Folders containing user metadata are created in locations with items. These folders are organized alongside the items they correspond to.

Note: All "Athena" folders are generated in the same directory as the execution absolute path. This means that the directory structure for these folders is maintained as defined in their initial configuration, ensuring a consistent and predictable file organization.

### Installation
Assuming these files are transferred into HiPerGator.

To start transfer of user metadata from User or Collection to HiPerGator
```
sbatch Metadata.sh athena --UserOrCollection userIDs/CollectionIDs --dest dest_addr(optional)
```

To start transfer of specific folder's user metadata to HiPerGator
```
sbatch Metadata.sh athena --folder FolderID --dest dest_addr(optional)
```

NOTE: If destination address is not specified the destination will be the same folder as you are running the code.


Example command to run in HiPerGator
```
sbatch Metadata.sh athena --folder 66b667e31acc7e45f89554a2 --dest /home/blue/pinaki.sarder/nikhil.yerra/test
```

#### JSON to CSV Metadata Extraction Script
Once the required metadata is transferred to the hipergator, use the metadata_csv.py file to aggregate this metadata to a csv file.
This Python script processes JSON files in a specified directory, extracting into a DataFrame, and then saves the collected data to a CSV file. It handles errors gracefully and provides feedback on its progress and any issues encountered.

## Requirements

- Python 3.x
- `pandas` library (can be installed via `pip install pandas`)

## Usage

To run the script, use:
```
python metadata_csv.py /path/to/json_files /path/to/output/metadata.csv
```

### logs
All logs are generated in a folder logs. These are generated whenever we run "Metadata.py". 

Error logs: <br/>
    [Metadata] error_log_UserMeta.txt <br/>

Audit logs: <br/>
    [Metadata] user_meta_data_log.txt <br/>


### Commnad to run 
To download annotations of a specific folder

```
python annotations_user_large_metadata.py athena --folder <Folder ID> --annotations --dest /path/to/destination
```

To download user metadata of a specific folder

```
python annotations_user_large_metadata.py athena --folder <Folder ID> --user_metadata --dest /path/to/destination
```
To download user large image metadata of a specific folder

```
python annotations_user_large_metadata.py athena --folder <Folder ID> --large_image_metadata --dest /path/to/destination
```

To download only files of a specific folder

```
python annotations_user_large_metadata.py athena --folder <Folder ID> --file --dest /path/to/destination
```



