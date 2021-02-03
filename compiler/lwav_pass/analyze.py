from hwlib.adp import ADP,ADPMetadata
from dslang.dsprog import DSProgDB

import compiler.lwav_pass.waveform as wavelib
import numpy as np

def get_reference_waveforms(program,dssim):
    times,value_dict = program.execute(dssim)
    waveforms = {}
    for varname,values in value_dict.items():
        wav = wavelib.Waveform(variable=varname, \
                               times=times, \
                               values=values, \
                               time_units=wavelib.Waveform.TimeUnits.DS_TIME_UNITS, \
                               ampl_units=wavelib.Waveform.AmplUnits.DS_QUANTITY, \
                               time_scale=1.0, \
                               mag_scale=1.0)
        waveforms[varname] = wav
        print("-> calculated reference <%s>" % varname)

    return waveforms

def reference_waveform(adp,waveform):
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])
    dssim = DSProgDB.get_sim(program.name)
    dsinfo = DSProgDB.get_info(program.name)
    ref_waveforms = get_reference_waveforms(program,dssim)

    reference = ref_waveforms[waveform.variable]
    return program,dsinfo,reference

def align_waveform(adp,reference,waveform):

    rec_experimental = waveform.start_from_zero().recover()
    print("unrec-time: [%f,%f]" % (min(waveform.times), \
          max(waveform.times)))
    print("rec-time: [%f,%f]" % (min(rec_experimental.times), \
          max(rec_experimental.times)))

    timing_error = 2e-5
    scale_error = max(timing_error/waveform.runtime,0.02)
    offset_error = 0.0002*(rec_experimental.runtime/waveform.runtime)

    rec_exp_aligned = reference.align(rec_experimental, \
                                      scale_slack=scale_error, \
                                      offset_slack=offset_error)
    rec_exp_aligned.trim(reference.min_time, reference.max_time)

    return rec_exp_aligned

def plot_waveform(adp,waveform):
    program,dsinfo,reference = reference_waveform(adp,waveform)

    ref_color = "#E74C3C"
    meas_color = "#5758BB"
    ylabel = "%s (%s)" % (dsinfo.observation,dsinfo.units)
    vis = wavelib.WaveformVis("meas",ylabel,program.name)
    vis.set_style('meas',meas_color,'--')
    vis.add_waveform("meas",waveform.start_from_zero())
    yield vis

    rec_exp_aligned = align_waveform(adp,reference,waveform)
    error = reference.error(rec_exp_aligned)
    print("error: %s" % error)

    vis = wavelib.WaveformVis("align",ylabel,program.name)
    vis.add_waveform("ref",reference)
    vis.set_style('ref',ref_color,'-')
    vis.set_style('meas',meas_color,'--')
    vis.add_waveform("meas",rec_exp_aligned)
    yield vis




def plot_waveform_summaries(adps,waveforms):
    # get reference waveform
    program,dsinfo,reference = reference_waveform(adps[0], \
                                                  waveforms[0])

    align_wfs = []
    errors = []

    for adp,wf in zip(adps,waveforms):
        awf = align_waveform(adp,reference,wf)
        error = reference.error(awf)
        align_wfs.append(awf)
        errors.append(error)

    ref_color = "#B53471"
    meas_color = "#006266"
    ylabel = "%s (%s)" % (dsinfo.observation,dsinfo.units)
    vis = wavelib.WaveformVis("wfs",ylabel,program.name)
    vis.add_waveform("ref",reference)
    vis.set_style('ref',ref_color,'-')

    for idx,awf in enumerate(align_wfs):
        vis.set_style('meas',meas_color,'-', \
                    opacity=1.0/len(align_wfs))

        vis.add_waveform("meas%d" % idx,awf)
    yield vis

    best_idx = np.argmin(errors)
    vis = wavelib.WaveformVis("bestwf",ylabel,program.name)
    vis.add_waveform("ref",reference)
    vis.set_style('ref',ref_color,'-')
    vis.set_style('meas',meas_color,'--')
    vis.add_waveform("meas",align_wfs[best_idx])
    yield vis



