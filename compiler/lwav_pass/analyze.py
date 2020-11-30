from hwlib.adp import ADP,ADPMetadata
from dslang.dsprog import DSProgDB

import compiler.lwav_pass.waveform as wavelib

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


def analyze(adp,waveform):
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])
    dssim = DSProgDB.get_sim(program.name)
    dsinfo = DSProgDB.get_info(program.name)
    ref_waveforms = get_reference_waveforms(program,dssim)

    reference = ref_waveforms[waveform.variable]
    # start from zero
    rec_experimental = waveform.recover()

    ylabel = "%s (%s)" % (dsinfo.observation,dsinfo.units)
    vis = wavelib.WaveformVis("meas",ylabel,program.name)
    vis.set_style('meas',"#5758BB",'--')
    vis.add_waveform("meas",waveform)
    yield vis

    rec_exp_aligned = reference.align(rec_experimental)
    rec_exp_aligned.trim(reference.min_time, reference.max_time)
    vis = wavelib.WaveformVis("align",ylabel,program.name)
    vis.add_waveform("ref",reference)
    vis.set_style('ref',"#E74C3C",'-')
    vis.set_style('meas',"#5758BB",'--')
    vis.add_waveform("meas",rec_exp_aligned)
    yield vis



