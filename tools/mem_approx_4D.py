import matplotlib.pyplot as plt
import numpy as np
import re
import math
import sys 
from sklearn.cluster import KMeans
#from kneed import KneeLocator
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from operator import itemgetter 
import time 

t1 = time.process_time() 

from fastkmeans import Sort, Dataset, kmeans_plusplus, Assignment, assign 

t2 = time.process_time()

print("FastKmeans Module load time: ", t2-t1)

# Regex to parse the memory trace
mem_trace_regex = re.compile(
        r"0x([0-9a-f]+) \| MemAddr: 0x([0-9a-f]+) \| MemSize: (\d+) (?:#([^!]+))? ! (LOAD|STORE)"
)



def getMemEstimate(memory_trace, interval):

    # Lists to hold coordinates and colors
    x_coords = []
    y_coords = []
    colors = []

    points_list = []
    file_accesses = {}

    size_map = {}
    access_per_point =  {}
    t1 = time.process_time()
    # Parse the memory trace
    trace_lines = memory_trace.strip().split('\n')
    for line in trace_lines:
        #print(line)
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

            # Extract bits for x and y coordinates
            # Example: use bits 32-63 for x and 0-31 for y
            #x = (mem_addr >> 32) & 0xFFFFFFFF
            #y = mem_addr & 0xFFFFFFFF
            #if(y < 0x0000FFFF and x < 0x0000FFFF):
                #print("Skipping kernel memory access")
                #print(y, x)
           #     continue

            # Choose color based on operation
            color = 'blue' if operation == 'LOAD' else 'red'

            # Split address space into 4 dimensions 
            # (0-15) (16-31) (32-47) (48-63)
            upper_half = (mem_addr >> 32) & 0xFFFFFFFF
            lower_half = mem_addr & 0xFFFFFFFF
            dim1 = (upper_half >> 16) & 0xFFFF
            dim2 = upper_half & 0xFFFF
            dim3 = (lower_half >> 16) & 0xFFFF
            dim4 = lower_half & 0xFFFF
            #x_coords.append(x)
            #y_coords.append(y)
            colors.append(color)
            points_list.append((dim1, dim2, dim3, dim4))
            if (dim1,dim2,dim3,dim4) in access_per_point:
                access_per_point[(dim1,dim2,dim3,dim4)] += 1
            else:
                access_per_point[(dim1,dim2,dim3,dim4)] = 1

            if (dim1,dim2,dim3,dim4) in size_map:
                if mem_size > size_map[(dim1,dim2,dim3,dim4)]:
                    size_map[(dim1,dim2,dim3,dim4)] = mem_size
            else:
                size_map[(dim1,dim2,dim3,dim4)] = mem_size

            if file_name not in file_accesses:
                file_accesses[file_name] = 0
        
            file_accesses[file_name] = file_accesses[file_name] + 1


    #print(points)
    t2 = time.process_time()
    print("PreProcess time: ", t2-t1)
    
    
    hot_zones = [] 
    num_hot = 0
    for key, value in access_per_point.items():
        if value > 1:
            #print(key, value)
            num_hot += 1
            hot_zones.append(key)

    cold_zones = []

    num_single = 0
    for (key, value) in access_per_point.items():
        if value == 1:
            #print(key, value)
            num_single += 1
            cold_zones.append(key)


    #wcss = []
    silhouettes = []
    #chi = []
    #dbi = []

    t1 = time.process_time()

    points = Dataset(len(points_list), 4) 
    for i, point in enumerate(points_list): 
        for j, dim in enumerate(point):
            points[i, j] = dim

    t2 = time.process_time()

    print("Dataset read time: ", t2-t1) 

    for i in range(2, 12):
        t1 = time.process_time() 
        initial_ctrs = kmeans_plusplus(points, i)
        a = Assignment(len(points_list))
        algorithm = Sort()
        assign(points, initial_ctrs, a)
        algorithm.initialize(points, i, a)
        iterations = algorithm.run(1000) #max_iteration = 1000 
        t2 = time.process_time()

        print(f"iteration {i} run time: {t2-t1}") 

        #clusterer = KMeans(n_clusters=i, init='k-means++', max_iter=300, n_init=10, random_state=2)
        #clusterer.fit(points)
        #wcss.append(clusterer.inertia_)
        #print(i, clusterer.inertia_)
        labels = [algorithm.get_assignment(i) for i, point in enumerate(points_list)]
        #labels = clusterer.labels_
        #print(i, clusterer.cluster_centers_)
        t1 = time.process_time()
        silhouette_avg = silhouette_score(points_list, labels)
        t2 = time.process_time() 

        print("Silhouette calculation time: ", t2-t1)
        #chi_avg = calinski_harabasz_score(points, labels)
        #dbi_avg = davies_bouldin_score(points, labels)
   
        #weighted_score = silhouette_avg * silhouette_avg / dbi_avg
        silhouettes.append((i, silhouette_avg)) 
        #chi.append((i, chi_avg))
        #dbi.append((i, dbi_avg))
    
    k = max(silhouettes, key = itemgetter(1))[0]
    algorithm = Sort()
    intial_ctrs = kmeans_plusplus(points, k)
    a = Assignment(len(points_list))
    assign(points, initial_ctrs, a)
    algorithm.initialize(points, k, a)
    iterations = algorithm.run(1000) # max_iteration = 1000
    labels = [algorithm.get_assignment(i) for i, point in enumerate(points_list)]
    centroids = algorithm.centers
    #kmeans = KMeans(n_clusters=k, init='k-means++', max_iter=1000, n_init=10, random_state=2)
    #kmeans.fit(points)

    #labels = kmeans.predict(points)
    #centroids = kmeans.cluster_centers_
    #print(centroids)

    clusters = {}

    num_address = len(set(points_list))
    total_mem_usage = sum(size_map.values())
    mem_ratio = total_mem_usage / num_address

    cluster_hot_zones = {}
    cluster_cold_zones = {}

    for label, point in zip(labels, points_list):
        if label not in clusters: 
            clusters[label] = []
        clusters[label].append(point)
        if label not in cluster_hot_zones:
            cluster_hot_zones[label] = []
        if point in hot_zones:
            cluster_hot_zones[label].append(point)
        if label not in cluster_cold_zones:
            cluster_cold_zones[label] = []
        if point in cold_zones:
            cluster_cold_zones[label].append(point)

    approx_mem = {}

    data_size = {}
    for label, points in clusters.items():
        distinct_points = set(points)
        points_in_cluster = len(distinct_points)
        reuse_ratio = len(points)/points_in_cluster 
        cluster_mem = sum([size_map[point] for point in distinct_points])
        cluster_cold_points = len(set(cluster_cold_zones[label]))
        cluster_hot_points = len(set(cluster_hot_zones[label]))
        if points_in_cluster == 1 and cluster_cold_points == 1:
            cluster_cold_points -= 1
            cluster_hot_points += 1
        approx_mem[label] = math.ceil(mem_ratio * (cluster_hot_points + cluster_cold_points*(interval**0.575)))

    if interval == 1: 
        return total_mem_usage, sum(approx_mem.values())
    else:
        return sum(approx_mem.values)


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
                    memory_trace = ''
                    with open(f"/people/must032/workloads/miniVite/new/output{o}_{p}_{v}_{i}.txt") as trace_file:
                        line = trace_file.readline()

                        while line:
                            memory_trace += line
                            line = trace_file.readline()

                    if i == 1:
                        actual[(o, p, v)] , estimates[(i, o, p, v)] = getMemEstimate(memory_trace, i)
                    else:
                        estimates[(i, o, p, v)] = getMemEstimate(memory_trace, i)

    print(actual) 
    print(estimates)
    '''

    memory_trace = ''
    with open(sys.argv[1]) as trace_file:
        line = trace_file.readline()

        while line:
            memory_trace += line
            line = trace_file.readline()

    interval = int(sys.argv[2])

    if interval == 1: 
        actual, estimate = getMemEstimate(memory_trace, interval) 
        print("Actual: ", actual)
    else: 
        estimate = getMemEstimate(memory_trace,interval)
    
    print("Estimate: ", estimate)
