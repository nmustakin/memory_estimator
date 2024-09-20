#!/bin/bash

num_files=$(ls Processed/matmul/*.txt | wc -l)

sbatch --array=1-$num_files matmul.sh
