

external_outs = [
  (0,3,3),
  (0,3,2),
  (1,3,3),
  (1,3,2)

]

external_inps = [
  (1,3,2),
  (1,3,3)
]

external_unused_inps = [
  (0,3,2),
  (0,3,3)
]
external_locs = external_inps + external_unused_inps + \
                external_outs

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
def make_instances(layout):

  for c,t,s in layout.locs('slice'):
    layout.block_at('integ',[c,t,s,0])
    layout.block_at('mult',[c,t,s,0])
    layout.block_at('mult',[c,t,s,1])
    layout.block_at('fanout',[c,t,s,0])
    layout.block_at('fanout',[c,t,s,1])
    layout.block_at('dac',[c,t,s,0])
    if s in [0,2]:
      layout.block_at('adc',[c,t,s,0])
      layout.block_at('lut',[c,t,s,0])

    if (c,t,s) in external_locs:
      if (c,t,s) in external_outs:
        layout.block_at('extout',[c,t,s,0])
      if (c,t,s) in external_inps:
        layout.block_at('extin',[c,t,s,0])
    else:
      layout.block_at('cin',[c,t,s,0])
      layout.block_at('cout',[c,t,s,0])

  for x,y,z,w in layout.locs('index'):
    layout.block_at('tin',[x,y,z,w])
    layout.block_at('tout',[x,y,z,w])

  for (c1,t1,s1,i1),(c2,t2,s2,i2),sign \
      in chip0_chip1 + chip1_chip0:
    if sign == '-':
      pass

def make_connections(dev,layout):
  WC = layout.WILDCARD
  for block1 in ['mult',
                 'integ',
                 'fanout',
                 'dac',
                 'tin']:
    for block2 in [
        'mult',
        'integ',
        'fanout',
        'adc',
        'tout'
    ]:
      for op in dev.get_block(block1).outputs:
        for ip in dev.get_block(block2).inputs:
          for c,t in layout.locs('tile'):
            layout.connect(block1,[c,t,WC,WC],op.name, \
                           block2,[c,t,WC,WC],ip.name)

  for c,t,s,i in layout.instances('adc'):
    layout.connect("adc",[c,t,s,i],'z','lut',[c,t,s,i],'x')
    layout.connect("lut",[c,t,s,i],'z','dac',[c,t,s,i],'x')

  for block1 in ['tout']:
    for block2 in ['cout','extout']:
      for c,t in layout.locs('tile'):
        layout.connect(block1,[c,t,WC,WC],'z',block2,[c,t,WC,WC],'x')

  for block1 in ['extin','cin']:
    for block2 in ['tin']:
      for c,t in layout.locs('tile'):
        layout.connect(block1,[c,t,WC,WC],'z',block2,[c,t,WC,WC],'x')


def make(board):
  layout = board.layout
  layout.set_views(['chip','tile','slice','index'])

  layout.add_locs('chip',[0,1])
  layout.add_locs('tile',[0,1,2,3])
  layout.add_locs('slice',[0,1,2,3])
  layout.add_locs('index',[0,1,2,3])

  make_instances(layout)
  make_connections(board,layout)
