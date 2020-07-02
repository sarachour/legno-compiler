

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
    loc = layout.loc('indec',[c,t,s,0])
    layout.block_at('integrator',[c,t,s,0])
    layout.block_at('multiplier',[c,t,s,0])
    layout.block_at('multiplier',[c,t,s,1])
    layout.block_at('fanout',[c,t,s,0])
    layout.block_at('fanout',[c,t,s,1])
    layout.block_at('dac',[c,t,s,0])
    if z in [0,2]:
      layout.block_at('adc',[c,t,s,0])
      layout.block_at('lut',[c,t,s,0])

    if (c,t,s) in external_locs:
      if (c,t,s) in external_outs:
        layout.block_out('extout',[c,t,s,0])
      if (c,t,s) in external_inps:
        layout.block_out('extin',[c,t,s,0])
    else:
      layout.block_at('cin',layout,[c,t,s,0])
      layout.block_at('cout',layout,[c,t,s,0])

  for x,y,z,w in layout.locs('index'):
    layout.block_at('tin',[x,y,z,w])
    layout.block_at('tout',[x,y,z,w])

  for (c1,t1,s1,i1),(c2,t2,s2,i2),sign \
      in chip0_chip1 + chip1_chip0:
    if sign == '-':
      pass

def make_connections(layout):
  raise NotImplementedError

def make(board):
  layout = board.layout
  layout.add_view('chip')
  layout.add_view('tile','chip')
  layout.add_view('slice','tile')
  layout.add_view('index','slice')

  layout.add_locs('chip',[0,1])
  layout.add_locs('tile',[0,1,2,3])
  layout.add_locs('slice',[0,1,2,3])
  layout.add_locs('index',[0,1,2,3])

  make_instances(layout)
