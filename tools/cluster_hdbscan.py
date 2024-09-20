import matplotlib.pyplot as plt
import numpy as np
import re
import sys 
#import hdbscan
from sklearn.cluster import HDBSCAN
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from operator import itemgetter 

# Regex to parse the memory trace
mem_trace_regex = re.compile(
    r"0x([0-9a-f]+) \| MemAddr: 0x([0-9a-f]+)(?: #(/[\w/\.]+):(\d+))? ! (LOAD|STORE)"
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
file_accesses = {}

# Parse the memory trace
trace_lines = memory_trace.strip().split('\n')
for line in trace_lines:
    match = mem_trace_regex.search(line)
    if match:
        mem_addr = int(match.group(2), 16)
        file_name = match.group(3)
        line_number = match.group(4)
        operation = match.group(5)

        if not file_name:
            continue

        # Extract bits for x and y coordinates
        # Example: use bits 32-63 for x and 0-31 for y
        x = (mem_addr >> 32) & 0xFFFFFFFF
        y = mem_addr & 0xFFFFFFFF
        if(y < 0x0000FFFF and x < 0x00FFFFFF):
            print("Skipping kernel memory access")
            print(y, x)
            continue

        # Choose color based on operation
        color = 'blue' if operation == 'LOAD' else 'red'

        x_coords.append(x)
        y_coords.append(y)
        colors.append(color)
        points.append((x,y))

        if file_name not in file_accesses:
            file_accesses[file_name] = 0
        
        file_accesses[file_name] = file_accesses[file_name] + 1


#print(file_accesses)

# Plotting
plt.figure(figsize=(10, 10))
plt.scatter(y_coords, x_coords, c=colors, alpha=0.5)
plt.title('Memory Address Visualization')
plt.ylabel('Upper 32 bits of Address')
plt.xlabel('Lower 32 bits of Address')
plt.grid(True)
plt.savefig(f'MemoryMap_FileOnly_{interval}.png')

clusterer = HDBSCAN(
            min_cluster_size=int(5),
            min_samples=5,
            cluster_selection_method='eom',
            allow_single_cluster=True,
            metric='euclidean',
            algorithm='auto',
            leaf_size=30
        )

clusterer.fit(points)

labels = clusterer.labels_
silhouette_avg = silhouette_score(points, labels)

#print(clusterer.centroids_)

#print(clusterer.medoids_)


print("Clusters = ", len(set(labels)))
print("Silhouette score: ", silhouette_avg)

plt.figure(figsize=(10, 10))
plt.scatter(y_coords, x_coords, c=clusterer.labels_,
                    cmap='viridis', s=50, alpha=0.7, edgecolors='k')
plt.colorbar()
plt.title('HDBSCAN Clustering')
plt.xlabel('Lower 32 bits')
plt.ylabel('Upper 32 bits')
plt.savefig(f'HDBSCAN_clusters_{interval}.png')

'''

n_rows = int(k ** 0.5)
n_cols = int(k/n_rows) + (k % n_rows > 0)


fig, axs = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 5*n_rows))

if n_rows == 1 or n_cols == 1:
    axs = axs.flatten()
else:
    axs = axs.ravel()

for i, (label, points) in enumerate(clusters.items()):
    ax = axs[i]
    cluster_points = np.array(points)
    ax.scatter(cluster_points[:, 1], cluster_points[:, 0])
    ax.scatter(centroids[label][1], centroids[label][0], color='red', label='Centroid', marker='x', s=100)
    ax.set_title(f'Cluster {label}')
    ax.legend()
    ax.grid(True)

for ax in axs[len(clusters):]:
    ax.set_visible(False)

plt.tight_layout()
plt.savefig(f'Clusters_FileOnly_{k}_{interval}.png')
'''
