#!/bin/bash
#SBATCH --job-name=annotations_meta_download
#SBATCH --ntasks=1
#SBATCH --time=12:00:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=2

module load python
module load conda

# Function to check if conda environment exists
env_exists() {
    conda env list | awk '{print $1}' | grep -qx $1
}

# Activate environment if it exists, otherwise create and install girder-client
if env_exists SP_DataManagement; then
    echo "Activating SP_DataManagement environment."
    source activate SP_DataManagement || { echo "Failed to activate environment"; exit 1; }
else
    echo "Creating SP_DataManagement environment and installing girder-client."
    conda create -n SP_DataManagement python=3.8 -y || { echo "Failed to create environment"; exit 1; }
    source activate SP_DataManagement || { echo "Failed to activate environment"; exit 1; }
    conda install -c conda-forge girder-client -y || { echo "Failed to install girder-client"; exit 1; }
fi


python file_metadata_annotation.py $@