#!/bin/bash 

for file in Processed/*.txt; do
    filename=$(basename -- "$file")
    config="${filename%.*}"
    i="${config##*_}"
    config_sub="${config#*_}"
    output_file="Outputs/output_${config_sub}.txt"

    echo "$file" "$i" "$output_file"
done
