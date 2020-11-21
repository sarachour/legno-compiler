import numpy as np

def count_valid(dectrees,sample):
    cnt = 0
    for dectree in dectrees:
        for leaf in dectree.leaves():
            if leaf.region.valid_code(sample):
                cnt += 1
    return cnt

def random_sample(dectrees,samples):
    n_tries = 100
    new_samples = samples
    for idx,node in enumerate(dectrees):
        total_samples = []
        total_sample_scores = []
        for _ in range(n_tries):
            for new_sample in node.random_sample(new_samples):
                score = count_valid(dectrees[idx:],new_sample)
                total_samples.append(new_sample)
                total_sample_scores.append(score)


        if len(total_samples) == 0:
            continue

        indices = np.argsort(total_sample_scores)
        best_samples = list(map(lambda idx: total_samples[idx], \
                                indices[0:node.min_sample()]))
        new_samples += best_samples
        print(max(total_sample_scores),min(total_sample_scores))

    return new_samples
