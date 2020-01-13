import hwlib.hcdc.hcdcv2_4 as hcdc
import hwlib.hcdc.globals as glb
import scripts.visualize.common as common

to_header = {
  'tile_out': 'tout',
  'tile_in': 'tin',
  'chip_in': 'vin',
  'chip_out': 'vout',
  'ext_chip_out': 'cout',
  'ext_chip_in': 'cin',
  'tile_dac':'dac',
  'tile_adc':'adc',
  'lut':'lut',
  'fanout': 'fan',
  'multiplier': 'mul',
  'integrator': 'int',
}
to_desc = {
  'tile_out': 'inter-tile output',
  'tile_in' : 'inter-tile input',
  'chip_in': 'inter-chip input',
  'chip_out': 'inter-chip output',
  'ext_chip_out': 'external chip output',
  'ext_chip_in': 'external chip input',
  'tile_dac': 'digital-to-analog converter',
  'tile_adc': 'analog to digital converter',
  'lut': 'programmable user-defined function',
  'fanout': 'current copier',
  'multiplier': 'current multiplier/scaling block',
  'integrator': 'current integrator'
}
to_type = {
  'tile_out': 'route',
  'tile_in': 'route',
  'chip_out': 'route',
  'chip_in': 'route',
  'chip_out': 'compute',
  'ext_chip_in': 'compute',
  'ext_chip_out': 'compute',
  'tile_dac':'compute',
  'tile_adc':'compute',
  'lut':'compute',
  'fanout': 'copy',
  'multiplier': 'compute',
  'integrator': 'compute',
  'conns': 'connections',
}
to_expr = {
  ('multiplier','vga'): "$d_0 \cdot x_0$",
  ('multiplier','mul'): "$x_1 \cdot x_0$",
  ('integrator',None): "$z_0 = \int x_0$",
  ('integrator2',None): "$z_0(0) = d_0$",
  ('fanout',None): "$z_i = x_0$",
  ('lut',None): "$z_0 = f(d_0)$"
}

def count(iterator):
  x = 0
  for i in iterator:
    x += 1
  return x

def build_block_profile(block):
  n_comp_modes = len(block.comp_modes)
  n_modes = 0
  scale_modes = {}
  subset = glb.HCDCSubset('extended')
  block.subset(subset)
  for comp_mode in block.comp_modes:
    n_scale_modes = 0
    coeffs = []
    opranges = []
    for scm in block.scale_modes(comp_mode):
      if block.whitelist(comp_mode,scm):
        n_scale_modes += 1
        n_modes += 1;
        for port in block.outputs + block.inputs:
          for handle in list(block.handles(comp_mode,port)) \
              + [None]:

            if not handle is None:
              continue

            if port in block.outputs:
              coeffs.append(block.coeff(comp_mode, \
                                        scm, \
                                        port,
                                        handle))

            prop = block.props(comp_mode,scm,port,handle)
            opranges.append(prop.interval().bound)

    scale_modes[comp_mode] = {}
    scale_modes[comp_mode]['scale_modes'] = n_scale_modes
    scale_modes[comp_mode]['coeff_min'] = min(coeffs)
    scale_modes[comp_mode]['coeff_max'] = max(coeffs)
    scale_modes[comp_mode]['oprange_min'] = min(opranges)
    scale_modes[comp_mode]['oprange_max'] = max(opranges)

  cm = block.comp_modes[0]
  sm = block.scale_modes(cm)[0]

  inputs_analog = count(filter(lambda i: block.props(cm,sm,i).analog(), \
                      block.inputs))
  inputs_dig_const = count(filter(lambda i: not block.props(cm,sm,i).analog() and \
                                  block.props(cm,sm,i).is_constant, \
                                  block.inputs))

  inputs_dig_dyn = count(filter(lambda i: not block.props(cm,sm,i).analog() and \
                                  not block.props(cm,sm,i).is_constant, \
                                  block.inputs))

  inputs_dig_expr = 1 if block.name == 'lut' else 0


  outputs_analog = count(filter(lambda o: block.props(cm,sm,o).analog(), \
                      block.outputs))
  outputs_dig= count(filter(lambda o: not block.props(cm,sm,o).analog(), \
                      block.outputs))

  # FIXME
  if block.name == 'tile_dac':
    inputs_dig_const = 1
    n_modes *= 2
  if block.name == 'ext_chip_out':
    outputs_dig = 0
    outputs_analog = 1


  return {
    'modes': n_modes,
    'comp_modes':n_comp_modes,
    'scale_modes':scale_modes,
    'type':to_type[block.name] if block.name in to_type else None,
    'data_const':inputs_dig_const,
    'data_expr':inputs_dig_expr,
    'digital_inputs':inputs_dig_dyn,
    'digital_outputs':outputs_dig,
    'analog_inputs':inputs_analog,
    'analog_outputs':outputs_analog
  }

def build_circ_profile(board):
  profile = {'blocks':{}, 'conns':0}
  print("==== Build Block Profiles ====")
  for block in board.blocks:
    print(" -> %s" % block.name)
    block_profile = build_block_profile(block)
    block_profile['count'] = board.num_blocks(block.name)
    profile['blocks'][block.name] = block_profile

  print("==== Build Other Properties ====")
  profile['conns'] = count(board.connections())
  profile['time_constant'] = board.time_constant

  ext_inps = 0
  ext_outs = 0
  for h,b,l in board.handles():
    if b == 'ext_chip_out':
      ext_outs += 1
    elif b == 'ext_chip_analog_in':
      ext_inps += 1


  profile['ext_inputs'] = ext_inps
  profile['ext_outputs'] = ext_outs
  return profile

def build_board_summary(profile):
  desc = "board characteristics"
  table = common.Table('HDACv2 Board Characteristics', \
                       desc, 'hwboard','|ccc|cccc|ccc|ccc|ccc|',
                       benchmarks=False)
  fields = ['property', \
            'value']
  table.set_fields(fields)

  row = {}
  row['property'] = 'time constant'
  row['value'] = '%d hz' % profile['time_constant']
  table.data(None,row)

  row = {}
  row['property'] = 'connections'
  row['value'] = '%d' % profile['conns']
  table.data(None,row)

  row = {}
  row['property'] = 'external inputs'
  row['value'] = profile['ext_inputs']
  table.data(None,row)

  row = {}
  row['property'] = 'external outputs'
  row['value'] = profile['ext_outputs']
  table.data(None,row)
  table.write(common.get_path('hwboard.tbl'))

def build_block_summary(profile):
  desc = "summaries of computational blocks available on device"
  table = common.Table('HDACv2 Board Block Summaries', \
                       desc, 'hwblocks','|ccc|cc|cc|cc|cc|',
                       benchmarks=False)
  table.two_column = True
  fields = ['block', \
            'type', \
            'count', \
            'analog_in', \
            'analog_out', \
            'digital_in', \
            'digital_out', \
            'data_const', \
            'data_expr', \
            'modes', \
            'desc'
  ]

  cat= ['','','',
        '\multicolumn{2}{c|}{analog}',
        '\multicolumn{2}{c|}{digital}',
        '\multicolumn{2}{c|}{data}',
        '',''
  ]
  table.set_fields(fields)
  table.horiz_rule()
  hdr = ['block', \
            'type', \
            'count', \
            'in', \
            'out', \
            'in', \
            'out', \
            'const', \
            'expr', \
            'modes', \
            'desc'
  ]
  table.raw(cat);
  table.raw(hdr);
  table.horiz_rule()
  for block in profile['blocks']:
    prof = profile['blocks'][block]

    if not block in to_header:
      continue

    row = {}
    row['block'] = "%s" % to_header[block]
    row['type'] = "%s" % prof['type']
    row['count'] = "%d" % prof['count']
    row['analog_in'] = prof['analog_inputs']
    row['analog_out'] = prof['analog_outputs']
    row['digital_in'] = prof['digital_inputs']
    row['digital_out'] = prof['digital_outputs']
    row['data_const'] = prof['data_const']
    row['data_expr'] = prof['data_expr']
    row['modes'] = prof['modes']
    row['desc'] = to_desc[block]
    table.data(None,row)
    '''
    if block == 'multiplier':
      for comp_mode,data in prof['scale_modes'].items():
        row = dict(row)
        row['compute mode'] = comp_mode
        row['function'] = to_expr[(block,comp_mode)]
        row['scale modes'] = data['scale_modes']

        if data['oprange_min'] == data['oprange_max']:
          row['operating bound'] = "%.1f" % (data['oprange_min'])
        else:
          row['operating bound'] = "%.1f-%.1f" \
                                 % (data['oprange_min'], \
                                    data['oprange_max'])
        if data['coeff_min'] == data['coeff_max']:
          row['gain'] = "%.1f x" % data['coeff_min']
        else:
          row['gain'] = "%.1f-%.1f x" \
                        % (data['coeff_min'], \
                           data['coeff_max'])
        table.data(None,row)

    else:
      comp_modes = list(prof['scale_modes'].keys())
      row['compute mode'] = "%d" % len(comp_modes)
      data = prof['scale_modes'][comp_modes[0]]
      row['scale_modes'] = data['scale_modes']
      if (block,None) in to_expr:
        row['function'] = to_expr[(block,None)]
      else:
        row['function'] = '$z_0 = x_0$'

      row['scale modes'] = data['scale_modes']
      if data['oprange_min'] == data['oprange_max']:
          row['operating bound'] = "%.1f" % (data['oprange_min'])
      else:
        row['operating bound'] = "%.1f-%.1f" \
                               % (data['oprange_min'], \
                                  data['oprange_max'])
      if data['coeff_min'] == data['coeff_max']:
        row['gain'] = "%.1f x" % data['coeff_min']
      else:
        row['gain'] = "%.1f -%.1f x" \
                      % (data['coeff_min'], \
                         data['coeff_max'])
      table.data(None,row)
      if block == "integrator":
        row = dict(map(lambda f: (f,""),fields))
        row['function'] =to_expr[('integrator2',None)]
        table.data(None,row)
    '''

  table.horiz_rule()
  table.write(common.get_path('hwblocks.tbl'))


def visualize(db):
  print("==== Construct Board ====")
  board = hcdc.make_board()
  profile = build_circ_profile(board)
  build_block_summary(profile)
  build_board_summary(profile)

