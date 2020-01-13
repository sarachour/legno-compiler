from hwlib.hcdc.integ import block as integ
from hwlib.hcdc.mult import block as mult
from hwlib.hcdc.crossbar import tile_in, tile_out, \
    chip_in, chip_out, inv_conn

from hwlib.hcdc.extern import block_in as ext_chip_in
from hwlib.hcdc.extern import block_out as ext_chip_out
from hwlib.hcdc.extern import block_analog_in as ext_chip_analog_in
from hwlib.hcdc.io import dac as tile_dac
from hwlib.hcdc.io import adc as tile_adc
from hwlib.hcdc.fanout import block as fanout
from hwlib.hcdc.lut import block as lut

import hwlib.hcdc.globals as glb
from hwlib.board import Board


BLACKLIST = []
# these integrators failed to calibrate, it cannot
# find calibration codes that produce a steady state of zero for these guys,
# given an input current of zero when in high-medium mode.
# i tried doing a brute force search for calibration, to no avail.
BLACKLIST += [
    ("multiplier","(HDACv2,0,3,1,1)"),
    ("adc","(HDACv2,0,0,0,0)")
]

def test_board(board,n_chips):
    mult = board.block('multiplier')
    assert(board.route_exists(mult.name,board.position_string([0,0,0,1]),'out',
                            mult.name,board.position_string([0,0,0,0]),'in0'))
    assert(board.route_exists(mult.name,board.position_string([0,0,1,1]),'out',
                            mult.name,board.position_string([0,0,0,0]),'in0'))
    assert(board.route_exists(mult.name,board.position_string([0,1,1,1]),'out',
                            mult.name,board.position_string([0,0,0,0]),'in0'))
    if n_chips > 1:
        assert(board.route_exists(mult.name,board.position_string([1,1,1,1]),'out',
                                mult.name,board.position_string([1,0,0,0]),'in0'))
        assert(board.route_exists(mult.name,board.position_string([0,1,1,1]),'out',
                                mult.name,board.position_string([1,0,0,0]),'in0'))


def connect(hw,scope1,block1,scope2,block2,negs=[]):
    count = 0
    for loc1 in hw.block_locs(scope1,block1.name):
        for loc2 in hw.block_locs(scope2,block2.name):
            for outport in block1.outputs:
                for inport in block2.inputs:
                    outprop = block1.signals(outport)
                    inprop= block2.signals(inport)
                    if outprop == inprop:
                        hw.conn(block1.name,loc1,outport,
                                block2.name,loc2,inport)
                        count += 1

    if count == 0:
        print("no connections made: %s to %s" % (block1.name,block2.name))

def connect_adj_list(hw,block1,block2,adjlist):
    for loc1,loc2,sign in adjlist:
        do_invert = True if sign == "-" else False
        for outport in block1.outputs:
            for inport in block2.inputs:
                outprop = block1.signals(outport)
                inprop= block2.signals(inport)
                if outprop == inprop:
                    if not do_invert:
                        hw.conn(block1.name,
                                hw.position_string(loc1),
                                outport,
                                block2.name,
                                hw.position_string(loc2),
                                inport)
                    else:
                         hw.conn(block1.name,
                                 hw.position_string(loc1),
                                 outport,
                                 'conn_inv',
                                 hw.position_string(loc1),
                                 'in')
                         hw.conn('conn_inv',
                                 hw.position_string(loc1),
                                 'out',
                                 block2.name,
                                 hw.position_string(loc2),
                                 inport)


def make_board(subset=glb.HCDCSubset.UNRESTRICTED,load_conns=True):
    n_chips = 2
    #no chip interconnects for now
    n_tiles = 4
    n_slices = 4
    is_extern_out = lambda tile_no,slice_no : tile_no == 3 \
                    and (slice_no == 2 or slice_no == 3)

    hw = Board("HDACv2",Board.CURRENT_MODE)
    blocks = [lut,integ,tile_dac,tile_adc,mult,fanout] + \
           [tile_in,tile_out,chip_in,chip_out,inv_conn] + \
           [ext_chip_in,ext_chip_out,ext_chip_analog_in]
    hw.add(list(map(lambda b: b.subset(subset), blocks)))

    hw.set_time_constant(glb.TIME_FREQUENCY)
    hw.set_blacklist(BLACKLIST)

    chips = map(lambda i : hw.layer(i),range(0,n_chips))
    for chip_idx,chip in enumerate(chips):
        tiles = map(lambda i : chip.layer(i), range(0,n_tiles))
        for tile_idx,tile in enumerate(tiles):
            slices = map(lambda i : tile.layer(i),
                         range(0,n_slices))
            for slice_idx,slce in enumerate(slices):
                layer0 = slce.layer(0)
                layer1 = slce.layer(1)
                layer2 = slce.layer(2)
                layer3 = slce.layer(3)

                if slice_idx in [0,2]:
                    # DEMO_BOARD_6, adc doesn't work on 0.0.0.0
                    layer0.inst('tile_adc')
                    layer0.inst('lut')

                layer0.inst('tile_dac')
                layer0.inst('fanout')
                layer1.inst('fanout')
                layer0.inst('integrator')
                layer0.inst('multiplier')
                layer1.inst('multiplier')


                for layer in [layer0,layer1,layer2,layer3]:
                    layer.inst('tile_in')
                    layer.inst('tile_out')

                if not is_extern_out(tile_idx,slice_idx):
                    layer0.inst("chip_out")
                    layer0.inst("chip_in")

                else:
                    adc = layer0.inst('ext_chip_out')

                    if chip_idx == 0:
                        dac = layer0.inst('ext_chip_in')
                    elif chip_idx == 1:
                        dac = layer0.inst('ext_chip_analog_in')

                    assert(tile_idx == 3)
                    assert(slice_idx == 2 or slice_idx == 3)
                    if slice_idx == 2 and chip_idx == 0:
                        hw.add_handle('A0','ext_chip_out',loc=adc)
                        hw.add_handle('D0','ext_chip_in',loc=dac)
                    elif slice_idx == 3 and chip_idx == 0:
                        hw.add_handle('A1','ext_chip_out',loc=adc)
                        hw.add_handle('D1','ext_chip_in',loc=dac)
                    elif slice_idx == 2 and chip_idx == 1:
                        hw.add_handle('A2','ext_chip_out',loc=adc)
                        hw.add_handle('E1','ext_chip_analog_in',loc=dac)
                    elif slice_idx == 3 and chip_idx == 1:
                        hw.add_handle('A3','ext_chip_out',loc=adc)
                        hw.add_handle('E2','ext_chip_analog_in',loc=dac)


    chip0_chip1 = [
        ([0,0,0,0],[1,1,3,0],'+'),
        ([0,0,1,0],[1,1,2,0],'+'),
        ([0,0,2,0],[1,1,1,0],'+'),
        ([0,0,3,0],[1,1,0,0],'+'),
        ([0,1,0,0],[1,2,3,0],'-'),
        ([0,1,1,0],[1,2,2,0],'-'),
        ([0,1,2,0],[1,2,1,0],'-'),
        ([0,1,3,0],[1,2,0,0],'-'),
        ([0,2,0,0],[1,0,3,0],'+'),
        ([0,2,1,0],[1,0,2,0],'+'),
        ([0,2,2,0],[1,0,1,0],'+'),
        ([0,2,3,0],[1,0,0,0],'+'),
        ([0,3,0,0],[1,3,0,0],'+'),
        ([0,3,1,0],[1,3,1,0],'+')
    ]

    chip1_chip0 = [
        ([1,0,0,0],[0,1,3,0],'+'),
        ([1,0,1,0],[0,1,2,0],'+'),
        ([1,0,2,0],[0,1,1,0],'+'),
        ([1,0,3,0],[0,1,0,0],'+'),
        ([1,1,0,0],[0,2,3,0],'-'),
        ([1,1,1,0],[0,2,2,0],'-'),
        ([1,1,2,0],[0,2,1,0],'-'),
        ([1,1,3,0],[0,2,0,0],'-'),
        ([1,2,0,0],[0,0,3,0],'+'),
        ([1,2,1,0],[0,0,2,0],'+'),
        ([1,2,2,0],[0,0,1,0],'+'),
        ([1,2,3,0],[0,0,0,0],'+'),
        ([1,3,0,0],[0,3,0,0],'+'),
        ([1,3,1,0],[0,3,1,0],'+'),
    ]
    for loc1,loc2,sign in chip0_chip1 + chip1_chip0:
        if n_chips > 1:
            if sign == "-":
                layer1 = hw.sublayer(loc1)
                layer1.inst('conn_inv')

    hw.freeze_instances()

    if not load_conns:
        return hw

    for chip1 in range(0,n_chips):
        chip1_layer = hw.layer(chip1)
        for chip2 in range(0,n_chips):
            chip2_layer = hw.layer(chip2)
            if chip1 == chip2:
                continue

            for block1 in [chip_out]:
                for block2 in [chip_in]:
                    if n_chips > 1:
                        connect_adj_list(hw,block1,block2,chip1_chip0  \
                                         + chip0_chip1)

    chip1_layer, chip2_layer = None, None
    for chip_no in range(0,n_chips):
        # two of the inputs and outputs on each chip
        # are connected to the board.
        chip_layer = hw.layer(chip_no)
        for tile1 in range(0,n_tiles):
            tile1_layer = chip_layer.layer(tile1)
            for tile2 in range(0,n_tiles):
                tile2_layer = chip_layer.layer(tile2)
                if tile1 == tile2:
                    continue

                for block1 in [tile_out]:
                    for block2 in [tile_in]:
                        if tile1 != tile2:
                            connect(hw,tile1_layer,block1,tile2_layer,block2)

        # connect components in each tile
        for tile_no in range(0,n_tiles):
            tile_layer = chip_layer.layer(tile_no)

            # compute
            for block1 in [mult,integ,fanout,tile_dac,tile_in]:
                for block2 in [mult,integ,fanout,tile_adc,tile_out]:
                    # FIXME: connect all to all
                    connect(hw,tile_layer,block1,tile_layer,block2)

            for block1 in [tile_out]:
                for block2 in [chip_out,ext_chip_out]:
                    connect(hw,tile_layer,block1,chip_layer,block2)

            for block1 in [chip_in, \
                           ext_chip_in if chip_no == 0 else ext_chip_analog_in]:
                for block2 in [tile_in]:
                    connect(hw,chip_layer,block1,tile_layer,block2)


            for block1 in [tile_adc]:
                for block2 in [lut]:
                    #FIXME: connect all to all
                    connect(hw,tile_layer,block1,tile_layer,block2)


            for block1 in [lut]:
                for block2 in [tile_dac]:
                    #FIXME: connect all to all
                    connect(hw,tile_layer,block1,tile_layer,block2)

    test_board(hw,n_chips=n_chips)
    return hw

#board = make_board()
#for blk in board.blocks:
#    n = board.num_blocks(blk.name)
#    print("%s = %d" % (blk.name,n))
#input()
