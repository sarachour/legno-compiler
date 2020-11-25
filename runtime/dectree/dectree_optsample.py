import numpy as np

def count_valid(dectrees,sample):
    cnt = 0
    for dectree in dectrees:
        for leaf in dectree.leaves():
            if leaf.region.valid_code(sample):
                cnt += 1
    return cnt

def random_sample(dectrees,samples):
    new_samples = []
    for idx,node in enumerate(dectrees):
        samps = node.random_sample(new_samples + samples)
        new_samples += samps

    return new_samples
