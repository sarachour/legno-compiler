import hwlib.adp as adplib
import compiler.lwav_pass.waveform as wavelib
import compiler.lwav_pass.histogram as histlib
from dslang.dsprog import DSProgDB
from hwlib.adp import ADP,ADPMetadata
import compiler.lsim as lsimlib
import numpy as np
import math
import json

def get_emulated_waveforms(board,program,adp,dssim,recover=False):
    en_phys,en_err,en_ival,en_quant = True,True,False,True
    #en_phys,en_err,en_ival,en_quant = True,False,False,False

    times,value_dict = lsimlib.run_adp_simulation(board, \
                                                  adp, \
                                                  dssim, \
                                                  recover=recover, \
                                                  enable_physical_model=en_phys, \
                                                  enable_model_error=en_err, \
                                                  enable_intervals=en_ival, \
                                                  enable_quantization=en_quant)

    waveforms = {}
    if recover:
        time_units = wavelib.Waveform.TimeUnits.DS_TIME_UNITS
        ampl_units = wavelib.Waveform.AmplUnits.DS_QUANTITY
    else:
        time_units = wavelib.Waveform.TimeUnits.WALL_CLOCK_SECONDS
        ampl_units = wavelib.Waveform.AmplUnits.VOLTAGE

    for varname,values in value_dict.items():
        wav = wavelib.Waveform(variable=varname, \
                               times=times, \
                               values=values, \
                               time_units=time_units, \
                               ampl_units=ampl_units, \
                               time_scale=1.0, \
                               mag_scale=1.0)
        waveforms[varname] = wav
        print("-> calculated emulated <%s>" % varname)

    #input("continue?")
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

def align_waveform(adp,reference,measured, \
                   timing_error=2e-5, \
                   min_scaling_error=0.02, \
                   offset_error=0.15):

    if adp.metadata.has(ADPMetadata.Keys.LWAV_ALIGN):
        xform = json.loads(adp.metadata.get(ADPMetadata.Keys.LWAV_ALIGN))
        rec_exp_aligned = measured.apply_time_transform(xform['scale'],xform['offset'])
    else:
        print("time: [%f,%f]" % (min(measured.times), \
            max(measured.times)))

        scale_error = max(timing_error/measured.runtime, min_scaling_error)
        abs_offset_error = offset_error*(reference.runtime)
        print("errors scale=%s offset=%s" % (scale_error,abs_offset_error) )

        xform,rec_exp_aligned = reference.align(measured, \
                                        scale_slack=scale_error, \
                                        offset_slack=abs_offset_error)
        adp.metadata.set(ADPMetadata.Keys.LWAV_ALIGN,json.dumps(xform))

    rec_exp_aligned.trim(reference.min_time, reference.max_time)
    return rec_exp_aligned

def get_alignment_params():
    return { \
             'min_scaling_error':0.02, \
             'offset_error':0.3, \
             'timing_error':8e-4

    }

def plot_waveform(dev,adp,waveform,emulate=True,measured=True):
    program,dsinfo,dssim,reference = reference_waveform(adp,waveform)
    if emulate:
        emulated_wfs = get_emulated_waveforms(dev,program,adp,dssim, \
                                              recover=False)
        emulated = emulated_wfs[waveform.variable]

    npts = reference.npts
    ref_color = "#E74C3C"
    emul_color = "#badc58"
    meas_color = "#5758BB"
    ylabel = "%s (%s)" % (dsinfo.observation,dsinfo.units)

    if measured:
        vis = wavelib.WaveformVis("meas",ylabel,dsinfo.name)
        vis.set_style('meas',meas_color,'--')
        vis.add_waveform("meas",waveform.start_from_zero().resample(npts))
        yield vis

    print("==== Align with Reference ====")
    pars = get_alignment_params()
    rec_exp_aligned = align_waveform(adp,reference, \
                                     waveform.start_from_zero().recover(), \
                                     min_scaling_error=pars['min_scaling_error'],
                                     offset_error=pars['offset_error'], \
                                     timing_error=pars['timing_error'])
    try:
        error = reference.error(rec_exp_aligned)

    except Exception as e:
        return

    adp.metadata.set(ADPMetadata.Keys.LWAV_NRMSE,error)
    time = min(rec_exp_aligned.max_time, reference.max_time)
    print("align error: %s" % error)
    print("times exp=%s ref=%s" % (rec_exp_aligned.max_time, reference.max_time))

    vis = wavelib.WaveformVis("vsref",ylabel,dsinfo.name)
    vis.set_style('ref',ref_color,'-')
    vis.set_style('meas',meas_color,'--')
    vis.add_waveform("ref",reference)
    vis.add_waveform("meas",rec_exp_aligned.resample(npts))
    yield vis

    if emulate:
        print("==== Align with Emulated ====")
        emul_exp_aligned = align_waveform(adp,emulated.start_from_zero(), \
                                          waveform.start_from_zero(), \
                                          min_scaling_error=pars['min_scaling_error'], \
                                          offset_error=pars['offset_error'])
        error = emulated.error(emul_exp_aligned)
        print("error: %s" % error)

        vis = wavelib.WaveformVis("vsemul",ylabel,dsinfo.name)
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
    pars = get_alignment_params()
    for adp,wf in zip(adps,waveforms):
        awf = align_waveform(adp,reference, \
                             wf.start_from_zero().recover(), \
                             min_scaling_error=pars['min_scaling_error'], \
                             offset_error=pars['offset_error'], \
                             timing_error=pars['timing_error'])
        try:
            error = reference.error(awf)
        except Exception as e:
            continue

        align_wfs.append(awf)
        errors.append(error)

    ref_color = "#B53471"
    meas_color = "#006266"
    ylabel = "%s (%s)" % (dsinfo.observation,dsinfo.units)
    vis = wavelib.WaveformVis("wfs",ylabel,dsinfo.name)
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
    vis = wavelib.WaveformVis("bestwf",ylabel,dsinfo.name)
    vis.add_waveform("ref",reference)
    vis.set_style('ref',ref_color,'-')
    vis.set_style('meas',meas_color,'--')
    vis.add_waveform("meas",align_wfs[best_idx])
    yield vis




    print("==== Median Waveform ====")
    npts = len(errors)
    median_value = np.percentile(errors,50,interpolation='nearest')
    best_idx = list(filter(lambda idx: abs(errors[idx] - median_value) < 1e-6,  \
                           range(npts)))[0]

    vis = wavelib.WaveformVis("medianwf",ylabel,dsinfo.name)
    vis.add_waveform("ref",reference)
    vis.set_style('ref',ref_color,'-')
    vis.set_style('meas',meas_color,'--')
    vis.add_waveform("meas",align_wfs[best_idx])
    yield vis



