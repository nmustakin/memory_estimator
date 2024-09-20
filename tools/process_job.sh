#!/bin/bash

num_files=$(ls /scratch/must032/matmul/*.txt | wc -l)

sbatch --array=1-$num_files submit.sh
