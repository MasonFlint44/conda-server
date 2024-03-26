#!/bin/bash

MERGED_ENV_FILE=/tmp/merged-environment.yml

# Merge the environment files
conda-merge environment.dev.yml environment.yml > $MERGED_ENV_FILE

# Check if the dev environment exists
if mamba env list | grep -wq $ENVIRONMENT_NAME-dev; then
    # Update the dev environment from the merged file
    mamba env update -f $MERGED_ENV_FILE -n $ENVIRONMENT_NAME-dev

    # Remove unused packages
    mamba clean --all -y
else
    # Create the dev environment from the merged file if it does not exist
    mamba env create -f $MERGED_ENV_FILE -n $ENVIRONMENT_NAME-dev
fi

# Check if the app environment exists
if mamba env list | grep -wq $ENVIRONMENT_NAME; then
    # Update the app environment from the merged file
    mamba env update -f environment.yml -n $ENVIRONMENT_NAME

    # Remove unused packages
    mamba clean --all -y
else
    # Create the app environment from the merged file if it does not exist
    mamba env create -f environment.yml -n $ENVIRONMENT_NAME
fi

# Export the app environment to a lock file
mamba env export -n $ENVIRONMENT_NAME > environment.lock.yml
