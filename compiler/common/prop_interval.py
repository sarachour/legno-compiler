from compiler.common.visitor import Visitor
import hwlib.props as props
import ops.op as ops
from ops.interval import Interval, IRange, IValue

class PropOpRangeVisitor(Visitor):

  def __init__(self,prog,adp):
    Visitor.__init__(self,adp)
    self.prog = prog
    self.hardware_op_ranges()


  def hardware_op_ranges(self):
    def ival_port_to_range(block,config,port,handle=None):
      assert(not config.scale_mode is None)
      assert(not config.comp_mode is None)
      return block.props(config.comp_mode,\
                         config.scale_mode,\
                         port,\
                         handle=handle).interval()
    '''main body '''
    adp = self.adp
    for block_name,loc,config in adp.instances():
        block = adp.board.block(block_name)
        mode = config.comp_mode
        for port in block.inputs + block.outputs:
            hwrng = ival_port_to_range(block,config,port)
            config.set_op_range(port,hwrng)
            for handle in block.handles(mode,port):
                hwrng = ival_port_to_range(block,config,port, \
                                           handle=handle)
                config.set_op_range(port,hwrng,\
                                    handle=handle)


class PropIntervalVisitor(Visitor):

  def __init__(self,prog,adp):
    Visitor.__init__(self,adp)
    self.prog = prog
    self.adp = adp
    self.math_label_ranges()


  def math_label_ranges(self):
    prog,adp = self.prog,self.adp
    for block_name,loc,config in adp.instances():
        block = adp.board.block(block_name)
        if not block_name == 'integrator' and \
           not block_name == 'ext_chip_in' and \
           not block_name == 'ext_chip_analog_in':
          continue

        for port in block.outputs + block.inputs:
            if config.has_label(port):
                label = config.label(port)
                if port in block.outputs:
                    handle = block.get_dynamics(config.comp_mode,\
                                                port).toplevel()
                else:
                    handle = None

                mrng = prog.get_interval(label)
                config.set_interval(port,mrng,\
                                    handle=handle)
                print("ival lbl %s[%s].%s:%s => %s" % (block_name,loc,port,handle,mrng))


  def is_free(self,block_name,loc,port):
    config = self.adp.config(block_name,loc)
    return config.interval(port) is None \
            or config.interval(port).unbounded()

  def input_port(self,block_name,loc,port):
    #print("visit inp %s[%s].%s" % (block_name,loc,port))
    Visitor.input_port(self,block_name,loc,port)
    adp = self.adp
    config = adp.config(block_name,loc)
    dest_expr = ops.Const(0.0 if not config.has_dac(port) \
                          else config.dac(port))
    dest_ival = dest_expr.infer_interval({}).interval

    for src_block_name,src_loc,src_port in \
        adp.get_conns_by_dest(block_name,loc,port):
      src_config = adp.config(src_block_name,src_loc)
      src_ival = src_config.interval(src_port)
      if(src_ival is None):
        print("free: %s[%s].%s\n" % (src_block_name,src_loc,src_port))
        raise Exception("unknown interval: %s[%s].%s" % \
                        (src_block_name,src_loc,src_port))

      dest_ival = dest_ival.add(src_ival)

    config.set_interval(port,dest_ival)
    #print("ival in %s[%s].%s => %s" % (block_name,loc,port,dest_ival))

  def output_port(self,block_name,loc,port):
    #print("visit out %s[%s].%s" % (block_name,loc,port))
    adp = self.adp
    block = adp.board.block(block_name)
    config = adp.config(block_name,loc)

    if self.visited(block_name,loc,port):
      return

    if not config.interval(port) is None:
      self.visit(block_name,loc,port)
      return

    # don't apply any coefficients
    if not config.has_expr(port):
      expr = block.get_dynamics(config.comp_mode,port)
    else:
      expr = config.expr(port,inject=False)

    # try to infer the intervals without resolving ports
    try:
      intervals = expr.infer_interval(config.intervals())
      config.set_interval(port,intervals.interval)
      #print("ival out %s[%s].%s => %s" % (block_name,loc,port,intervals.interval))
      self.visit(block_name,loc,port)
      return
    except Exception as e:
      pass

    free,bound = self.classify(block_name,loc,expr.vars())
    for free_var in free:
      self.port(block.name,loc,free_var)

    intervals = expr.infer_interval(config.intervals())
    config.set_interval(port,intervals.interval)
    #print("ival out %s[%s].%s => %s" % (block_name,loc,port,intervals.interval))
    for handle,interval in intervals.bindings():
      config.set_interval(port, \
                          interval, \
                          handle=handle)

    config.set_interval(port,intervals.interval)




  def is_valid(self):
    adp = self.adp
    valid = True
    for block_name,loc,config in adp.instances():
      for ival in config.intervals().values():
        if ival.unbounded():
           valid = False

    return valid



  def all(self,inputs=False):
    circ = self._circ
    for block_name,loc,config in circ.instances():
      block = circ.board.block(block_name)
      for inp in block.inputs:
        self.input_port(block_name,loc,inp)

    for block_name,loc,config in circ.instances():
      self.block(block_name,loc)

def compute_intervals(prog,adp):
  visitor = PropIntervalVisitor(prog,adp)
  visitor.all()
  while(not visitor.is_valid()):
      visitor.clear()
      visitor.all()

def compute_op_ranges(prog,adp):
  visitor = PropOpRangeVisitor(prog,adp)
  visitor.all()
  while(not visitor.is_valid()):
      visitor.clear()
      visitor.all()

def clear_intervals(adp):
  for block_name,loc,config in adp.instances():
        config.clear_intervals()
