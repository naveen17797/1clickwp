#!/bin/bash

# Exit on error
set -e

# Get WP path
WP_PATH=$(wp eval 'echo ABSPATH;' --skip-plugins --skip-themes)

# Define source and destination
SRC="/tmp/mu-plugins"
DEST="${WP_PATH}wp-content/mu-plugins"

mkdir -p $DEST

# Check if source exists
if [ ! -d "$SRC" ]; then
  echo "Source directory $SRC does not exist."
  exit 1
fi

# Copy files
cp -r "$SRC"/* "$DEST"

# Set permissions (optional but matches your request)
chmod -R 777 "$DEST"

echo "MU plugins copied from $SRC to $DEST"
