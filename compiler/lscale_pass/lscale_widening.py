import compiler.lscale_pass.lscale_harmonize as harmlib

def widen_modes(block,config):
    all_modes = list(block.modes)
    modes_subset = set(all_modes)

    for out in block.outputs:
      # idealized relation
      baseline = out.relation[config.modes[0]]
      deviations = list(map(lambda mode: out.relation[mode], all_modes))
      _, modes, _ = harmlib.get_master_relation(baseline, \
                                                deviations, \
                                                all_modes)
      modes_subset = modes_subset.intersection(set(modes))
    return modes_subset
