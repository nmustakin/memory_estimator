import matplotlib.pyplot as plt
import numpy as np
import re
import math
import sys 
from sklearn.cluster import KMeans
from kneed import KneeLocator
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from operator import itemgetter 

# Regex to parse the memory trace
mem_trace_regex = re.compile(
        r"0x([0-9a-f]+) \| MemAddr: 0x([0-9a-f]+) \| MemSize: (\d+)(?: #(/[\w/\.]+):(\d+))? ! (LOAD|STORE)"
)

memory_trace = ''

with open(sys.argv[1], 'r') as trace_file:
    line = trace_file.readline()

    while line:
        memory_trace += line
        line = trace_file.readline()

interval = int(sys.argv[2])
# Lists to hold coordinates and colors
x_coords = []
y_coords = []
colors = []

points = []
source_files = []
file_accesses = {}

size_map = {}
access_per_point =  {}

# Parse the memory trace
trace_lines = memory_trace.strip().split('\n')
for line in trace_lines:
    match = mem_trace_regex.search(line)
    if match:
        mem_addr = int(match.group(2), 16)
        mem_size = int(match.group(3))
        file_name = match.group(4)
        line_number = match.group(5)
        operation = match.group(6)

        if not file_name:
            continue

        # Extract bits for x and y coordinates
        # Example: use bits 32-63 for x and 0-31 for y
        x = (mem_addr >> 32) & 0xFFFFFFFF
        y = mem_addr & 0xFFFFFFFF
        if(y < 0x0000FFFF and x < 0x0000FFFF):
            print("Skipping kernel memory access")
            print(y, x)
            continue

        # Choose color based on operation
        color = 'blue' if operation == 'LOAD' else 'red'

        x_coords.append(x)
        y_coords.append(y)
        colors.append(color)
        source_files.append(file_name)
        points.append((x,y))

        if (x,y) in access_per_point:
            access_per_point[(x,y)] += 1
        else:
            access_per_point[(x,y)] = 1

        if (x,y) in size_map:
            if mem_size > size_map[(x,y)]:
                size_map[(x,y)] = mem_size
        else:
            size_map[(x,y)] = mem_size

        if file_name not in file_accesses:
            file_accesses[file_name] = 0
        
        file_accesses[file_name] = file_accesses[file_name] + 1

#print(file_accesses)

#print(access_per_point)

#print("Hot zones") 

hot_zones = [] 
num_hot = 0
for key, value in access_per_point.items():
    if value > 1:
 #       print(key, value)
        num_hot += 1
        hot_zones.append(key)

#print("Total hot addresses: ", num_hot)
#print("Single Access")

cold_zones = []

num_single = 0
for (key, value) in access_per_point.items():
    if value == 1:
 #       print(key, value)
        num_single += 1
        cold_zones.append(key)

#print("Total single accesses: ", num_single)


for file_name in source_files:
    if file_accesses[file_name] == 1 and interval == 1:
        del points[source_files.index(file_name)]
        source_files.remove(file_name)

unique_files = np.unique(source_files)
#unique_files = unique_files[file_accesses[unique_files] != 1]
colors = plt.cm.get_cmap('tab10', len(unique_files))
file_to_color = {file_name: colors(i) for i, file_name in enumerate(unique_files)}

#print(unique_files)
#print(len(unique_files))

# Plotting
plt.figure(figsize=(10, 10))
for point, file_name in zip(points, source_files):
    plt.scatter(point[1], point[0], color=file_to_color[file_name], label=file_name, s=30, alpha=0.5)
#plt.scatter(y_coords, x_coords, c=colors, alpha=0.5)

handles, labels = plt.gca().get_legend_handles_labels()
by_label = dict(zip(labels, handles))
plt.legend(by_label.values(), by_label.keys())

plt.title('Memory Address Visualization')
plt.ylabel('Upper 32 bits of Address')
plt.xlabel('Lower 32 bits of Address')
plt.grid(True)
plt.savefig(f'MemoryMap_FileOnly_WithFileNam_{interval}.png')

'''

wcss = []
silhouettes = []
chi = []
dbi = []

for i in range(2, 12):
    clusterer = KMeans(n_clusters=i, init='k-means++', max_iter=300, n_init=10, random_state=2)
    clusterer.fit(points)
    wcss.append(clusterer.inertia_)
    #print(i, clusterer.inertia_)

    labels = clusterer.labels_

    silhouette_avg = silhouette_score(points, labels)
    chi_avg = calinski_harabasz_score(points, labels)
    dbi_avg = davies_bouldin_score(points, labels)
   
    weighted_score = silhouette_avg * silhouette_avg / dbi_avg
    print(
        "For n_clusters =",
        i,
        "Silhouette_score is :",
        silhouette_avg,
        " | CHI score is :",
        chi_avg, 
        " | DBI score is :",
        dbi_avg,
        " | Weighted score : ",
        weighted_score
    )
    silhouettes.append((i, silhouette_avg)) 
    chi.append((i, chi_avg))
    dbi.append((i, dbi_avg))
    #if(silhouette_avg > 0.999):
    #    break
    #if(dbi_avg < 0.0005):
    #    break

print(max(silhouettes, key = itemgetter(1))[0])
print(min(dbi, key = itemgetter(1))[0])

#print(wcss)
plt.figure(figsize=(10,10))
plt.plot(range(2, 26), wcss)
plt.title('Elbow Method')
plt.yscale('log')
plt.xlabel('Number of clusters')
plt.ylabel('WCSS')
plt.savefig('Elbow.png')


#kneedle = KneeLocator(range(1,11), wcss, curve='convex', direction = 'decreasing')

#print(kneedle.knee)
#print(kneedle.elbow)

'''

#k = kneedle.elbow
#k = max(silhouettes, key = itemgetter(1))[0]
#k = min(dbi, key = itemgetter(1))[0]
#print(k)
k = 5

kmeans = KMeans(n_clusters=k, init='k-means++', max_iter=1000, n_init=10, random_state=2)
kmeans.fit(points)

labels = kmeans.predict(points)
centroids = kmeans.cluster_centers_

clusters = {}

num_address = len(set(points))
total_mem_usage = sum(size_map.values())
mem_ratio = total_mem_usage / num_address

#print("Unique memory addresses: ", num_address)
#print("Total memory usage: ", total_mem_usage)
#print("Mem Usage Ratio: ", mem_ratio)

cluster_hot_zones = {}
cluster_cold_zones = {}

for label, point in zip(labels, points):
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

n_rows = int(k ** 0.5)
n_cols = int(k/n_rows) + (k % n_rows > 0)


fig, axs = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 5*n_rows))

if n_rows == 1 or n_cols == 1:
    axs = axs.flatten()
else:
    axs = axs.ravel()

for i, (label, cluster_points) in enumerate(clusters.items()):
    ax = axs[i]
    cluster_points = np.array(cluster_points)
    for point in cluster_points:
        #print(points.index((point[0], point[1])))
        #print(source_files[points.index(point)])
        ax.scatter(point[1], point[0], color=file_to_color[source_files[points.index((point[0], point[1]))]])
    #ax.scatter(cluster_points[:, 1], cluster_points[:, 0], color=file_to_color[source_files[points.index(cluster_points)]])
    ax.scatter(centroids[label][1], centroids[label][0], color='red', label='Centroid', marker='x', s=100)
    ax.set_title(f'Cluster {label}')
    ax.legend(loc='center left', bbox_to_anchor=(0.7, 0.3))
    ax.grid(True)

for ax in axs[len(clusters):]:
    ax.set_visible(False)

#fig.legend(file_to_color.values(), file_to_color.keys(), bbox_to_anchor=(0.7, 0.3))

plt.tight_layout()
plt.savefig(f'Clusters_FileOnly_{k}_{interval}.png')

approx_mem = {}

data_size = {}
for label, points in clusters.items():
    min_y = min(points, key = itemgetter(0))[0]
    max_y = max(points, key = itemgetter(0))[0]
    min_x = min(points, key = itemgetter(1))[1]
    max_x = max(points, key = itemgetter(1))[1]
    
    data_size[label] = (max_x - min_x + 1)*(max_y - min_y + 1)
    distinct_points = set(points)
    points_in_cluster = len(distinct_points)
    reuse_ratio = len(points)/points_in_cluster 
    cluster_mem = sum([size_map[point] for point in distinct_points])
    cluster_cold_points = len(set(cluster_cold_zones[label]))
    cluster_hot_points = len(set(cluster_hot_zones[label]))
    if points_in_cluster == 1 and cluster_cold_points == 1:
        cluster_cold_points -= 1
        cluster_hot_points += 1
 #   print("Cluster ID, Envelop Size, Points in Cluster, ClusterMem") 
 #   print(label, data_size[label], points_in_cluster, cluster_mem)
 #   print("Mem usage ratio: ", cluster_mem/len(set(points)))
 #   print("Reuse rate: ", reuse_ratio)
 #   print("Hot points: ", cluster_hot_points)
 #   print("Cold points: ", cluster_cold_points)
    #print("MIN and MAX: ", min_y, max_y, min_x, max_x)
    #approx_mem[label] = math.ceil(mem_ratio * points_in_cluster * interval * (1/ reuse_ratio**(interval**0.5)))
    approx_mem[label] = math.ceil(mem_ratio * (cluster_hot_points + cluster_cold_points*(interval**0.575)))

 #   print("Approximated memory usage: ", approx_mem[label])

print("Total approximated memory usage: ", sum(approx_mem.values()))

