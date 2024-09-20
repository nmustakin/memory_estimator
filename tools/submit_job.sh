#!/bin/bash

num_files=$(ls Processed/*.txt | wc -l)

sbatch --array=1-$num_files submit.sh
