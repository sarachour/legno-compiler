from hwlib.adp import ADP,ADPMetadata
from dslang.dsprog import DSProgDB


def analyze(adp,waveform):
    program = DSProgDB.get_prog(adp.metadata[ADPMetadata.Keys.DSNAME])
    print(waveform.max_time, waveform.rec_max_time)

    print(program)
    raise NotImplementedError
