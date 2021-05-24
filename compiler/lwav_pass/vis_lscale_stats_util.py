import hwlib.adp as adplib
from hwlib.adp import ADP,ADPMetadata

import compiler.lwav_pass.waveform as wavelib
import compiler.lwav_pass.histogram as histlib
import compiler.lwav_pass.heatgrid as heatlib
import compiler.lwav_pass.vis_util as visutil
import compiler.lwav_pass.table as tbllib
import compiler.lwav_pass.boxandwhisker as boxlib

import compiler.lscale_pass.lscale_dynsys as lscaleprob
import compiler.lscale_pass.lscale_ops as lscalelib

import hwlib.block as blocklib
import hwlib.device as devlib

from dslang.dsprog import DSProgDB
import numpy as np
import math
import re



def insert_value(dic,key,val):
    if not key in dic:
        dic[key] = []
    dic[key].append(val)

def get_port_info(dev,block,mode,port):
    spec = block.inputs.get(port) if block.inputs.has(port) else \
        (block.outputs.get(port) if block.outputs.has(port) else \
            block.data.get(port))

    is_port = block.inputs.has(port) or block.outputs.has(port)

    oprng = spec.interval.get(mode)
    error = spec.quantize.get(mode).error(oprng) \
        if spec.type == blocklib.BlockSignalType.DIGITAL or \
            isinstance(spec,blocklib.BlockData) else \
            spec.noise.get(mode)


    if is_port:
        freq_limit = spec.freq_limit.get(mode)
    else:
        freq_limit = None

    return freq_limit,oprng,error


def get_coverages(dev,dsprog,adp,  \
                  per_instance=False, \
                  apply_scale_transform=False, \
                  prescale=1.0, \
                  label_integrators_only=True):
    unscaled_adp = visutil.get_unscaled_adp(dev,adp)
    dsinfo= lscaleprob.generate_dynamical_system_info(dev, \
                                                      dsprog, \
                                                      unscaled_adp, \
                                                      apply_scale_transform=False)
    signal_coverages = {}
    value_coverages = {}
    quality_measures = {}
    max_freq = 1.0/dev.time_constant
    freq_limits = []
    ignored_blocks = ["tin","tout","cin","cout"]
    for cfg in adp.configs:
        block = dev.get_block(cfg.inst.block)

        if block.name in ignored_blocks:
            continue

        for stmt in cfg.stmts:
            if stmt.type == adplib.ConfigStmtType.CONSTANT or \
            stmt.type == adplib.ConfigStmtType.PORT:
                freq_limit,oprng,error = get_port_info(dev,block,cfg.mode,stmt.name)
                if not freq_limit is None:
                    freq_limits.append(freq_limit)

                if not dsinfo.has_interval(cfg.inst,stmt.name):
                    continue

                orig_ival = ival = dsinfo.get_interval(cfg.inst, stmt.name)
                expr = dsinfo.get_expr(cfg.inst, stmt.name)

                if not per_instance:
                    key = (cfg.inst.block,stmt.name)
                else:
                    key = (cfg.inst,stmt.name)

                if ival.bound > 0:
                    if  apply_scale_transform:
                        ival = orig_ival.scale(stmt.scf)

                    if ival.is_constant():
                        ratio = ival.bound/(oprng.bound*prescale)
                        insert_value(value_coverages,key,ratio)
                    else:
                        ratio = ival.spread/(oprng.spread*prescale)
                        if ratio-1.0 > 1e-5:
                            print(block.name,cfg.inst,cfg.mode,stmt.name,ratio)
                            print("  %s %s %s %s" % (orig_ival,oprng,stmt.scf,ival))
                            print(" %s" % expr)

                        insert_value(signal_coverages,key,ratio)


                    if not error is None and error > 0:
                        qm = ival.bound/error
                        insert_value(quality_measures,key,qm)

    max_time_scf = min(freq_limits)/max_freq
    time_coverage = (adp.tau)/max_time_scf if apply_scale_transform else 1.0/max_time_scf
    return quality_measures,signal_coverages,value_coverages,time_coverage




def get_scale_transform(dev,adp):
    scfs = {}
    injs = {}
    for cfg in adp.configs:
        for stmt in cfg.stmts:
            if  stmt.type == adplib.ConfigStmtType.PORT:
                if stmt.scf > 10000:
                    print(cfg.inst,stmt.name,stmt.scf)

                scfs[(cfg.inst,stmt.name)] = stmt.scf
            if  stmt.type == adplib.ConfigStmtType.CONSTANT:
                scfs[(cfg.inst,stmt.name)] = stmt.scf

            if  stmt.type == adplib.ConfigStmtType.EXPR:
                for arg,scf in stmt.scfs.items():
                    scfs[(cfg.inst,arg)] = scf
                for arg,inj in stmt.injs.items():
                    injs[(cfg.inst,arg)] = inj



    return adp.tau,scfs,injs


def get_correlation(x,y):
    return np.corrcoef(x,y)[0][1]

   #numer = np.cov(x,y)[0][1]
   # return numer/(x_std*y_std)

def extract_variables_from_objective_function(exprinfo,expr):
        time_scale_var =  "tau" in expr
        signals = []

        matches = re.findall("port\([^)]*\)",expr)

        for match in matches:
            args = match.split("port(")[1].split(")")[0].split(",")
            inst_args = args[0].split("_")
            block_name = inst_args[0]
            loc = list(map(lambda inst: int(inst), inst_args[1:]))

            inst = adplib.BlockInst(block_name,devlib.Location(loc))
            port = args[1]
            dsexpr = exprinfo.get_expr(inst,port)
            signals.append((inst,port,dsexpr))

        return time_scale_var,signals


def get_aggregate_quality_measures(dev,adp,qual_meas):
    def compute_aggregate(lst):
        if len(lst) == 0:
            return None
        else:
            return min(lst)

    aqm,dqm,dqme,aqme,aqmst,aqmderiv,aqmobs = [],[],[],[],[],[],[]
    for( block_inst,name),_qm in qual_meas.items():
        qm = _qm[0]
        block = dev.get_block(block_inst.block)
        config = adp.configs.get(block_inst.block,block_inst.loc)
        if block.inputs.has(name):
            port = block.inputs.get(name)
            if port.type == blocklib.BlockSignalType.ANALOG:
                aqm.append(qm)
            else:
                dqme.append(qm)

            if port.extern:
                aqmobs.append(qm)

            elif block.name == "integ" and port.name == "x":
                aqmderiv.append(qm)

            if config.has(name) and \
                not config[name].source is None:
                aqme.append(qm)


        elif block.outputs.has(name):
            port = block.outputs.get(name)
            if port.type == blocklib.BlockSignalType.ANALOG:
                aqm.append(qm)
            else:
                dqme.append(qm)

            if block.name == "integ" and port.name == "z":
                aqmst.append(qm)

            if port.extern:
                aqmobs.append(qm)

            if config.has(name) and \
                not config[name].source is None:
                aqme.append(qm)

        else:
            datum = block.data.get(name)
            dqm.append(qm)


    return compute_aggregate(aqm), compute_aggregate(dqm), \
        compute_aggregate(aqme),compute_aggregate(dqme), \
        compute_aggregate(aqmst),compute_aggregate(aqmderiv), \
        compute_aggregate(aqmobs)
