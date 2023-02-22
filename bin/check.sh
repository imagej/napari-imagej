#!/bin/sh

case "$CONDA_PREFIX" in
  */napari-imagej-dev)
    ;;
  *)
    echo "Please run 'make setup' and then 'mamba activate napari-imagej-dev' first."
    exit 1
    ;;
esac
