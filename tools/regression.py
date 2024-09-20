import numpy as np
from scipy.optimize import curve_fit

# Define the function to fit
def memory_estimate(sampling_rate, cluster_size, avg_bytes_per_req, reuse_ratio, alpha):
    return cluster_size * sampling_rate * avg_bytes_per_req * (1 / np.log1p(reuse_ratio)**alpha)

# Compile the data
# Assuming these arrays are ordered consistently
sampling_rates = np.array([1, 1, 1, 1, 1, 10, 10, 10, 10, 100, 100, 100, 100, 100, 1000, 1000, 1000, 1000])
cluster_sizes = np.array([224, 216, 232, 1, 1, 126, 120, 93, 1, 31, 37, 5, 4, 1, 6, 2, 3, 1])
avg_bytes_per_reqs = np.array([7.228, 7.228, 7.228, 7.228, 7.228, 7.312, 7.312, 7.312, 7.312, 7.2658, 7.2658, 7.2658, 7.2658, 7.2658, 7.666, 7.666, 7.666, 7.666])
reuse_ratios = np.array([17.875, 18.39, 6.069, 8, 17, 3.12, 7.116, 1.47, 1, 1.1935, 1.378, 1, 1.25, 1, 1.0, 1.0, 1.0, 1.0])

initial_guess = [1] 


def total_memory_usage(alpha):
    estimates = memory_estimate(sampling_rates, cluster_sizes, avg_bytes_per_reqs, reuse_ratios, alpha)
    return np.sum(estimates)


target_total_memory = 4872

# Perform the curve fitting
popt, _ = curve_fit(lambda x, a: total_memory_usage(a)- target_total_memory, reuse_ratios, [0], p0=initial_guess)

# Print the estimated alpha
print("Estimated alpha:", popt[0])

