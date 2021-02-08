from hwlib.adp import ADP,ADPMetadata
from dslang.dsprog import DSProgDB

import compiler.lwav_pass.waveform as wavelib
import compiler.lsim as lsimlib
import numpy as np
import math

def get_emulated_waveforms(board,program,adp,dssim):
    times,value_dict = lsimlib.run_adp_simulation(board, \
                                                  adp, \
                                                  dssim, \
                                                  recover=True)
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
        print("-> calculated emulated <%s>" % varname)

    return waveforms


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
    return program,dsinfo,dssim,reference

def align_waveform(adp,reference,waveform, \
                   timing_error=2e-5, \
                   min_scaling_error=0.02, \
                   offset_error=0.0002):

    rec_experimental = waveform.start_from_zero().recover()
    print("unrec-time: [%f,%f]" % (min(waveform.times), \
          max(waveform.times)))
    print("rec-time: [%f,%f]" % (min(rec_experimental.times), \
          max(rec_experimental.times)))

    scale_error = max(timing_error/waveform.runtime, \
                      min_scaling_error)
    abs_offset_error = offset_error*(rec_experimental.runtime/waveform.runtime)

    rec_exp_aligned = reference.align(rec_experimental, \
                                      scale_slack=scale_error, \
                                      offset_slack=abs_offset_error)
    rec_exp_aligned.trim(reference.min_time, reference.max_time)

    return rec_exp_aligned

def plot_waveform(dev,adp,waveform,emulate=True,measured=True):
    program,dsinfo,dssim,reference = reference_waveform(adp,waveform)
    if emulate:
        emulated_wfs = get_emulated_waveforms(dev,program,adp,dssim)
        emulated = emulated_wfs[waveform.variable]

    npts = reference.npts
    ref_color = "#E74C3C"
    emul_color = "#badc58"
    meas_color = "#5758BB"
    ylabel = "%s (%s)" % (dsinfo.observation,dsinfo.units)

    if measured:
        vis = wavelib.WaveformVis("meas",ylabel,program.name)
        vis.set_style('meas',meas_color,'--')
        vis.add_waveform("meas",waveform.start_from_zero().resample(npts))
        yield vis

    print("==== Align with Reference ====")
    rec_exp_aligned = align_waveform(adp,reference,waveform)
    error = reference.error(rec_exp_aligned)
    print("error: %s" % error)

    vis = wavelib.WaveformVis("vsref",ylabel,program.name)
    vis.set_style('ref',ref_color,'-')
    vis.set_style('meas',meas_color,'--')
    vis.add_waveform("ref",reference)
    vis.add_waveform("meas",rec_exp_aligned.resample(npts))
    yield vis

    if emulate:
        print("==== Align with Emulated ====")
        emul_exp_aligned = align_waveform(adp,emulated,waveform)
        error = emulated.error(emul_exp_aligned)
        print("error: %s" % error)

        vis = wavelib.WaveformVis("vsemul",ylabel,program.name)
        vis.set_style('emul',emul_color,'-')
        vis.set_style('meas',meas_color,'--')
        vis.add_waveform("emul",emulated)
        vis.add_waveform("meas",emul_exp_aligned.resample(npts))
        yield vis






def plot_waveform_summaries(dev,adps,waveforms):
    # get reference waveform
    program,dsinfo,dssim,reference = reference_waveform(adps[0], \
                                                  waveforms[0])


    align_wfs = []
    errors = []

    print("==== Collating Summaries ====")
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

    print("==== Summary Plot ====")
    opacity = math.sqrt(1.0/len(align_wfs))
    for idx,awf in enumerate(align_wfs):
        series = 'meas%d' % idx
        vis.set_style(series,meas_color,'-', \
                      opacity=opacity)

        vis.add_waveform(series,awf)
    yield vis

    print("==== Best Waveform ====")
    best_idx = np.argmin(errors)
    vis = wavelib.WaveformVis("bestwf",ylabel,program.name)
    vis.add_waveform("ref",reference)
    vis.set_style('ref',ref_color,'-')
    vis.set_style('meas',meas_color,'--')
    vis.add_waveform("meas",align_wfs[best_idx])
    yield vis



