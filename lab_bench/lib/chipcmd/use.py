import hwlib.hcdc.enums as spec_enums

import lab_bench.lib.chipcmd.data as ccmd_data
import lab_bench.lib.chipcmd.common as ccmd_common
from lab_bench.lib.chipcmd.disable import DisableCmd
from lab_bench.lib.chipcmd.calib import SetStateCmd
import lab_bench.lib.chipcmd.state as state

from lab_bench.lib.base_command import AnalogChipCommand
import lab_bench.lib.enums as glb_enums
import lab_bench.lib.util as util
import numpy as np
from enum import Enum
import construct
import math


class UseCommand(AnalogChipCommand):

    def __init__(self,block,loc):
        AnalogChipCommand.__init__(self)
        self.test_loc(block,loc)
        self._loc = loc
        self._block = block
        self.calibrated = True

    def to_key(self,targeted=False):
        raise NotImplementedError

    @property
    def block_type(self):
        return self._block

    @property
    def loc(self):
        return self._loc

    def update_state(self,stateobj):
        raise Exception("override me with keyword dict of targeted args: %s" % \
                        self.__class__.__name__)

    def execute_command(self,env):
        AnalogChipCommand.execute_command(self,env)

        if self.calibrated:
            dbkey = self.to_key(calib_obj=env.calib_obj)
            assert(isinstance(dbkey, state.BlockState.Key))
            if not env.state_db.has(dbkey):
                for obj in env.state_db.get_all():
                    print(obj.identifier,obj.descriptor)

                print("=====")
                print(dbkey.identifier,dbkey.descriptor)
                input("not calibrated")
                raise Exception("not calibrated")

            blockstate = env.state_db.get(dbkey)
            blockstate.from_key(dbkey)
            assert(isinstance(blockstate, state.BlockState))
            # set the state
            loc = ccmd_data.CircLoc(self._loc.chip,
                                    self._loc.tile,
                                    self._loc.slice,
                                    self._loc.index \
                                    if self._loc.index != None \
                                    else 0)

            cmd = SetStateCmd(self._block,loc,blockstate)
            resp = cmd.execute_command(env)



    def disable(self):
         return DisableCmd(
             self._block,
             self._loc.chip,
             self._loc.tile,
             self._loc.slice,
             self._loc.index)

    def __repr__(self):
        raise Exception("override me")



class UseLUTCmd(UseCommand):

    def __init__(self,chip,tile,slice,
                 source=spec_enums.LUTSourceType.EXTERN):
        UseCommand.__init__(self,
                            glb_enums.BlockType.LUT,
                            ccmd_data.CircLoc(chip,tile,slice))

        if not self._loc.index is None:
            self.fail("dac has no index <%d>" % loc.index)

        self._source = source

    @property
    def expr(self):
        return self._expr

    @staticmethod
    def desc():
        return "use a lut block on the hdacv2 board"

    @staticmethod
    def parse(args):
        return UseLUTCmd._parse(args,UseLUTCmd)

    @staticmethod
    def _parse(args,cls):
        result = ccmd_common.parse_pattern_use_block(args,0,0,0,
                                     cls.name(),
                                     source=spec_enums.LUTSourceType,
                                     expr=False)
        if result.success:
            data = result.value
            return cls(
                data['chip'],
                data['tile'],
                data['slice'],
                source=data['source']
            )
        else:
            raise Exception(result.message)

    def to_key(self,calib_obj):
        loc = ccmd_data.CircLoc(self.loc.chip,
                      self.loc.tile,
                      self.loc.slice,
                      0
        )
        return state.LutBlockState.Key(loc=loc,
                                       source=self._source,
                                       calib_obj=calib_obj)



    def build_ctype(self):
        # inverting flips the sign for some wacky reason, given the byte
        # representation is signed
        return ccmd_common.build_circ_ctype({
            'type':glb_enums.CircCmdType.USE_LUT.name,
            'data':{
                'lut':{
                    'loc':self._loc.build_ctype(),
                    'source':self._source.code()
                }
            }
        })

    @staticmethod
    def name():
        return 'use_lut'

    def __repr__(self):
        cmd = "use_lut {chip} {tile} {slice} src {source}"
        st = cmd.format(\
                        chip=self.loc.chip, \
                        tile=self.loc.tile, \
                        slice=self.loc.slice, \
                        source=self._source.abbrev())
        return st


    def apply(self,state):
        if state.dummy:
            return
        resp = AnalogChipCommand.apply(self,state)
        return resp


class UseADCCmd(UseCommand):

    def __init__(self,chip,tile,slice,
                 in_range=spec_enums.RangeType.MED):
        UseCommand.__init__(self,
                            glb_enums.BlockType.ADC,
                            ccmd_data.CircLoc(chip,tile,slice))

        if not self._loc.index is None:
            self.fail("adc has no index <%d>" % loc.index)

        assert(isinstance(in_range,spec_enums.RangeType))
        if in_range == spec_enums.RangeType.LOW:
            raise Exception("incompatible: low input")

        self._in_range = in_range

    @staticmethod
    def desc():
        return "use a constant adc block on the hdacv2 board"

    @staticmethod
    def parse(args):
        return UseADCCmd._parse(args,UseADCCmd)

    @staticmethod
    def _parse(args,cls):
        result = ccmd_common.parse_pattern_use_block(args,0,0,1,
                                                     cls.name())
        if result.success:
            data = result.value
            return cls(
                data['chip'],
                data['tile'],
                data['slice'],
                in_range=data['range0']
            )
        else:
            raise Exception(result.message)

    def to_key(self,calib_obj):
        loc = ccmd_data.CircLoc(self.loc.chip,
                      self.loc.tile,
                      self.loc.slice,
                      0
        )

        false_val = ccmd_data.BoolType.FALSE
        return state.AdcBlockState.Key(loc=loc,
                                       test_en=false_val,
                                       test_adc=false_val,
                                       test_i2v=false_val,
                                       test_rs=false_val,
                                       test_rsinc=false_val,
                                       rng=self._in_range,
                                       calib_obj=calib_obj)

    def build_ctype(self):
        # inverting flips the sign for some wacky reason, given the byte
        # representation is signed
        return ccmd_common.build_circ_ctype({
            'type':glb_enums.CircCmdType.USE_ADC.name,
            'data':{
                'adc':{
                    'loc':self._loc.build_ctype(),
                    'in_range':self._in_range.code()
                }
            }
        })

    @staticmethod
    def name():
        return 'use_adc'

    def __repr__(self):
        cmd = "use_adc {chip} {tile} {slice} rng {range}"
        st = cmd.format(
            chip=self.loc.chip, \
            tile=self.loc.tile, \
            slice=self.loc.slice, \
            range=self._in_range.abbrev() \
        )
        return st


class UseDACCmd(UseCommand):

    def __init__(self,chip,tile,slice,value,
                 source=spec_enums.DACSourceType.MEM,
                 out_range=spec_enums.RangeType.MED,
                 inv=spec_enums.SignType.POS):
        UseCommand.__init__(self,
                            glb_enums.BlockType.DAC,
                            ccmd_data.CircLoc(chip,tile,slice))

        if value < -1.0 or value > 1.0:
            self.fail("value not in [-1,1]: %s" % value)
        if not self._loc.index is None:
            self.fail("dac has no index <%d>" % loc.index)

        assert(isinstance(inv,spec_enums.SignType))
        assert(isinstance(out_range,spec_enums.RangeType))
        if out_range == spec_enums.RangeType.LOW:
            raise Exception("incompatible: low output")

        self._out_range = out_range
        self._value = value
        self._inv = inv
        self._source = source

    @staticmethod
    def desc():
        return "use a constant dac block on the hdacv2 board"


    @staticmethod
    def parse(args):
        return UseDACCmd._parse(args,UseDACCmd)

    def to_key(self,calib_obj):
        loc = ccmd_data.CircLoc(self.loc.chip,
                      self.loc.tile,
                      self.loc.slice,
                      0
        )
        return state.DacBlockState.Key(loc=loc,
                                       inv=self._inv,
                                       rng=self._out_range,
                                       source=self._source,
                                       const_val=self._value,
                                       calib_obj=calib_obj)


    @staticmethod
    def _parse(args,cls):
        result = ccmd_common.parse_pattern_use_block(args,1,1,1,
                                     cls.name(),
                                     source=spec_enums.DACSourceType)
        if result.success:
            data = result.value
            return cls(
                data['chip'],
                data['tile'],
                data['slice'],
                data['value0'],
                source=data['source'],
                inv=data['sign0'],
                out_range=data['range0']
            )
        else:
            raise Exception(result.message)

    def build_ctype(self):
        # inverting flips the sign for some wacky reason, given the byte
        # representation is signed
        return ccmd_common.build_circ_ctype({
            'type':glb_enums.CircCmdType.USE_DAC.name,
            'data':{
                'dac':{
                    'loc':self._loc.build_ctype(),
                    'value':self._value,
                    # for whatever screwy reason, with inversion disabled
                    # 255=-1.0 and 0=1.0
                    'source':self._source.code(),
                    'inv':self._inv.code(),
                    'out_range':self._out_range.code()
                }
            }
        })

    @staticmethod
    def name():
        return 'use_dac'

    def __repr__(self):
        cmd = "use_dac {chip} {tile} {slice} src {source} sgn {inv} "
        cmd += "val {value} rng {range}"
        st = cmd.format(\
                        chip=self.loc.chip,
                        tile=self.loc.tile, \
                        slice=self.loc.slice,
                        source=self._source.abbrev(),
                        inv=self._inv.abbrev(),
                        value=self._value,
                        range=self._out_range.abbrev())
        return st



class UseFanoutCmd(UseCommand):


    def __init__(self,chip,tile,slice,index,
                 in_range,
                 inv0,inv1,inv2,
                 third):

        assert(isinstance(inv0, spec_enums.SignType))
        assert(isinstance(inv1,spec_enums.SignType))
        assert(isinstance(inv2,spec_enums.SignType))
        assert(isinstance(third,ccmd_data.BoolType))
        assert(isinstance(in_range,spec_enums.RangeType))

        UseCommand.__init__(self,
                            glb_enums.BlockType.FANOUT,
                            ccmd_data.CircLoc(chip,tile,slice,index))
        if in_range == spec_enums.RangeType.LOW:
            raise Exception("incompatible: low output")

        self._inv = [inv0,inv1,inv2]
        self._inv0 = inv0
        self._inv1 = inv1
        self._inv2 = inv2
        self._in_range = in_range
        self._third = third

    @staticmethod
    def name():
        return 'use_fanout'

    @staticmethod
    def desc():
        return "use a fanout block on the hdacv2 board"


    def build_ctype(self):
        return ccmd_common.build_circ_ctype({
            'type':glb_enums.CircCmdType.USE_FANOUT.name,
            'data':{
                'fanout':{
                    'loc':self._loc.build_ctype(),
                    'inv':[
                        self._inv0.code(),
                        self._inv1.code(),
                        self._inv2.code()
                    ],
                    'in_range':self._in_range.code(),
                    'third': self._third.code()
                }
            }
        })

    def to_key(self,calib_obj):
        loc = ccmd_data.CircLoc(self.loc.chip,
                      self.loc.tile,
                      self.loc.slice,
                      self.loc.index
        )
        invs = {
            glb_enums.PortName.OUT0: self._inv0,
            glb_enums.PortName.OUT1: self._inv1,
            glb_enums.PortName.OUT2: self._inv2
        }
        return state.FanoutBlockState.Key(loc=loc, \
                                          third=self._third, \
                                          invs=invs, \
                                          rng=self._in_range, \
                                          calib_obj=calib_obj)

    @staticmethod
    def parse(args):
        result = ccmd_common.parse_pattern_use_block(args,3,0,1, \
                                                    UseFanoutCmd.name(), \
                                                    index=True, \
                                                    third=True)
        if result.success:
            data = result.value
            return UseFanoutCmd(
                data['chip'],
                data['tile'],
                data['slice'],
                data['index'],
                in_range=data['range0'],
                inv0=data['sign0'],
                inv1=data['sign1'],
                inv2=data['sign2'],
                third=ccmd_data.BoolType.from_bool(data['third'])
            )
        else:
            raise Exception(result.message)


    def __repr__(self):
        cmd = "use_fanout {chip} {tile} {slice} {index} "
        cmd += " sgn {inv0} {inv1} {inv2} rng {range} {third}"
        st = cmd.format(\
                        chip=self.loc.chip,
                        tile=self.loc.tile,
                        slice=self.loc.slice,
                        index=self.loc.index,
                        inv0=self._inv[0].abbrev(),
                        inv1=self._inv[1].abbrev(),
                        inv2=self._inv[2].abbrev(),
                        range=self._in_range.abbrev(),
                        third="three" if self._third.boolean() else "two")
        return st



class UseIntegCmd(UseCommand):


    def __init__(self,chip,tile,slice,init_cond,
                 inv=spec_enums.SignType.POS, \
                 in_range=spec_enums.RangeType.MED, \
                 out_range=spec_enums.RangeType.MED,
                 debug=ccmd_data.BoolType.FALSE):
        UseCommand.__init__(self,
                            glb_enums.BlockType.INTEG,
                            ccmd_data.CircLoc(chip,tile,slice))
        assert(isinstance(inv,spec_enums.SignType))
        assert(isinstance(in_range,spec_enums.RangeType))
        assert(isinstance(out_range,spec_enums.RangeType))
        if init_cond < -1.0 or init_cond > 1.0:
            self.fail("init_cond not in [-1,1]: %s" % init_cond)

        self._init_cond = init_cond
        self._inv = inv
        if in_range == spec_enums.RangeType.HIGH and \
           out_range == spec_enums.RangeType.LOW:
            raise Exception("incompatible: high input and low output")
        elif in_range == spec_enums.RangeType.LOW and \
             out_range == spec_enums.RangeType.HIGH:
            raise Exception("incompatible: high input and low output")

        self._in_range = in_range
        self._out_range = out_range
        self._debug = debug


    @staticmethod
    def desc():
        return "use a integrator block on the hdacv2 board"


    @staticmethod
    def parse(args):
        return UseIntegCmd._parse(args,UseIntegCmd)

    @staticmethod
    def _parse(args,cls):
        result = ccmd_common.parse_pattern_use_block(args,1,1,2, \
                                                    cls.name(), \
                                                    debug=True)
        if result.success:
            data = result.value
            return cls(
                data['chip'],
                data['tile'],
                data['slice'],
                data['value0'],
                inv=data['sign0'],
                in_range=data['range0'],
                out_range=data['range1'],
                debug=ccmd_data.BoolType.TRUE if data['debug'] \
                else ccmd_data.BoolType.FALSE
            )
        else:
            raise Exception(result.message)


    @staticmethod
    def name():
        return 'use_integ'

    def build_ctype(self):
        return ccmd_common.build_circ_ctype({
            'type':glb_enums.CircCmdType.USE_INTEG.name,
            'data':{
                'integ':{
                    'loc':self._loc.build_ctype(),
                    'value':self._init_cond,
                    'inv':self._inv.code(),
                    'in_range': self._in_range.code(),
                    'out_range': self._out_range.code(),
                    'debug': self._debug.code()
                }
            }
        })

    def to_key(self,calib_obj):
        loc = ccmd_data.CircLoc(self.loc.chip,
                      self.loc.tile,
                      self.loc.slice,
                      0
        )
        rngs = {
            glb_enums.PortName.IN0: self._in_range,
            glb_enums.PortName.OUT0: self._out_range
        }
        cal_en = {
            glb_enums.PortName.IN0: ccmd_data.BoolType.FALSE,
            glb_enums.PortName.OUT0: ccmd_data.BoolType.FALSE
        }

        return state.IntegBlockState.Key(loc=loc,
                                         cal_enables=cal_en,
                                         exception=self._debug,
                                         inv=self._inv,
                                         ranges=rngs,
                                         ic_val=self._init_cond,
                                         calib_obj=calib_obj)


    def __repr__(self):
        cmd = "use_integ {chip} {tile} {slice} sgn {inv} "
        cmd += "val {init_cond} rng {in_range} {out_range} {debug}"
        st = cmd.format(
            chip=self.loc.chip, \
            tile=self.loc.tile, \
            slice=self.loc.slice, \
            inv=self._inv.abbrev(),
            init_cond=self._init_cond,
            in_range=self._in_range.abbrev(),
            out_range=self._out_range.abbrev(),
            debug="debug" if self._debug else "prod"
        )
        return st



class UseMultCmd(UseCommand):


    def __init__(self,chip,tile,slice,index,
                 in0_range=spec_enums.RangeType.MED,
                 in1_range=spec_enums.RangeType.MED,
                 out_range=spec_enums.RangeType.MED,
                 coeff=0, \
                 use_coeff=False):
        UseCommand.__init__(self,
                            glb_enums.BlockType.MULT,
                            ccmd_data.CircLoc(chip,tile,slice,index))

        if coeff < -1.0 or coeff > 1.0:
            self.fail("value not in [-1,1]: %s" % coeff)

        assert(isinstance(in0_range,spec_enums.RangeType))
        assert(isinstance(in1_range,spec_enums.RangeType))
        assert(isinstance(out_range,spec_enums.RangeType))

        self._use_coeff = use_coeff
        self._coeff = coeff
        self._in0_range = in0_range
        self._in1_range = in1_range
        self._out_range = out_range

    def update_state(self,state):
        state.update_gain(self._coeff)

    @staticmethod
    def desc():
        return "use a multiplier block on the hdacv2 board"

    def build_ctype(self):
        return ccmd_common.build_circ_ctype({
            'type':glb_enums.CircCmdType.USE_MULT.name,
            'data':{
                'mult':{
                    'loc':self._loc.build_ctype(),
                    'use_coeff':self._use_coeff,
                    'coeff':self._coeff,
                    'in0_range':self._in0_range.code(),
                    'in1_range':self._in1_range.code(),
                    'out_range':self._out_range.code()
                }
            }
        })


    def to_key(self,calib_obj):
        loc = ccmd_data.CircLoc(self.loc.chip,
                      self.loc.tile,
                      self.loc.slice,
                      self.loc.index
        )
        rngs = {
            glb_enums.PortName.IN0: self._in0_range,
            glb_enums.PortName.IN1: self._in1_range,
            glb_enums.PortName.OUT0: self._out_range,
        }
        return state.MultBlockState.Key(loc=loc,
                                        vga=ccmd_data.BoolType.from_bool(self._use_coeff),
                                        ranges=rngs,
                                        gain_val=self._coeff,
                                        calib_obj=calib_obj)

    @staticmethod
    def parse(args):
        return UseMultCmd._parse(args,UseMultCmd)

    @staticmethod
    def _parse(args,cls):
        result1 = ccmd_common.parse_pattern_use_block(args,0,1,2,
                                      cls.name(),
                                     index=True)

        result2 = ccmd_common.parse_pattern_use_block(args,0,0,3,
                                      cls.name(),
                                      index=True)

        if result1.success:
            data = result1.value
            return cls(data['chip'],data['tile'],
                       data['slice'],data['index'],
                       in0_range=data['range0'],
                       in1_range=spec_enums.RangeType.MED,
                       out_range=data['range1'],
                       use_coeff=True,
                       coeff=data['value0'])

        elif result2.success:
            data = result2.value
            return cls(data['chip'],data['tile'],
                       data['slice'],data['index'],
                       in0_range=data['range0'],
                       in1_range=data['range1'],
                       out_range=data['range2'],
                       use_coeff=False, coeff=0)

        elif not result1.success and not result2.success:
            msg = result1.message
            msg += "OR\n"
            msg += result2.message
            raise Exception(msg)


    @staticmethod
    def name():
        return 'use_mult'

    def __repr__(self):
        cmd = "use_mult {chip} {tile} {slice} {index} "
        if self._use_coeff:
            cmd += "val {coeff} rng {in_range} {out_range}"
            st = cmd.format(\
                            chip=self.loc.chip,
                            tile=self.loc.tile,
                            slice=self.loc.slice,
                            index=self.loc.index,
                            coeff=self._coeff,
                            in_range=self._in0_range.abbrev(),
                            out_range=self._out_range.abbrev())
        else:
            cmd += "rng {in0_range} {in1_range} {out_range}"
            st = cmd.format(
                chip=self.loc.chip,
                tile=self.loc.tile,
                slice=self.loc.slice,
                index=self.loc.index,
                in0_range=self._in0_range.abbrev(),
                in1_range=self._in1_range.abbrev(),
                out_range=self._out_range.abbrev())

        return st

