
import hwlib.hcdc.energy_model as energy_model

def analyze(entry,ad_prog):
  energy_fig,energy = energy_model.compute_energy(ad_prog, \
                                                  entry.runtime, \
                                                  entry.bandwidth)
  entry.set_energy(energy_fig)
