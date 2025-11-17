#!/bin/bash
# Wrapper script to set OpenMP environment variable before running Python
# This fixes FAISS segmentation faults on Apple Silicon

export KMP_DUPLICATE_LIB_OK=TRUE

# Run the Python command with all arguments passed through
python "$@"
