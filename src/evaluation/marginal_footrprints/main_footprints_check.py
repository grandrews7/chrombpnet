import pyBigWig
import pandas as pd
import numpy as np
from load_model import *
import os
import pyfaidx
import one_hot
import random
import pickle as pkl
import matplotlib.pyplot as plt
import argparse

parser=argparse.ArgumentParser(description="wrapper for marginal footprinting")
parser.add_argument("--gc_neg")
parser.add_argument("--ref_fasta")
parser.add_argument("--model_dir")
parser.add_argument("--motifs")
args = parser.parse_args() 

random.seed(1)

reference_genome_path=args.ref_fasta
gc_matched_negs = args.gc_neg
path=args.model_dir


reader = pyfaidx.Fasta(reference_genome_path)
neg_bed=pd.read_csv(gc_matched_negs,delimiter="\t", names=["chr", "start", "end", "name", "score", "strand", "pval", "qval", "qval2", "summit"])
neg_bed.head()

try:
    model=load_model_wrapper(model_hdf5=path+"model.0.hdf5")
except:
    model=load_model_wrapper(json_string=path+"model.0.arch", weights=path+"model.0.weights")

test_nonpeaks = neg_bed[(neg_bed["chr"]=="chr1")]


def get_seq(genome, peaks_df, width=2114):
    vals = []
    for i, r in peaks_df.iterrows():
        vals.append(str(genome[r['chr']][(r['start']+r['summit'] - width//2):(r['start'] + r['summit'] + width//2)]))
        
    return one_hot.dna_to_one_hot(vals)


def softmax(x, temp=1):
    norm_x = x - np.mean(x,axis=1, keepdims=True)
    return np.exp(temp*norm_x)/np.sum(np.exp(temp*norm_x), axis=1, keepdims=True)

test_nonpeaks_seqs = get_seq(reader, test_nonpeaks)
num=test_nonpeaks_seqs.shape[0]
print(num)

def profiles_for_motif(seqs, motif, model_peaks_corrected):
    random.shuffle(seqs)
  
    w_mot_seqs = seqs.copy()[0:num]
    w_mot_seqs[:, 1057:1057+len(motif)] = one_hot.dna_to_one_hot([motif])
    
    predictions = []
    
    for i in range(0,num,100):
        unplug_bias_pred = softmax(model_peaks_corrected.predict([w_mot_seqs[i:i+100]], 
                                                                       verbose=True)[0])
        predictions.extend(unplug_bias_pred)
    
    return predictions


if args.motifs == "tn5":
    motifs_to_test = ["GCACAGTACAGAGCTG", "GTGCACAGTTCTAGAGTGTGCAG", "CCTCTACACTGTGCAGAA", "GCACAGTTCTAGACTGTGCAG", "CTGCACAGTGTAGAGTTGTGC"]
    ylims=[0.06,0.06,0.06,0.06, 0.06] 
    #Tn5
elif args.motifs == "tn5_c":
    motifs_to_test = ["GCACAGTACAGAGCTG", "GTGCACAGTTCTAGAGTGTGCAG", "CCTCTACACTGTGCAGAA", "GCACAGTTCTAGACTGTGCAG", "CTGCACAGTGTAGAGTTGTGC"]
    ylims=[0.0015,0.0015,0.0015,0.0015, 0.0015] 
elif args.motifs == "dnase1":
    motifs_to_test = ["TTTACAAGTCCA", "TGTACTTACGAA"]
    #DNASE
elif args.motifs == "gm12878_motifs_set1":
    motifs_to_test = ["GCGCATGCGC", "CGATATGACTCATCCC", "TTGGCCACTAGGGGGCGCTAT", "CCGAAAGCGGAAGTGAGAC"]
    ylims=[0.004,0.003,0.02,0.004] 
    #NRF1, AP1, CTCF, ETS - GM12878
elif args.motifs == "gm12878_motifs_set2":
    motifs_to_test =  ["AAGGGGGCGGGGCCTAA", "CCCTAACCACAGCCC", "GCAAGGGAAATTCCCCAGG", "GATGG"]
    ylims=[0.002,0.002,0.003,0.002] 

    #SPI1, RUNX, NFKB, GATA1
else:
    pass

#motifs_to_test = ["ATAGCGCCCCCTAGTGGCCAA", "TTGGCCACTAGGGGGCGCTAT"]
#motifs_to_test = ["CCATTGTTATGCAAAT"]


predictions_motifs = []
for motif in motifs_to_test:
    pred_unplug_bias = profiles_for_motif(test_nonpeaks_seqs, motif, model)
    predictions_motifs.append(pred_unplug_bias)
    
def plot_tracks(pred_unplug_bias, ax=None, ylim=0.01, start=500-100+5, end=500+100+5 ):
    width = end - start
    ax.plot(range(width), pred_unplug_bias[:, start:end].mean(0))
    ax.set_ylim(0,ylim)   
    #plt.legend()

plt.rcParams["figure.figsize"] = (7*len(motifs_to_test),4)
fig, axs = plt.subplots(1, len(motifs_to_test))
 
i=0
for pred_unplug_bias in predictions_motifs:
    plot_tracks(np.array(pred_unplug_bias).reshape(num,1000), axs[i], ylim=ylims[i])
    i+=1

plt.savefig(os.path.join(path,args.motifs+"_footprint.png"))
#plt.show()
#p#kl.dump(pred_unplug_bias, open(output_file, "wb"))



