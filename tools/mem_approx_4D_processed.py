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


# Regex to parse the memory trace
mem_trace_regex = re.compile(
        r"0x([0-9a-f]+) \| MemAddr: 0x([0-9a-f]+) \| MemSize: (\d+) (?:#([^!]+))? ! (LOAD|STORE)"
)



def getMemEstimate(input_file_name, interval):

    access_per_point = {}
    size_map = {}
    
    points_list = [] 
    t1 = time.process_time()

    with open(input_file_name) as f:
        text = f.readlines()
        n,d = map(int, text[0].strip().split())
        points = Dataset(n, d)

        for i, line in enumerate(text[1:n+1]):
            vals = tuple(map(float, line.strip().split()))
            #print(vals)
            points_list.append(vals[:-1])
            for j in range(d): 
                points[i, j] = vals[j]

            mem_size = vals[-1]
            key = vals[:-1]
            if key in access_per_point:
                access_per_point[key] += 1
            else:
                access_per_point[key] = 1

            if key in size_map:
                if mem_size > size_map[key]:
                    size_map[key] = mem_size
            else:
                size_map[key] = mem_size



    #print(points)
    t2 = time.process_time()
    #print("File Read time: ", t2-t1)
    
    
    hot_zones = [] 
    num_hot = 0
    cold_zones = []
    num_single = 0
    for key, value in access_per_point.items():
        if value > 1:
            #print(key, value)
            num_hot += 1
            hot_zones.append(key)
        else: 
            num_single += 1
            cold_zones.append(key)


    silhouettes = []

    for i in range(2, 12):
        t1 = time.process_time() 
        initial_ctrs = kmeans_plusplus(points, i)
        a = Assignment(n)
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
        #print(labels)
        #labels = clusterer.labels_
        #print(i, clusterer.cluster_centers_)
        t1 = time.process_time()
        #silhouette_avg = silhouette_score(points_list, labels)
        sse = algorithm.get_sse()
        t2 = time.process_time() 
        print("SSE time: ", t2-t1, " SSE: ", sse) 
        #print(silhouette_avg)
        #print("Silhouette calculation time: ", t2-t1)
        
        #chi_avg = calinski_harabasz_score(points, labels)
        #dbi_avg = davies_bouldin_score(points, labels)
   
        #weighted_score = silhouette_avg * silhouette_avg / dbi_avg
        silhouettes.append((i, sse)) 
        #chi.append((i, chi_avg))
        #dbi.append((i, dbi_avg))
    
    k = min(silhouettes, key = itemgetter(1))[0]
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
        approx_mem[label] = math.ceil(mem_ratio * ((2)**math.log(interval) * cluster_hot_points + cluster_cold_points*(interval**0.45)))

    if interval == 1: 
        return total_mem_usage, sum(approx_mem.values())
    else:
        return sum(approx_mem.values())


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

    input_file_name = sys.argv[1]
    interval = int(sys.argv[2])

    if interval == 1: 
        actual, estimate = getMemEstimate(input_file_name, interval) 
        print("Actual: ", actual)
    else: 
        estimate = getMemEstimate(input_file_name,interval)
    
    print("Estimate: ", estimate)
