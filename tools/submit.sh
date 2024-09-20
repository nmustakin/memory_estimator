#!/bin/bash
#SBATCH --job-name=mem_estimate
#SBATCH --time=02:00:00
#SBATCH --partition=junction
#SBATCH --ntasks=1

FILELIST="files.txt"
INDEX=$(($SLURM_ARRAY_TASK_ID -1))
FILE=$(sed -n "${INDEX}p" $FILELIST)


filename=$(basename -- "$FILE")

config="${filename%.*}"

i=${config##*_}

config_sub=${config#*_}

output_file="Outputs/minivite/new/mv_${config_sub}.txt"

python mem_approx_4D_processed_sklearn.py "$FILE" "$i" &> "$output_file"

