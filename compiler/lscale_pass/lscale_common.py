from enum import Enum
import numpy as np
import ops.scop as scop
import hwlib.props as props
import hwlib.model as hwmodel
import util.util as util
import util.config as CONFIG
import compiler.lscale_pass.lscale_util as lscale_util
import compiler.lscale_pass.lscale_physlog as lscale_physlog
import compiler.lscale_pass.scenv as scenvlib
import math


def get_physics_params(scenv,circ,block,loc,port,handle=None):
    model = scenv.params.model
    config = circ.config(block.name,loc)
    oprange_lower, oprange_upper = hwmodel.get_oprange_scale(scenv.model_db, \
                                                             circ, \
                                                             block.name, \
                                                             loc, \
                                                             port,handle=handle, \
                                                             mode=model)
    gain_sc = hwmodel.get_gain(scenv.model_db, \
                               circ, \
                               block.name,loc, \
                               port,handle=handle, \
                               mode=model)
    uncertainty_sc = hwmodel.get_variance(scenv.model_db, \
                                          circ,block.name,loc, \
                                          port,handle=handle, \
                                          mode=model)

    model = hwmodel.get_model(scenv.model_db, \
                                          circ,block.name,loc, \
                                          port,handle=handle)
    return {
        'model':model,
        'gain':gain_sc,
        'uncertainty': uncertainty_sc,
        'oprange_lower': oprange_lower,
        'oprange_upper':oprange_upper
    }


def get_parameters(scenv,circ,block,loc,port,handle=None):
    config = circ.config(block.name,loc)
    baseline = block.baseline(config.comp_mode)
    pars = {}
    if isinstance(scenv, scenvlib.LScaleInferEnv):
        scale_mode = baseline
        #physical scale variable
        hwscvar_lower = scop.SCMult( \
                             scop.SCVar(scenv.get_phys_op_range_scvar(block.name,loc,port, \
                                                                   handle,lower=True)), \
                             scop.SCVar(scenv.get_op_range_var(block.name,loc,port,handle)) \
        );
        hwscvar_upper = scop.SCMult( \
                             scop.SCVar(scenv.get_phys_op_range_scvar(block.name,loc,port, \
                                                                   handle,lower=False)), \
                             scop.SCVar(scenv.get_op_range_var(block.name,loc,port,handle)) \
        );
        uncertainty = scop.SCVar(scenv.get_phys_uncertainty(block.name,loc,port,handle))
        hwscvar_gain = scop.SCMult(
            scop.SCVar(scenv.get_phys_gain_var(block.name,loc,port,handle)),
            scop.SCVar(scenv.get_gain_var(block.name,loc,port,handle))
        )

    else:
        pars = get_physics_params(scenv,circ,block,loc,port,handle=handle)
        scale_mode = config.scale_mode
        hwscvar_lower = scop.SCConst(pars['oprange_lower'])
        hwscvar_upper = scop.SCConst(pars['oprange_upper'])
        hwscvar_gain = scop.SCConst(pars['gain']*block.coeff(config.comp_mode, \
                                                            config.scale_mode, \
                                                            port,handle=handle))
        uncertainty = scop.SCConst(pars['uncertainty'])
        assert(not uncertainty is None)

    mrng = config.interval(port)
    mathscvar = scop.SCVar(scenv.get_scvar(block.name,loc,port,handle))
    prop = block.props(config.comp_mode,scale_mode,port,handle=handle)
    hwrng= prop.interval()
    hwbw = prop.bandwidth()
    resolution = 1
    coverage = 1
    if isinstance(prop,props.DigitalProperties):
        resolution = prop.resolution
        coverage = prop.coverage
    return {
        'math_interval':mrng,
        'math_scale':mathscvar,
        'prop':prop,
        'hw_coverage':coverage,
        'hw_oprange_scale_lower':hwscvar_lower,
        'hw_oprange_scale_upper':hwscvar_upper,
        'hw_gain':hwscvar_gain,
        'hw_oprange_base':hwrng,
        'hw_bandwidth':hwbw,
        'hw_uncertainty': uncertainty,
        'mdpe': scenv.params.mdpe,
        'mape': scenv.params.mape,
        'vmape': scenv.params.vmape,
        'mc': scenv.params.mc,
        'digital_resolution': resolution,
    }

def decl_scale_variables(scenv,circ):
    # define scaling factors
    MIN_SC = 1e-6
    MAX_SC = 1e6
    for block_name,loc,config in circ.instances():
        block = circ.board.block(block_name)
        for output in block.outputs:
            v = scenv.decl_scvar(block_name,loc,output)
            for handle in block.handles(config.comp_mode,output):
                v = scenv.decl_scvar(block_name,loc,output,handle=handle)
            if block.name == "lut":
                v=scenv.decl_inject_var(block_name,loc,output)

        for inp in block.inputs:
            v=scenv.decl_scvar(block_name,loc,inp)
            if block.name == "lut":
                v=scenv.decl_inject_var(block_name,loc,inp)

        for output in block.outputs:
            for orig in block.copies(config.comp_mode,output):
                copy_scf = scenv.get_scvar(block_name,loc,output)
                orig_scf = scenv.get_scvar(block_name,loc,orig)
                scenv.eq(scop.SCVar(orig_scf),scop.SCVar(copy_scf),'jc-copy')

    for sblk,sloc,sport,dblk,dloc,dport in circ.conns():
        s_scf = scenv.get_scvar(sblk,sloc,sport)
        d_scf = scenv.get_scvar(dblk,dloc,dport)
        scenv.eq(scop.SCVar(s_scf),scop.SCVar(d_scf),'jc-conn')

def _to_phys_time(circ,time):
    return time/circ.board.time_constant

def _to_phys_bandwidth(circ):
    return circ.board.time_constant



def digital_op_range_constraint(scenv,circ,block,loc,port,handle,annot=""):
    pars = get_parameters(scenv,circ,block,loc,port,handle)
    mrng = pars['math_interval']
    hwrng = pars['hw_oprange_base']
    prop = pars['prop']
    hscale_lower = pars['hw_oprange_scale_lower']
    hscale_upper = pars['hw_oprange_scale_upper']
    coverage = pars['hw_coverage']
    min_coverage = pars['mc']

    assert(isinstance(prop, props.DigitalProperties))
    def ratio(hwexpr):
        return scop.SCMult(pars['math_scale'], scop.expo(hwexpr,-1.0))

    lscale_util.upper_bound_constraint(scenv,
                                      ratio(hscale_upper),
                                      mrng.upper,
                                      hwrng.upper,
                                      'jcom-digital-oprange-%s' % annot)

    lscale_util.lower_bound_constraint(scenv,
                                      ratio(hscale_lower),
                                      mrng.lower,
                                      hwrng.lower,
                                      'jcom-digital-oprange-%s' % annot)


    if mrng.spread > 0.0 and \
       coverage > 0.0:
        signal_expr = scop.SCMult(pars['math_scale'],scop.SCConst(mrng.bound))
        scenv.lte(scop.SCConst(pars['mc']),signal_expr,\
                 annot='jcom-dig-minmap')


def analog_op_range_constraint(scenv,circ,block,loc,port,handle,annot=""):

    pars = get_parameters(scenv,circ,block,loc,port,handle)
    mrng = pars['math_interval']
    hwrng = pars['hw_oprange_base']
    min_snr = 1.0/pars['mape']
    stvar_min_snr = 1.0/pars['vmape']
    hw_unc = pars['hw_uncertainty']
    prop = pars['prop']
    assert(isinstance(prop, props.AnalogProperties))
    hw_lower = pars['hw_oprange_scale_lower']
    hw_upper = pars['hw_oprange_scale_upper']

    def ratio(hwexpr):
        return scop.SCMult(pars['math_scale'], scop.expo(hwexpr,-1.0))

    lscale_util.upper_bound_constraint(scenv,
                                      ratio(hw_upper),
                                      mrng.upper,
                                      hwrng.upper,
                                      'jcom-analog-oprange-%s' % annot)
    lscale_util.lower_bound_constraint(scenv,
                                      ratio(hw_lower),
                                      mrng.lower,
                                      hwrng.lower,
                                      'jcom-analog-oprange-%s' % annot)

    # if this makes the system a system that processes a physical signal.
    if prop.is_physical:
        scenv.eq(pars['math_scale'], scop.SCConst(1.0),'jcom-analog-physical-rng')

    hw_unc_coeff,_ = hw_unc.factor_const()
    if hw_unc_coeff > 0.0  \
       and mrng.bound > 0.0 \
       and scenv.params.enable_quality_constraint:
        signal_expr = scop.SCMult(pars['math_scale'],scop.SCConst(mrng.bound))
        noise_expr = scop.expo(hw_unc, -1.0)
        snr_expr = scop.SCMult(signal_expr,noise_expr)
        scenv.gte(snr_expr,scop.SCConst(min_snr), \
                 annot='jcom-analog-minsig')

        if block.name == "integrator" and port == "out" and handle is None:
            scenv.gte(snr_expr,scop.SCConst(stvar_min_snr), \
                      annot='jcom-analog-minsig')


def digital_quantize_constraint(scenv,circ,block,loc,port,handle,annot=""):
    pars = get_parameters(scenv,circ,block,loc,port,handle)
    prop = pars['prop']
    mrng = pars['math_interval']
    min_snr = 1.0/pars['mdpe']
    resolution = pars['digital_resolution']
    delta_h = np.mean(np.diff(prop.values()))

    if delta_h > 0.0  \
       and mrng.bound > 0.0 \
       and scenv.params.enable_quantize_constraint:
        noise_expr = scop.SCConst(1.0/(resolution*delta_h))

        signal_expr = scop.SCMult(pars['math_scale'],scop.SCConst(mrng.bound))
        snr_expr = scop.SCMult(signal_expr,noise_expr)
        scenv.gte(snr_expr,scop.SCConst(min_snr), \
                annot='jcom-digital-minsig')

def max_sim_time_constraint(scenv,prob,circ):
    max_sim_time = _to_phys_time(circ,prob.max_time)
    # 100 ms.
    max_time = 0.05
    tau_inv = scop.SCVar(scenv.tau(),exponent=-1.0)
    hw_time = scop.SCMult(
        scop.SCConst(max_sim_time), tau_inv
    )
    scenv.lte(hw_time, scop.SCConst(max_time), 'max-time')


def analog_bandwidth_constraint(scenv,circ,block,loc,port,handle,annot):
    tau = scop.SCVar(scenv.tau())
    pars = get_parameters(scenv,circ,block,loc,port,handle)
    hwbw = pars['hw_bandwidth']
    prop = pars['prop']

    if not scenv.params.enable_bandwidth_constraint:
        return

    if hwbw.unbounded_lower() and hwbw.unbounded_upper():
        return

    # physical signals are not corrected by the board's time constant
    physbw = _to_phys_bandwidth(circ)
    scenv.use_tau()

    if not scenv.params.max_freq_hz is None:
        scenv.lte(scop.SCMult(tau,scop.SCConst(physbw)), \
                scop.SCConst(scenv.params.max_freq_hz),
                'jcom-analog-maxbw-%s' % annot
        )

    if hwbw.upper > 0:
        scenv.lte(scop.SCMult(tau,scop.SCConst(physbw)), \
                scop.SCConst(hwbw.upper),
                'jcom-analog-bw-%s' % annot
        )
    else:
        scenv.fail()

    if hwbw.lower > 0:
        scenv.gte(scop.SCMult(tau,scop.SCConst(physbw)), \
                scop.SCConst(hwbw.lower),
                'jcom-analog-bw-%s' % annot
        )


def digital_bandwidth_constraint(scenv,prob,circ,block,loc,port,handle,annot):
    max_sim_time = _to_phys_time(circ,prob.max_time)
    tau = scop.SCVar(scenv.tau())
    tau_inv = scop.SCVar(scenv.tau(),exponent=-1.0)
    pars = get_parameters(scenv,circ,block,loc,port,handle)
    prop = pars['prop']

    physbw = _to_phys_bandwidth(circ)
    if prop.kind == props.DigitalProperties.ClockType.CONSTANT:
        return

    elif prop.kind == props.DigitalProperties.ClockType.CLOCKED:
        scenv.use_tau()
        # time between samples
        hw_sample_freq = 1.0/prop.sample_rate
        # maximum number of samples
        # sample frequency required
        sim_sample_freq = 2.0*physbw
        if scenv.params.enable_bandwidth_constraint:
            scenv.lte(scop.SCMult(tau, scop.SCConst(sim_sample_freq)), \
                    scop.SCConst(hw_sample_freq),
                    'jcom-digital-bw-%s' % annot
            )
            if not scenv.params.max_freq_hz is None:
                scenv.lte(scop.SCMult(tau,scop.SCConst(sim_sample_freq)), \
                         scop.SCConst(scenv.params.max_freq_hz),
                         'jcom-digital-maxbw-%s' % annot
                )


        # maximum runtime of 50 ms
        max_sim_time_constraint(scenv,prob,circ)

        if not prop.max_samples is None:
            sim_max_samples = max_sim_time*sim_sample_freq
            hw_max_samples = prop.max_samples

            if sim_max_samples > hw_max_samples:
                raise Exception("[error] not enough storage in arduino to record data")

    elif prop.kind == props.DigitalProperties.ClockType.CONTINUOUS:
        hwbw = prop.bandwidth()
        analog_bandwidth_constraint(scenv,circ,block,loc,port,handle,
                                    "digcont-bw-%s[%s].%s" % (block.name,loc,port))
    else:
        raise Exception("unknown not permitted")
