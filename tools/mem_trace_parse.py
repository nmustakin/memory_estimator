#import matplotlib.pyplot as plt
import numpy as np
import re
import math
import sys 
import os
#from sklearn.cluster import KMeans
#from kneed import KneeLocator
#from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
#from operator import itemgetter 

# Regex to parse the memory trace
mem_trace_regex = re.compile(
        r"0x([0-9a-f]+) \| MemAddr: 0x([0-9a-f]+) \| MemSize: (\d+) (?:#([^!]+))? ! (LOAD|STORE)"
)



def dumpMemPoints(input_file_name, outfile_name):

    # Lists to hold coordinates and colors
    x_coords = []
    y_coords = []
    colors = []

    points = []
    file_accesses = {}

    access_sizes = []
    access_per_point =  {}

    #outfile = open("mem_points.txt", 'w')

    # Parse the memory trace
    with open(input_file_name) as input_file:
        line = input_file.readline()
        #print(line)
        while line: 
            match = mem_trace_regex.search(line)
            if match:
                mem_addr = int(match.group(2), 16)
                mem_size = int(match.group(3))
                file_info = match.group(4)
                file_name, line_number = (file_info.split(":") + [None])[:2] if file_info else (None, None)
                #line_number = match.group(5)
                operation = match.group(5)

                #print(mem_addr, mem_size, file_name, line_number, operation)
                if not file_name:
                    continue

                # Split address space into 4 dimensions 
                # (0-15) (16-31) (32-47) (48-63)
                upper_half = (mem_addr >> 32) & 0xFFFFFFFF
                lower_half = mem_addr & 0xFFFFFFFF
                dim1 = (upper_half >> 16) & 0xFFFF
                dim2 = upper_half & 0xFFFF
                dim3 = (lower_half >> 16) & 0xFFFF
                dim4 = lower_half & 0xFFFF
                points.append((dim1,dim2,dim3,dim4))
                access_sizes.append(mem_size)

                #if(y < 0x0000FFFF and x < 0x0000FFFF):
                    #print("Skipping kernel memory access")
                    #print(y, x)
                #   continue
                #outfile.write(str(dim1))
                #outfile.write(',')
                #outfile.write(str(dim2))
                #outfile.write(',')
                #outfile.write(str(dim3))
                #outfile.write(',')
                #outfile.write(str(dim4))
                #outfile.write('\n')
            line = input_file.readline()

   # outfile.close()
    with open(outfile_name, 'w') as outfile:
        outfile.write(str(len(points)) + " " + str(len(points[0])) + "\n")
        for point, size in zip(points, access_sizes):
            outfile.write(' '.join(str(i) for i in point))
            outfile.write(" " + str(size))
            outfile.write("\n")

if __name__ == "__main__":
    
    ''' 
    intervals = [1, 10, 100, 1000]
    percentages = [0, 1, 2, 4, 8, 16]
    vertices = [8, 16, 32, 64, 128]
    options = ['', '_w', '_l', '_w_l']

    estimates = {}
    actual = {}

    for i in intervals: 
        for o in options: 
            for p in percentages:
                for v in vertices:
                    print(f"Reading file output{o}_{p}_{v}_{i}.txt")
                    if(os.path.exists(f"/scratch/must032/new/output{o}_{p}_{v}_{i}.txt")):
                        memory_trace = ''
                        with open(f"/scratch/must032/new/output{o}_{p}_{v}_{i}.txt") as trace_file:
                            line = trace_file.readline()

                            while line:
                                memory_trace += line
                                line = trace_file.readline()

                        outfile_name = f"Processed/processed{o}_{p}_{v}_{i}.txt" 
                        dumpMemPoints(memory_trace, i, outfile_name)
    
    

    
    intervals = [1, 10, 100, 1000]
    dims = [16, 32, 48, 64]
    modes = ['base', 'ord']

    for i in intervals:
        for d in dims:
            for m in modes: 
                print(f"Reading file output_{m}_{d}_{i}.txt")
                input_file_name = f"/people/must032/workloads/matrix_mul/performance-engineering/matrix_multiplication/output_{m}_{d}_{i}.txt"
                if(os.path.exists(input_file_name)):
                    outfile_name = f"Processed/matmul/processed_{m}_{d}_{i}.txt"
                    if(not os.path.exists(outfile_name)):
                        dumpMemPoints(input_file_name, outfile_name)
    #print(actual) 
    #print(estimates)
    
    '''

    input_filename = sys.argv[1]

    input_file = os.path.basename(input_filename)
    config = input_file[len("output_"):]
    outfile = f"Processed/matmul/processed_{config}"
    dumpMemPoints(input_filename, outfile)
    
       

