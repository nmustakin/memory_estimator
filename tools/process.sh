#!/bin/bash
#SBATCH --job-name=mem_estimate
#SBATCH --time=02:00:00
#SBATCH --partition=junction
#SBATCH --ntasks=1

FILELIST="matmul.txt"
INDEX=$(($SLURM_ARRAY_TASK_ID -1))
FILE=$(sed -n "${INDEX}p" $FILELIST)

python mem_trace_parse.py "$FILE"

