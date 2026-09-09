#!/usr/bin/env python3

import os
import re
import sys
import json
import argparse
import pandas as pd
import girder_client
import common


# ============================================================
# Configuration
# ============================================================

QC_COLUMNS = [
    "gloms_qc",
    "muscular_vessels_qc",
    "tubules_qc",
    "ptc_qc",
    "ifta_qc",
]


# ============================================================
# Utility functions
# ============================================================

def sanitize_name(name):
    """
    Convert a name to a filesystem-safe name.

    Examples:
        Jeffrey Hodgin   -> jeffrey_hodgin
        Laura Barisoni   -> laura_barisoni
        Pathologist #3   -> pathologist_#3
        Batch #1         -> Batch_#1
    """

    if not name:
        return "unknown"

    name = str(name).strip()

    # Spaces -> underscores
    name = re.sub(r"\s+", "_", name)

    # Remove problematic filesystem characters
    name = re.sub(r'[<>:"/\\|?*]', "_", name)

    # Collapse repeated underscores
    name = re.sub(r"_+", "_", name)

    return name


def remove_all_extensions(filename):
    """
    Remove all extensions.

    Example:
        kidney.svs.gz -> kidney
        image.tif     -> image
    """

    while os.path.splitext(filename)[1]:
        filename = os.path.splitext(filename)[0]

    return filename


def get_batch_number(folder_name):
    """
    Convert a folder name into the batch identifier used
    in output filenames.

    Examples:
        Batch #1 -> batch1
        Batch_#2 -> batch2
        Batch 3 -> batch3
    """

    match = re.search(
        r"batch[_\s-]*#?\s*(\d+)",
        folder_name,
        re.IGNORECASE
    )

    if match:
        return f"batch{match.group(1)}"

    # Fallback
    return sanitize_name(folder_name).lower()


def get_user_file_name(user_name):
    """
    Convert pathologist name to the filename convention.

    Examples:
        Jeffrey Hodgin -> jeffery
        Laura Barisoni -> laurabarisoni
        Pathologist #3 -> pathologist3

    The special Jeffrey spelling is kept to match your
    existing desired filename:
        output_batch1_jeffery.csv
    """

    clean_name = sanitize_name(user_name).lower()

    # Remove underscores
    clean_name = clean_name.replace("_", "")

    # Your existing requested naming convention
    if clean_name == "jeffreyhodgin":
        return "jeffery"

    return clean_name


# ============================================================
# Directory structure
# ============================================================

def create_user_structure(
    batch_root,
    user_name,
    batch_number
):
    """
    Creates:

        Batch_#1/
            pathologist/
                logs/
                UserMetaData/
                output_batch1_pathologist.csv
                output_batch1_pathologist_filtered.csv
    """

    user_dir_name = sanitize_name(
        user_name
    ).lower()

    user_dir = os.path.join(
        batch_root,
        user_dir_name
    )

    logs_dir = os.path.join(
        user_dir,
        "logs"
    )

    metadata_dir = os.path.join(
        user_dir,
        "UserMetaData"
    )

    os.makedirs(
        logs_dir,
        exist_ok=True
    )

    os.makedirs(
        metadata_dir,
        exist_ok=True
    )

    output_name = get_user_file_name(
        user_name
    )

    output_csv = os.path.join(
        user_dir,
        f"output_{batch_number}_{output_name}.csv"
    )

    filtered_csv = os.path.join(
        user_dir,
        f"output_{batch_number}_{output_name}_filtered.csv"
    )

    return {
        "root": user_dir,
        "logs": logs_dir,
        "metadata": metadata_dir,
        "output_csv": output_csv,
        "filtered_csv": filtered_csv,
        "tracking_json": os.path.join(
            logs_dir,
            "tracking_data.json"
        ),
        "error_log": os.path.join(
            logs_dir,
            "error_log_UserMeta.txt"
        ),
        "metadata_log": os.path.join(
            logs_dir,
            "user_meta_data_log.txt"
        ),
    }


# ============================================================
# Logging
# ============================================================

def write_log(log_file, message):
    """
    Write a message to a log file.
    """

    with open(
        log_file,
        "a"
    ) as f:

        f.write(message + "\n")


# ============================================================
# Tracking
# ============================================================

def load_tracking_data(path):
    """
    Load existing tracking data.
    """

    if not os.path.exists(path):
        return {}

    try:

        with open(
            path,
            "r"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


def save_tracking_data(
    path,
    tracking_data
):

    with open(
        path,
        "w"
    ) as f:

        json.dump(
            tracking_data,
            f,
            indent=4
        )


# ============================================================
# Girder metadata download
# ============================================================

def download_item_metadata(
    gc,
    item,
    user_structure,
    tracking_data
):
    """
    Download metadata for one Girder item.
    """

    item_id = item["_id"]

    item_name = item.get(
        "name",
        item_id
    )

    print(
        f"      Processing: {item_name}"
    )

    # --------------------------------------------------------
    # Get item path
    # --------------------------------------------------------

    try:

        item_path = gc.get(
            f"/resource/{item_id}/path?type=item"
        )

    except Exception as e:

        message = (
            f"[Item Path Error] "
            f"{item_id}: {item_name}: {e}"
        )

        print(
            f"      ERROR: {message}"
        )

        write_log(
            user_structure["error_log"],
            message
        )

        return False

    # --------------------------------------------------------
    # Get metadata
    # --------------------------------------------------------

    item_user_meta = item.get(
        "meta"
    )

    if not item_user_meta:

        print(
            f"      No metadata: {item_name}"
        )

        return False

    # --------------------------------------------------------
    # Metadata filename
    # --------------------------------------------------------

    base_name = remove_all_extensions(
        item_name
    )

    metadata_file = os.path.join(
        user_structure["metadata"],
        base_name + ".json"
    )

    # --------------------------------------------------------
    # Save metadata
    # --------------------------------------------------------

    try:

        with open(
            metadata_file,
            "w"
        ) as f:

            json.dump(
                item_user_meta,
                f,
                indent=4
            )

        # Tracking
        tracking_data[item_id] = {
            "item_name": item_name,
            "item_path": item_path,
            "metadata_file": metadata_file,
        }

        save_tracking_data(
            user_structure["tracking_json"],
            tracking_data
        )

        # Log path
        write_log(
            user_structure["metadata_log"],
            item_path
        )

        print(
            f"      Saved: {metadata_file}"
        )

        return True

    except Exception as e:

        message = (
            f"[Metadata Save Error] "
            f"{item_id}: {item_name}: {e}"
        )

        print(
            f"      ERROR: {message}"
        )

        write_log(
            user_structure["error_log"],
            message
        )

        return False


# ============================================================
# JSON -> CSV
# ============================================================

def json_to_csv(
    metadata_dir,
    output_csv
):
    """
    Read every JSON file in UserMetaData and create
    the corresponding CSV.
    """

    print()
    print(
        f"    JSON -> CSV"
    )

    print(
        f"    Input: {metadata_dir}"
    )

    print(
        f"    Output: {output_csv}"
    )

    data = []

    if not os.path.exists(
        metadata_dir
    ):

        print(
            "    UserMetaData directory does not exist."
        )

        return False

    # --------------------------------------------------------
    # Recursively find JSON files
    # --------------------------------------------------------

    json_files = []

    for root, dirs, files in os.walk(
        metadata_dir
    ):

        for filename in files:

            if filename.lower().endswith(
                ".json"
            ):

                json_files.append(
                    os.path.join(
                        root,
                        filename
                    )
                )

    print(
        f"    Found {len(json_files)} JSON files."
    )

    # --------------------------------------------------------
    # Read JSON files
    # --------------------------------------------------------

    for file_path in sorted(
        json_files
    ):

        json_file = os.path.basename(
            file_path
        )

        print(
            f"      Reading: {json_file}"
        )

        try:

            with open(
                file_path,
                "r"
            ) as f:

                json_data = json.load(f)

            # ----------------------------------------------
            # Extract QC metadata
            # ----------------------------------------------

            gloms_qc = json_data.get(
                "gloms_qc",
                "N/A"
            )

            muscular_vessels_qc = json_data.get(
                "muscular_vessels_qc",
                "N/A"
            )

            tubules_qc = json_data.get(
                "tubules_qc",
                "N/A"
            )

            ptc_qc = json_data.get(
                "ptc_qc",
                "N/A"
            )

            ifta_qc = json_data.get(
                "ifta_qc",
                "N/A"
            )

            data.append({
                "file_name": json_file,
                "gloms_qc": gloms_qc,
                "muscular_vessels_qc": muscular_vessels_qc,
                "tubules_qc": tubules_qc,
                "ptc_qc": ptc_qc,
                "ifta_qc": ifta_qc,
            })

        except json.JSONDecodeError as e:

            print(
                f"      ERROR decoding "
                f"{json_file}: {e}"
            )

            continue

        except Exception as e:

            print(
                f"      ERROR processing "
                f"{json_file}: {e}"
            )

            continue

    # --------------------------------------------------------
    # Create DataFrame
    # --------------------------------------------------------

    df = pd.DataFrame(
        data,
        columns=[
            "file_name",
            "gloms_qc",
            "muscular_vessels_qc",
            "tubules_qc",
            "ptc_qc",
            "ifta_qc",
        ]
    )

    # --------------------------------------------------------
    # Save CSV
    # --------------------------------------------------------

    try:

        df.to_csv(
            output_csv,
            index=False
        )

        print(
            f"    CSV created: {output_csv}"
        )

        print(
            f"    Rows: {len(df)}"
        )

        return True

    except Exception as e:

        print(
            f"    ERROR writing CSV: {e}"
        )

        return False


# ============================================================
# CSV filtering
# ============================================================

def filter_csv(
    input_csv,
    output_csv
):
    """
    Filter the CSV using the same logic as your existing
    filtering script.

    Keep rows where at least ONE QC column is not "N/A".
    """

    print()
    print(
        f"    Filtering CSV"
    )

    print(
        f"    Input: {input_csv}"
    )

    print(
        f"    Output: {output_csv}"
    )

    try:

        df = pd.read_csv(
            input_csv,
            keep_default_na=False
        )

    except Exception as e:

        print(
            f"    ERROR reading CSV: {e}"
        )

        return False

    # --------------------------------------------------------
    # Check columns
    # --------------------------------------------------------

    missing_columns = [
        col
        for col in QC_COLUMNS
        if col not in df.columns
    ]

    if missing_columns:

        print(
            "    ERROR: Missing QC columns:"
        )

        for col in missing_columns:
            print(
                f"      {col}"
            )

        return False

    # --------------------------------------------------------
    # Original filtering logic
    # --------------------------------------------------------

    before_count = len(df)

    mask = ~df[
        QC_COLUMNS
    ].eq("N/A").all(axis=1)

    df_filtered = df[
        mask
    ].copy()

    after_count = len(
        df_filtered
    )

    removed_count = (
        before_count -
        after_count
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    try:

        df_filtered.to_csv(
            output_csv,
            index=False
        )

        print(
            f"    Filtering complete."
        )

        print(
            f"    Original rows: {before_count}"
        )

        print(
            f"    Kept rows:     {after_count}"
        )

        print(
            f"    Removed rows:  {removed_count}"
        )

        print(
            f"    Saved: {output_csv}"
        )

        return True

    except Exception as e:

        print(
            f"    ERROR writing filtered CSV: {e}"
        )

        return False


# ============================================================
# Process one pathologist
# ============================================================

def process_user(
    gc,
    items,
    user_name,
    batch_root,
    batch_number
):
    """
    Complete processing for one pathologist:

        1. Create directories
        2. Download metadata
        3. JSON -> CSV
        4. Filter CSV
    """

    print()
    print(
        "#" * 70
    )

    print(
        f"PATHOLOGIST: {user_name}"
    )

    print(
        "#" * 70
    )

    # --------------------------------------------------------
    # Create structure
    # --------------------------------------------------------

    structure = create_user_structure(
        batch_root=batch_root,
        user_name=user_name,
        batch_number=batch_number
    )

    print(
        f"    Directory: {structure['root']}"
    )

    # --------------------------------------------------------
    # Tracking
    # --------------------------------------------------------

    tracking_data = load_tracking_data(
        structure["tracking_json"]
    )

    # --------------------------------------------------------
    # Download metadata
    # --------------------------------------------------------

    metadata_count = 0

    for item in items:

        success = download_item_metadata(
            gc=gc,
            item=item,
            user_structure=structure,
            tracking_data=tracking_data
        )

        if success:
            metadata_count += 1

    print()
    print(
        f"    Metadata files created: "
        f"{metadata_count}"
    )

    # --------------------------------------------------------
    # JSON -> CSV
    # --------------------------------------------------------

    csv_success = json_to_csv(
        metadata_dir=structure["metadata"],
        output_csv=structure["output_csv"]
    )

    if not csv_success:

        print(
            "    JSON -> CSV failed."
        )

        return False

    # --------------------------------------------------------
    # CSV -> filtered CSV
    # --------------------------------------------------------

    filter_success = filter_csv(
        input_csv=structure["output_csv"],
        output_csv=structure["filtered_csv"]
    )

    if not filter_success:

        print(
            "    CSV filtering failed."
        )

        return False

    print()
    print(
        f"    COMPLETED: {user_name}"
    )

    return True


# ============================================================
# Recursive Girder folder processing
# ============================================================

def process_folder_recursive(
    gc,
    folder_id,
    batch_root,
    batch_number,
    pathologist_name=None,
    processed_users=None
):
    """
    Recursively traverse Girder folders.

    Folder structure assumed:

        Batch #1
        ├── Jeffrey Hodgin
        │   ├── image1
        │   └── image2
        ├── Laura Barisoni
        │   ├── image3
        │   └── image4
        └── Pathologist #3
            └── image5

    The first folder level below the Batch folder is treated
    as the pathologist name.

    Deeper folders remain part of that pathologist's items.
    """

    if processed_users is None:
        processed_users = {}
        
    # --------------------------------------------------------
    # Get folder
    # --------------------------------------------------------

    try:

        folder_info = gc.getFolder(
            folder_id
        )

        folder_name = folder_info[
            "name"
        ]

    except Exception as e:

        print(
            f"ERROR getting folder "
            f"{folder_id}: {e}"
        )

        return

    print()
    print(
        f"Scanning folder: {folder_name}"
    )

    # --------------------------------------------------------
    # Determine current pathologist
    # --------------------------------------------------------

    current_pathologist = pathologist_name

    if current_pathologist is None:

        # This is the first level below Batch.
        # Folder name becomes pathologist.
        current_pathologist = folder_name

    # --------------------------------------------------------
    # Get items
    # --------------------------------------------------------

    try:

        items = list(
            gc.listItem(
                folder_id
            )
        )

    except Exception as e:

        print(
            f"ERROR listing items in "
            f"{folder_name}: {e}"
        )

        return

    # --------------------------------------------------------
    # Add items to pathologist group
    # --------------------------------------------------------

    if items:

        if current_pathologist not in processed_users:

            processed_users[
                current_pathologist
            ] = []

        processed_users[
            current_pathologist
        ].extend(items)

        print(
            f"  Found {len(items)} items "
            f"for {current_pathologist}"
        )

    # --------------------------------------------------------
    # Get subfolders
    # --------------------------------------------------------

    try:

        subfolders = list(
            gc.listFolder(
                folder_id
            )
        )

    except Exception as e:

        print(
            f"ERROR listing subfolders "
            f"of {folder_name}: {e}"
        )

        return

    # --------------------------------------------------------
    # Recurse
    # --------------------------------------------------------

    for subfolder in subfolders:

        process_folder_recursive(
            gc=gc,
            folder_id=subfolder["_id"],
            batch_root=batch_root,
            batch_number=batch_number,
            pathologist_name=current_pathologist,
            processed_users=processed_users
        )


# ============================================================
# Main batch processor
# ============================================================

def process_batch(
    gc,
    folder_id,
    dest_root
):
    """
    Process an entire Batch folder.

    """

    # --------------------------------------------------------
    # Get batch information
    # --------------------------------------------------------

    try:

        batch_folder = gc.getFolder(
            folder_id
        )

        batch_name = batch_folder[
            "name"
        ]

    except Exception as e:

        print(
            f"ERROR retrieving batch folder: {e}"
        )

        return False

    # --------------------------------------------------------
    # Batch names
    # --------------------------------------------------------

    batch_dir_name = sanitize_name(
        batch_name
    )

    batch_number = get_batch_number(
        batch_name
    )

    batch_root = os.path.join(
        dest_root,
        batch_dir_name
    )

    os.makedirs(
        batch_root,
        exist_ok=True
    )

    print()
    print(
        "=" * 70
    )

    print(
        f"BATCH: {batch_name}"
    )

    print(
        f"Batch output: {batch_root}"
    )

    print(
        f"Batch identifier: {batch_number}"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # Collect items by pathologist
    # --------------------------------------------------------

    processed_users = {}

    subfolders = list(
        gc.listFolder(
            folder_id
        )
    )

    print(
        f"Found {len(subfolders)} "
        f"pathologist/top-level folders."
    )

    # --------------------------------------------------------
    # Each immediate child = pathologist
    # --------------------------------------------------------

    for subfolder in subfolders:

        pathologist_folder_id = (
            subfolder["_id"]
        )

        pathologist_folder_name = (
            subfolder["name"]
        )

        print()
        print(
            "-" * 70
        )

        print(
            f"Pathologist folder: "
            f"{pathologist_folder_name}"
        )

        print(
            "-" * 70
        )

        process_folder_recursive(
            gc=gc,
            folder_id=pathologist_folder_id,
            batch_root=batch_root,
            batch_number=batch_number,
            pathologist_name=pathologist_folder_name,
            processed_users=processed_users
        )

    # --------------------------------------------------------
    # Process each pathologist
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )

    print(
        f"Pathologists found: "
        f"{len(processed_users)}"
    )

    print(
        "=" * 70
    )

    for user_name, items in processed_users.items():

        process_user(
            gc=gc,
            items=items,
            user_name=user_name,
            batch_root=batch_root,
            batch_number=batch_number
        )

    return True


# ============================================================
# Girder authentication
# ============================================================

def connect_to_girder(
    instance
):
    """
    Initialize and authenticate Girder.
    """

    print()
    print(
        f"Connecting to Girder instance: "
        f"{instance}"
    )

    api_url, api_key, _, cookie, _ = (
        common.urlAndCredentials(
            instance
        )
    )

    print(
        f"API URL: {api_url}"
    )

    try:

        gc = girder_client.GirderClient(
            apiUrl=api_url
        )

    except Exception as e:

        print(
            f"ERROR initializing GirderClient: {e}"
        )

        return None

    try:

        # ----------------------------------------------------
        # Authentication cookie
        # ----------------------------------------------------

        if cookie:

            gc.session().headers.update({
                "Cookie": f"auth_tkt={cookie}"
            })

        # ----------------------------------------------------
        # API authentication
        # ----------------------------------------------------

        gc.authenticate(
            apiKey=api_key
        )

        print(
            "Girder authentication successful."
        )

        return gc

    except Exception as e:

        print(
            f"ERROR authenticating with Girder: {e}"
        )

        return None


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Recursive KPMP Girder metadata pipeline: "
            "download JSON -> create CSV -> filter CSV."
        )
    )

    parser.add_argument(
        "instance",
        type=str,
        help=(
            "Girder instance, e.g. athena "
            "or devathena"
        )
    )

    parser.add_argument(
        "--folder",
        required=True,
        type=str,
        help=(
            "Girder Batch Folder ID. "
            "Multiple IDs can be comma-separated."
        )
    )

    parser.add_argument(
        "--dest",
        required=True,
        type=str,
        help=(
            "Destination root directory."
        )
    )

    args = parser.parse_args()

    print()
    print(
        "=" * 70
    )
    print(
        "KPMP METADATA PIPELINE"
    )
    print(
        "=" * 70
    )

    print(
        f"Instance: {args.instance}"
    )

    print(
        f"Folder(s): {args.folder}"
    )

    print(
        f"Destination: {args.dest}"
    )

    # --------------------------------------------------------
    # Create destination
    # --------------------------------------------------------

    os.makedirs(
        args.dest,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Connect to Girder
    # --------------------------------------------------------

    gc = connect_to_girder(
        args.instance
    )

    if gc is None:

        sys.exit(1)

    # --------------------------------------------------------
    # Multiple batch folders
    # --------------------------------------------------------

    folder_ids = [
        x.strip()
        for x in args.folder.split(",")
        if x.strip()
    ]

    # --------------------------------------------------------
    # Process each batch
    # --------------------------------------------------------

    for folder_id in folder_ids:

        print()
        print()
        print(
            "#" * 70
        )

        print(
            f"STARTING BATCH FOLDER: {folder_id}"
        )

        print(
            "#" * 70
        )

        try:

            process_batch(
                gc=gc,
                folder_id=folder_id,
                dest_root=args.dest
            )

        except Exception as e:

            print()
            print(
                f"ERROR processing batch "
                f"{folder_id}: {e}"
            )

            continue

    # --------------------------------------------------------
    # Done
    # --------------------------------------------------------

    print()
    print()
    print(
        "=" * 70
    )

    print(
        "ALL PROCESSING COMPLETE"
    )

    print(
        "=" * 70
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print(
            "Pipeline interrupted by user."
        )

        sys.exit(130)

    except Exception as e:

        print()
        print(
            f"Fatal error: {e}"
        )

        sys.exit(1)
