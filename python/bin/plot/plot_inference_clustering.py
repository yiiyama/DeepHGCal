import numpy as np
import os
import sys
import argparse
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import math
import gzip
import pickle
import configparser as cp
from libs.plots import plot_clustering
from matplotlib import cm
from matplotlib.colors import LogNorm
import matplotlib.backends.backend_pdf



parser = argparse.ArgumentParser(description='Plot clustering model output')
parser.add_argument('input', help="Path to the config file which was used to train")
parser.add_argument('config', help="Config section within the config file")
args = parser.parse_args()

config_file = cp.ConfigParser()
config_file.read(args.input)
config = config_file[args.config]

spatial_features_indices = tuple([int(x) for x in (config['input_spatial_features_indices']).split(',')])
spatial_features_local_indices = tuple([int(x) for x in (config['input_spatial_features_local_indices']).split(',')])
other_features_indices = tuple([int(x) for x in (config['input_other_features_indices']).split(',')])
target_indices = tuple([int(x) for x in (config['target_indices']).split(',')])


energy_values = []
histogram_values_resolution=[]
loss_values = []
position_values = []

with open(os.path.join(config['test_out_path'], 'inference_output_files.txt')) as f:
    content = f.readlines()
    for i in content:
        with gzip.open(i.strip()) as f:
            data=pickle.load(f)
            for j in data:
                input, num_entries, output = j
                output = np.nan_to_num(output[:,0:2])

                spatial = input[:, spatial_features_indices]
                targets = input[:, target_indices]
                energy = input[:,other_features_indices][:,0]

                num_entries = float(np.asscalar(num_entries))

                diff_sq_1 = (output - targets) ** 2 * energy[:, np.newaxis]  # TODO: Multiply by sequence mask
                loss_1 = ((1/num_entries)*np.sum(diff_sq_1) / np.sum(energy, axis=-1)) * float(num_entries!=0)

                diff_sq_2 = (output - (1-targets)) ** 2 * energy[:, np.newaxis]  # TODO: Multiply by sequence mask
                loss_2 = ((1/num_entries)*np.sum(diff_sq_2) / np.sum(energy, axis=-1)) * float(num_entries!=0)

                shower_indices = np.argmin(np.array([loss_1, loss_2]))


                if loss_1 < loss_2:
                    sorted_target = targets
                else:
                    sorted_target = 1-targets

                perf1 = np.sum(output[:,0]*energy) / np.sum(sorted_target[:,0] * energy)
                perf2 = np.sum(output[:,1]*energy) / np.sum(sorted_target[:,1] * energy)

                truth_energy_sum_1 = np.sum(sorted_target[:,0] * energy)
                truth_energy_sum_2 = np.sum(sorted_target[:,1] * energy)

                if max(truth_energy_sum_2, truth_energy_sum_1) < 70000:
                    sorted_target_energies_extended_1 = (sorted_target[:,0] * energy)[..., np.newaxis]
                    sorted_target_energies_extended_2 = (sorted_target[:,1] * energy)[..., np.newaxis]

                    position_shower_1 = np.sum(spatial * sorted_target_energies_extended_1, axis=0)/np.sum(sorted_target_energies_extended_1)
                    position_shower_2 = np.sum(spatial * sorted_target_energies_extended_2, axis=0)/np.sum(sorted_target_energies_extended_2)

                    histogram_values_resolution.append(perf1)
                    energy_values.append(truth_energy_sum_1)
                    histogram_values_resolution.append(perf2)
                    energy_values.append(truth_energy_sum_2)
                    position_values.append(position_shower_1)
                    position_values.append(position_shower_2)

                    loss_values.append(min(loss_1, loss_2))

                    # a = plt.figure(0)
                    # a.suptitle('Output')
                    # b = plt.figure(1)
                    # b.suptitle('GT')
                    # plot_clustering(spatial=spatial, energy=energy, prediction=output, fig=a)
                    # plot_clustering(spatial=spatial, energy=energy, prediction=sorted_target, fig=b)
                    # print("%05.5f %05.5f %05.5f %05.5f" % (loss_1, loss_2, perf1, perf2))
                    # plt.show()


mean = np.mean(histogram_values_resolution)
variance = np.var(histogram_values_resolution)
loss_mean = np.mean(loss_values)
loss_variance = np.var(loss_values)


def get_mean_variance_histograms(energy_values, histogram_values_resolution):
    nbins=20
    min_value = np.min(energy_values)
    max_value = np.max(energy_values)

    bin_index = np.minimum((energy_values - min_value)*nbins/(max_value-min_value), nbins-1).astype(np.int64)

    energy_values_x = np.linspace(min_value, max_value, num=nbins)

    resolution_sum = np.zeros(nbins, dtype=np.float64)
    square_difference = np.zeros(nbins, dtype=np.float64)
    count = np.zeros(nbins, dtype=np.int64)

    for i in range(len(energy_values)):
        resolution_sum[bin_index[i]] += histogram_values_resolution[i]
        count[bin_index[i]] += 1

    mean_resolution_values = resolution_sum/count
    # mean_resolution_values[count==0]=0

    for i in range(len(energy_values)):
        square_difference[bin_index[i]] += float(histogram_values_resolution[i] - mean_resolution_values[bin_index[i]])**2

    varaince_resolution_values = square_difference / (count)

    # mean_resolution_values[(count-1)==0]=0
    # mean_resolution_values[(count)==0]=0

    return mean_resolution_values, varaince_resolution_values, energy_values_x, count


def diff_2d_plot(energy_values, histogram_values_resolution):
    nbins=10
    energy_values_1 = energy_values[0::2]
    energy_values_2 = energy_values[1::2]
    min_energy, max_energy = np.min(energy_values), np.max(energy_values)

    energy_values_x = np.linspace(min_energy, max_energy, num=nbins)

    bin_indices_x = np.minimum((energy_values_1 - min_energy)*nbins/(max_energy-min_energy), nbins-1).astype(np.int64)
    bin_indices_y = np.minimum((energy_values_2 - min_energy)*nbins/(max_energy-min_energy), nbins-1).astype(np.int64)

    mean_2d = np.zeros((nbins,nbins), dtype=np.float32)
    variance_2d = np.zeros((nbins,nbins), dtype=np.float32)
    freq_2d = np.zeros((nbins,nbins), dtype=np.int64)

    for i in range(len(energy_values_1)):
        mean_2d[bin_indices_y[i], bin_indices_x[i]] += histogram_values_resolution[i*2]
        mean_2d[bin_indices_x[i], bin_indices_y[i]] += histogram_values_resolution[i*2+1]
        freq_2d[bin_indices_y[i], bin_indices_x[i]] += 1
        freq_2d[bin_indices_x[i], bin_indices_y[i]] += 1

    mean_2d /= freq_2d

    for i in range(len(energy_values_1)):
        variance_2d[bin_indices_y[i], bin_indices_x[i]] += float(histogram_values_resolution[i*2] - mean_2d[bin_indices_y[i], bin_indices_x[i]])**2
        variance_2d[bin_indices_x[i], bin_indices_y[i]] += float(histogram_values_resolution[i*2+1] - mean_2d[bin_indices_x[i], bin_indices_y[i]])**2

    variance_2d = variance_2d/(freq_2d)

    mean_2d[freq_2d == 0] = 0
    variance_2d[freq_2d == 0] = 0

    mean_2d = np.flip(mean_2d, axis=0)
    freq_2d = np.flip(freq_2d, axis=0)
    variance_2d = np.flip(variance_2d, axis=0)


    return mean_2d, variance_2d, freq_2d, energy_values_x


def make_shower_energy_plots(energy_values, histogram_values_resolution):
    nbinsx=10
    nbinsy=4
    energy_values_1 = energy_values[0::2]
    energy_values_2 = energy_values[1::2]
    min_energy, max_energy = np.min(energy_values), np.max(energy_values)

    energy_values_x = np.linspace(min_energy, max_energy, num=nbinsx)

    bin_indices_x = np.minimum((energy_values - min_energy)*nbinsx/(max_energy-min_energy), nbinsx-1).astype(np.int64)

    bin_indices_y = np.zeros(energy_values.shape).astype(np.int32)
    bin_indices_y[energy_values < 5000] = 0
    bin_indices_y[(energy_values > 5000) & (energy_values < 10000)] = 1
    bin_indices_y[(energy_values > 10000) & (energy_values < 20000)] = 2
    bin_indices_y[energy_values > 20000] = 3

    mean_2d = np.zeros((nbinsy,nbinsx), dtype=np.float32)
    variance_2d = np.zeros((nbinsy,nbinsx), dtype=np.float32)
    freq_2d = np.zeros((nbinsy,nbinsx), dtype=np.int64)

    for i in range(len(energy_values_1)):
        if histogram_values_resolution[i*2] < 3:
            mean_2d[bin_indices_y[i*2], bin_indices_x[i*2+1]] += histogram_values_resolution[i*2]
            freq_2d[bin_indices_y[i*2], bin_indices_x[i*2+1]] += 1
        if histogram_values_resolution[i*2+1] < 3:
            mean_2d[bin_indices_y[i*2+1], bin_indices_x[i*2]] += histogram_values_resolution[i*2+1]
            freq_2d[bin_indices_y[i*2+1], bin_indices_x[i*2]] += 1

    mean_2d /= freq_2d

    for i in range(len(energy_values_1)):
        if histogram_values_resolution[i*2] < 3:
            variance_2d[bin_indices_y[i*2], bin_indices_x[i*2+1]] += float(histogram_values_resolution[i*2] - mean_2d[bin_indices_y[i*2], bin_indices_x[i*2+1]])**2
        if histogram_values_resolution[i * 2 + 1] < 3:
            variance_2d[bin_indices_y[i*2+1], bin_indices_x[i*2]] += float(histogram_values_resolution[i*2+1] - mean_2d[bin_indices_y[i*2+1], bin_indices_x[i*2]])**2
    variance_2d = variance_2d/(freq_2d)

    mean_2d[freq_2d == 0] = 0
    variance_2d[freq_2d == 0] = 0

    plt.figure()
    plt.plot(np.linspace(min_energy, max_energy, nbinsx), mean_2d[0], label='E<5000')
    plt.plot(np.linspace(min_energy, max_energy, nbinsx), mean_2d[1], label='5000<E<10000')
    plt.plot(np.linspace(min_energy, max_energy, nbinsx), mean_2d[2], label='10000<E<20000')
    plt.plot(np.linspace(min_energy, max_energy, nbinsx), mean_2d[3], label='E>20000')
    # plt.legend('1', '2', '3', '4', '5')
    plt.xlabel('Noise shower energy')
    plt.ylabel("Response of test shower (mean)")
    plt.legend()


    plt.figure()
    plt.plot(np.linspace(min_energy, max_energy, nbinsx), variance_2d[0], label='E<1000')
    plt.plot(np.linspace(min_energy, max_energy, nbinsx), variance_2d[1], label='5000<E<10000')
    plt.plot(np.linspace(min_energy, max_energy, nbinsx), variance_2d[2], label='10000<E<20000')
    plt.plot(np.linspace(min_energy, max_energy, nbinsx), variance_2d[3], label='E>20000')
    # plt.legend('1', '2', '3', '4', '5')
    plt.xlabel('Noise shower energy')
    plt.ylabel("Response of test shower (variance)")
    plt.legend()


def make_distance_plots(energy_values, position_values, values_resolution):
    nbinsy=4
    nbinsx=10
    position_values = np.array(position_values)
    position_values_1 = position_values[0::2]
    position_values_2 = position_values[1::2]
    distances = np.sqrt(np.sum((position_values_1 - position_values_2)**2, axis=-1))
    distances_repeated = np.repeat(distances, 2)

    min_energy, max_energy = np.min(energy_values), np.max(energy_values)
    min_distance, max_distance = np.min(distances), np.max(distances)

    mean_2d = np.zeros((nbinsy,nbinsx), dtype=np.float32)
    variance_2d = np.zeros((nbinsy,nbinsx), dtype=np.float32)
    freq_2d = np.zeros((nbinsy,nbinsx), dtype=np.int64)

    bin_indices_y = np.zeros(energy_values.shape).astype(np.int32)
    bin_indices_y[energy_values < 5000] = 0
    bin_indices_y[(energy_values > 5000) & (energy_values < 10000)] = 1
    bin_indices_y[(energy_values > 10000) & (energy_values < 20000)] = 2
    bin_indices_y[energy_values > 20000] = 3

    print(np.sum(energy_values<1000), np.sum((energy_values > 1000) & (energy_values < 10000)), np.sum((energy_values > 10000) & (energy_values < 20000)), np.sum(energy_values > 20000))

    bin_indices_x = np.minimum((distances_repeated - min_distance)*nbinsx/(max_distance-min_distance), nbinsx-1).astype(np.int64)

    for i in range(len(values_resolution)):
        if values_resolution[i] < 3:
            mean_2d[bin_indices_y[i], bin_indices_x[i]] += values_resolution[i]
            freq_2d[bin_indices_y[i], bin_indices_x[i]] += 1

    print(freq_2d)
    print(np.sum(freq_2d, axis=1))

    mean_2d /= freq_2d

    print(mean_2d)

    for i in range(len(values_resolution)):
        if values_resolution[i] < 3:
            variance_2d[bin_indices_y[i], bin_indices_x[i]] += float(values_resolution[i] - mean_2d[bin_indices_y[i], bin_indices_x[i]])**2

    variance_2d = variance_2d/(freq_2d)

    mean_2d[freq_2d == 0] = 0
    variance_2d[freq_2d == 0] = 0

    variance_2d = np.flip(variance_2d, axis=0)

    energy_max_values = np.power(10, np.log10(max_energy-min_energy+1)/5*(np.arange(5)+1))+min_energy

    plt.figure()
    plt.plot(np.linspace(min_distance, max_distance, nbinsx), mean_2d[0], label='E<5000')
    plt.plot(np.linspace(min_distance, max_distance, nbinsx), mean_2d[1], label='5000<E<10000')
    plt.plot(np.linspace(min_distance, max_distance, nbinsx), mean_2d[2], label='10000<E<20000')
    plt.plot(np.linspace(min_distance, max_distance, nbinsx), mean_2d[3], label='E>20000')
    # plt.legend('1', '2', '3', '4', '5')
    plt.xlabel('Distance')
    plt.ylabel("Resolution (mean)")
    plt.legend()


    plt.figure()
    plt.plot(np.linspace(min_distance, max_distance, nbinsx), variance_2d[0], label='E<1000')
    plt.plot(np.linspace(min_distance, max_distance, nbinsx), variance_2d[1], label='5000<E<10000')
    plt.plot(np.linspace(min_distance, max_distance, nbinsx), variance_2d[2], label='10000<E<20000')
    plt.plot(np.linspace(min_distance, max_distance, nbinsx), variance_2d[3], label='E>20000')
    # plt.legend('1', '2', '3', '4', '5')
    plt.xlabel('Distance')
    plt.ylabel("Resolution (variance)")
    plt.legend()



energy_values = np.array(energy_values)


make_distance_plots(energy_values, position_values, histogram_values_resolution)
make_shower_energy_plots(energy_values, histogram_values_resolution)

resolution_mean_fo_energy, resolution_variance_fo_energy, energy_values_x, count = get_mean_variance_histograms(energy_values, histogram_values_resolution)
mean_2d, variance_2d, count_2d, energy_values_x_2d = diff_2d_plot(energy_values, histogram_values_resolution)

accuracy = float(np.sum((np.array(histogram_values_resolution)>0.7) & (np.array(histogram_values_resolution)<1.3)))/float(np.size(np.array(histogram_values_resolution)))
variance_from_1 = np.mean((np.array(histogram_values_resolution)-1)**2)

output_string = str(("Resolution mean:", mean, "Resolution variance :", variance, "Loss mean:", loss_mean, "Loss variance:", loss_variance, "Accuracy", accuracy, "Variance from 1", variance_from_1))

print("Samples tested", np.alen(histogram_values_resolution)/2)
print(output_string)

plt.figure()
bins = np.linspace(-0.1,3.1,num=32)
histogram_values_resolution_2 = np.copy(histogram_values_resolution)
histogram_values_resolution_2[histogram_values_resolution_2<0.2] = -0.05
histogram_values_resolution_2[histogram_values_resolution_2>2.8] = 3.05
plt.hist(histogram_values_resolution_2, bins=bins)
plt.ylabel('Frequency')
plt.xlabel("Resolution")

plt.figure()
plt.plot(energy_values_x, count)
plt.xlabel("Energy")
plt.ylabel('Frequency')



plt.figure()
plt.plot(energy_values_x, resolution_mean_fo_energy)
plt.xlabel("Energy")
plt.ylabel('Resolution (mean)')


plt.figure()
plt.plot(energy_values_x, resolution_variance_fo_energy)
plt.xlabel("Energy")
plt.ylabel('Resolution (variance)')


fig = plt.figure()
cax = plt.imshow(mean_2d, interpolation='nearest', extent=[np.min(energy_values_x_2d), np.max(energy_values_x_2d), np.min(energy_values_x_2d), np.max(energy_values_x_2d)], vmin=0, vmax=5)
plt.xlabel("Test shower energy")
plt.ylabel("Noise shower energy")
plt.title("Response of test shower (mean)")
cbar = fig.colorbar(cax)


fig = plt.figure()
cax = plt.imshow(variance_2d, interpolation='nearest', extent=[np.min(energy_values_x_2d), np.max(energy_values_x_2d), np.min(energy_values_x_2d), np.max(energy_values_x_2d)])
plt.xlabel("Test shower energy")
plt.ylabel("Noise shower energy")
plt.title("Response of test shower (variance)")
cbar = fig.colorbar(cax)


fig = plt.figure()
cax = plt.imshow(count_2d, interpolation='nearest', extent=[np.min(energy_values_x_2d), np.max(energy_values_x_2d), np.min(energy_values_x_2d), np.max(energy_values_x_2d)], )
plt.xlabel("Test shower energy")
plt.ylabel("Noise shower energy")
plt.title("Frequency")
cbar = fig.colorbar(cax)
# plt.savefig(os.path.join(config['test_out_path'], 'frequency_2d_fo_energy.png'))


histogram_values_resolution_3 = np.copy(histogram_values_resolution)
histogram_values_resolution_3 = histogram_values_resolution_3[histogram_values_resolution_3<=2.5]
histogram_values_resolution_3 = histogram_values_resolution_3[histogram_values_resolution_3 >=0.05]
output_string_3 = str(("Inlier resolution mean:", np.mean(histogram_values_resolution_3), "Inlier resolution variance :",
                       np.var(histogram_values_resolution_3),
                      "Efficiency", str(np.alen(histogram_values_resolution_3)/float(np.alen(histogram_values_resolution)))))
print(output_string_3)



with open(os.path.join(config['test_out_path'], 'test_summary.txt'), "w") as text_file:
    text_file.write(output_string)

pdf = matplotlib.backends.backend_pdf.PdfPages(os.path.join(config['test_out_path'], 'plots.pdf'))
for fig in range(1, plt.gcf().number + 1): ## will open an empty extra figure :(
    pdf.savefig( fig )
pdf.close()