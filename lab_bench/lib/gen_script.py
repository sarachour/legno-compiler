import lab_bench.lib.chipcmd.state as statelib
import lab_bench.lib.chipcmd.use as uselib
import lab_bench.lib.chipcmd.data as datalib
import lab_bench.lib.enums as glb_enums
# generates a grendel script for database
def generate_commands(state):
    for obj in state.get_all():
        if obj.block == glb_enums.BlockType.FANOUT:
            cmd = uselib.UseFanoutCmd(chip=obj.loc.chip,
                                      tile=obj.loc.tile,
                                      slice=obj.loc.slice,
                                      index=obj.loc.index,
                                      inv0=obj.key.invs[glb_enums.PortName.OUT0],
                                      inv1=obj.key.invs[glb_enums.PortName.OUT1],
                                      inv2=obj.key.invs[glb_enums.PortName.OUT2],
                                      in_range=obj.key.rng,
                                      third=obj.key.third)
            yield cmd

        elif obj.block == glb_enums.BlockType.INTEG:
            cmd = uselib.UseIntegCmd(chip=obj.loc.chip,
                                     tile=obj.loc.tile,
                                     slice=obj.loc.slice,
                                     init_cond=obj.key.ic_val,
                                     in_range=obj.key.ranges[glb_enums.PortName.IN0],
                                     out_range=obj.key.ranges[glb_enums.PortName.OUT0],
                                     debug=obj.key.exception,
                                     inv=obj.key.inv)
            yield cmd

        elif obj.block == glb_enums.BlockType.DAC:
            cmd = uselib.UseDACCmd(chip=obj.loc.chip,
                                   tile=obj.loc.tile,
                                   slice=obj.loc.slice,
                                   value=obj.key.const_val,
                                   source=obj.key.source,
                                   inv=obj.key.inv,
                                   out_range=obj.key.rng
            )
            yield cmd

        elif obj.block == glb_enums.BlockType.ADC:
            cmd = uselib.UseADCCmd(chip=obj.loc.chip,
                                   tile=obj.loc.tile,
                                   slice=obj.loc.slice,
                                   in_range=obj.key.rng
            )
            yield cmd

        elif obj.block == glb_enums.BlockType.MULT:
            cmd = uselib.UseMultCmd(chip=obj.loc.chip,
                                    tile=obj.loc.tile,
                                    slice=obj.loc.slice,
                                    index=obj.loc.index,
                                    in0_range=obj.key.ranges[glb_enums.PortName.IN0],
                                    in1_range=obj.key.ranges[glb_enums.PortName.IN1],
                                    out_range=obj.key.ranges[glb_enums.PortName.OUT0],
                                    coeff=obj.key.gain_val,
                                    use_coeff=obj.key.vga
            )
            yield cmd

def generate(state,filename):
    cmdbuf = []
    for cmd in generate_commands(state):
        cmdbuf.append(str(cmd))

    uniq = set(cmdbuf)
    with open(filename,'w') as fh:
        for cmd in uniq:
            fh.write("%s\n" % cmd)

