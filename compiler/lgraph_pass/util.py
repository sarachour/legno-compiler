import itertools
#import hwlib.props as prop
#import hwlib.abs as acirc
import random
import math

class TryObject:

    def __init__(self,name,n_succ,n_fail):
        self._max_succ = n_succ
        self._max_fail = n_fail
        self._n_succ = 0
        self._n_fail = 0
        self._name = name
        self._next_iter = False

    def succeed(self):
        if self.successes_left()  \
           and self._next_iter:
            self._n_succ += 1
            self._next_iter = False

    def fail(self):
        if self.failures_left():
            self._n_fail += 1

    def clear(self):
        self._n_succ = 0
        self._n_fail = 0

    def iterate(self,gen,do_succeed=True):
        if not self.successes_left() or \
               not self.failures_left():
            return

        succeeded = False
        for result in gen:
            self._next_iter = True
            if do_succeed:
                self.succeed()
            yield result
            succeeded = True
            if not self._max_succ is None:
                print(self)

            if not self.successes_left() or \
               not self.failures_left():
                break

        if not succeeded:
            if not self._max_fail is None:
                print(self)
            self.fail()


    def enumerate(self,gen,do_succeed=True):
        for idx,result in enumerate(self.iterate(gen,do_succeed)):
            yield idx,result

    def failures_left(self):
        if self._max_fail is None:
            return True

        return self._n_fail < self._max_fail

    def successes_left(self):
        if self._max_succ is None:
            return True

        return self._n_succ < self._max_succ

    def __repr__(self):
        rpr = "[%s] " % self._name
        if not self._max_succ is None:
            rpr += "succ=%d/%d " % (self._n_succ,self._max_succ)
        if not self._max_fail is None:
            rpr += "fail=%d/%d " % (self._n_fail,self._max_fail)

        return rpr

def all_same(gen):
    value = gen.__next__()
    for item in gen:
        if item != value:
            return False
    return True

def sample(optmap):
    choice = {}
    for var_name,choices in optmap.items():
        idx = random.randint(0,len(choices)-1)
        choice[var_name] = idx

    return choice

def group_by(generator,key):
    items = {}
    for el in generator:
        el_key = key(el)
        if not el_key in items:
            items[el_key] = []

        items[el_key].append(el)

    return items

def counts(lst):
    els = {}
    for el in lst:
        if not el in els:
            els[el] = 0
        els[el] += 1
    return els

def has_duplicates(lst):
    els = counts(lst)
    for el,cnt in els.items():
        if cnt > 1:
             return True
    return False

def enumerate_tree(block,n,max_blocks=None,
                   permute_input=False,prop=None):
    nels = len(block.by_signal(prop,block.inputs)) if permute_input \
       else len(block.by_signal(prop,block.outputs))

    def compute_max_depth(n,n_ports):
        if n <= n_ports:
            return 1
        else:
            return 1+\
                compute_max_depth(n-(n_ports-1),n_ports)

    def count_free(levels):
        cnt = 0
        for idx in range(0,len(levels)):
            if idx == len(levels)-1:
                cnt += levels[idx]*nels

            else:
                cnt += levels[idx]*nels-levels[idx+1]

        return cnt

    levels = [1]
    max_depth = compute_max_depth(n,nels)
    choices = []
    for depth in range(0,max_depth):
        max_nodes = nels**depth
        choices.append(range(1,max_nodes+1))

    for depth in range(0,max_depth):
        for counts in itertools.product(*choices[0:depth+1]):
            if not max_blocks is None \
               and sum(counts) > max_blocks:
                continue

            free_ports = count_free(counts)
            if free_ports >= n + nels or free_ports < n:
                continue

            yield counts

def bitree_split(fan,levels_):
  n_comps = list(levels_[1:])
  max_comps = list(map(lambda idx: fan**(idx+1), \
                range(0,len(n_comps))))

  for fan_id in range(0,fan):
    new_n_cmps = []
    print(n_comps,max_comps)
    for max_cmp,n_cmp in zip(max_comps,n_comps):
      value = n_cmp if n_cmp < max_cmp else max_cmp
      new_n_cmps.append(math.ceil(value/fan))

    yield new_n_cmps

    for idx,new_n_cmp in enumerate(new_n_cmps):
      n_comps[idx] -= new_n_cmp



def build_input_tree_from_levels(board,levels,block,inports,outport,mode='?'):
  nodes = {}

  def mknode():
    node = acirc.ANode.make_node(board,block.name)
    node.config.set_comp_mode(mode)
    nodes[node.id] = node
    return node

  def recurse(levels,depth=0):
    assert(levels[0] <= 1)
    if levels[0] == 0:
      return [],None

    curr_node = mknode()
    # cannot connect more nodes than number of inputs
    free_ports = []
    offset = 0
    if len(levels) > 1:
      for inport_id,new_levels in \
          enumerate(bitree_split(len(inports),levels)):
        ch_free_ports,child_node = recurse(new_levels,depth=depth+1)
        free_ports += ch_free_ports
        if not child_node is None:
          offset = inport_id+1
          acirc.ANode.connect(
              child_node,outport,
              curr_node,inports[inport_id]
          )

    for inport_id in range(offset,len(inports)):
      free_ports.append((depth,curr_node,inports[inport_id]))

    return free_ports,curr_node

  free_ports,curr_node = recurse(levels)
  free_port_levels = {}
  for level,node,port in free_ports:
    if not level in free_port_levels:
      free_port_levels[level] = []
    free_port_levels[level].append((node,port))

  return free_port_levels,curr_node,outport,nodes


def build_output_tree_from_levels(board,levels,block,outports,inport,mode='?'):
  nodes = {}
  def mknode():
    node = acirc.ANode.make_node(board,block.name)
    node.config.set_comp_mode(mode)
    nodes[node.id] = node
    return node

  def recurse(levels,depth=0):
    assert(levels[0] <= 1)
    if levels[0] == 0:
      return [],None

    curr_node = mknode()
    # cannot connect more nodes than number of inputs
    free_ports = []
    offset = 0
    if len(levels) > 1:
      for outport_id,new_levels in \
          enumerate(bitree_split(len(outports),levels)):
        ch_free_ports,child_node = recurse(new_levels,depth=depth+1)
        free_ports += ch_free_ports
        if not child_node is None:
          offset = outport_id+1
          acirc.ANode.connect(
              curr_node,outports[outport_id],
              child_node,inport
          )

    for outport_id in range(offset,len(outports)):
      free_ports.append((depth,curr_node,outports[outport_id]))
    return free_ports,curr_node

  free_ports,curr_node = recurse(levels)
  free_port_levels = {}
  for level,node,port in free_ports:
    if not level in free_port_levels:
      free_port_levels[level] = []
    free_port_levels[level].append((node,port))


  return free_port_levels,curr_node,inport,nodes


def build_tree_from_levels(board,levels,block,inputs,output,
                           input_tree=False,
                           mode='?',
                           prop=None):
    blocks = []
    free_ports = {}

    if input_tree:
      free_ports,root_node,root_port,nodes = \
        build_input_tree_from_levels(board,levels,block,inputs,output,mode=mode)
    else:
      free_ports,root_node,root_port,nodes = \
        build_output_tree_from_levels(board,levels,block,inputs,output,mode=mode)

    for level in free_ports:
      for node,port in free_ports[level]:
        if not root_node.contains(node):
          raise Exception("level: <%s> not in <%s>" % \
                          (node,root_node))

    return free_ports,root_node,root_port,nodes


def input_level_combos(level_inputs,sources):
    input_ports = []
    for level,inputs in level_inputs.items():
        input_ports += inputs

    for combo in itertools.permutations(input_ports,len(sources)):
        assigns = list(zip(combo,sources))
        unused = []
        for blk,port in input_ports:
          assigned = False
          for (blk2,port2),_ in assigns:
            if blk.id == blk2.id and port == port2:
              assigned = True

          if not assigned:
            unused.append((blk,port))

        yield unused,assigns



def validate_fragment(frag):
    def test_inputs(inps,connected=True):
         for inp in inps:
            if frag.get_input_conn(inp) is None and connected:
                raise Exception("\n%s\n<<input %s not connected>>" % \
                                (frag.to_str(),inp))
            elif not frag.get_input_conn(inp) is None and not connected:
                raise Exception("\n%s\n<<input %s connected>>" % \
                                (frag.to_str(),inp))

         return True

    if isinstance(frag, acirc.ABlockInst):
      if frag.block.name == 'multiplier':
        #print(frag.id,frag.config.comp_mode)
        if frag.config.comp_mode == 'vga':
          test_inputs(['in0'])
          test_inputs(['in1','coeff'],connected=False)
        else:
          test_inputs(['in0','in1'])
          test_inputs(['coeff'],connected=False)
      elif frag.block.name == 'tile_dac':
        test_inputs(['in'],connected=False)
      else:
        raise Exception("unimplemented block: %s" % frag.block.name)


      for subn in frag.subnodes():
        validate_fragment(subn)

    elif isinstance(frag,acirc.AConn):
        snode,sport = frag.source
        validate_fragment(snode)

    elif isinstance(frag,acirc.AInput):
        return

    elif isinstance(frag,acirc.AJoin):
        assert(len(list(frag.subnodes())) > 0)
        for subn in frag.subnodes():
            validate_fragment(subn)

    else:
        raise Exception("unimplemented:validate %s" % frag)
