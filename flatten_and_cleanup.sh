#!/bin/bash
# flatten_and_cleanup.sh
# This script moves all PDFs from subdirectories of the specified folder to that folder,
# deletes any empty directories, and then removes directories that contain non-PDF files.
# Usage: ./flatten_and_cleanup.sh /path/to/folder

# Check for the folder argument.
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <folder>"
  exit 1
fi

TARGET_FOLDER="$1"

# Verify that the provided argument is a directory.
if [ ! -d "$TARGET_FOLDER" ]; then
  echo "Error: '$TARGET_FOLDER' is not a valid directory."
  exit 1
fi

# Change to the target directory.
cd "$TARGET_FOLDER" || { echo "Error: Unable to change directory to '$TARGET_FOLDER'"; exit 1; }

echo "Working in folder: $TARGET_FOLDER"

# Step 1: Flatten PDFs by moving them to the current directory.
echo "Flattening PDF files from subdirectories..."
find . -mindepth 2 -type f -name "*.pdf" -exec mv -n {} . \;

# Step 2: Delete empty directories.
echo "Deleting empty directories..."
find . -type d -empty -delete

# Step 3: Identify directories that contain any files other than PDFs.
echo "Identifying directories containing non-PDF files..."
directories=$(find . -mindepth 1 -type d -exec sh -c '
  for f in "$1"/*; do
    case "$f" in
      *.pdf|*.PDF) ;;
      *) echo "$1"; exit 0;;
    esac
  done
' _ {} \; | sort -u)

# If no directories are found, exit.
if [ -z "$directories" ]; then
  echo "No directories found containing non-PDF files."
  exit 0
fi

echo "The following directories contain non-PDF files and will be deleted:"
echo "$directories"
echo

# Step 4: Ask for confirmation before deletion.
read -p "Are you sure you want to delete these directories? (y/N): " confirm
if [[ $confirm == "y" || $confirm == "Y" ]]; then
  echo "$directories" | while IFS= read -r dir; do
    echo "Deleting: $dir"
    rm -rf "$dir"
  done
  echo "Deletion complete."
else
  echo "Deletion aborted."
fi

echo "Script complete."