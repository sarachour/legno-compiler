import os
import colorlover
import ops.op as op
import math
from hwlib.model import ModelDB, PortModel, get_variance

def undef_to_one(v):
  return 1.0 if v is None else v

class Shader:
  IGNORE = "ignore"
  ERROR = "error"

  def __init__(self):
    self._min = 0
    vals = list(self.all_values())
    if len(vals) > 0:
      self._max = max(vals)*2
    else:
      self._max = 0

    self._n = 500
    sch = colorlover.scales['9']['seq']['BuPu']
    self._scheme = colorlover.interp(sch,500)

  @staticmethod
  def get_shader(circ,method):
    if method == 'snr':
      return SNRShader(circ)
    if method == 'pctrng':
      return PercentOpRangeShader(circ)
    if method == 'interval':
      return IntervalShader(circ)
    if method == 'bandwidth':
      return BandwidthShader(circ)
    elif method == 'scaled-interval':
      return ScaledIntervalShader(circ)
    elif method == 'scale-factor':
      return ScaleFactorShader(circ)
    elif method is None:
      return GenericShader()
    else:
      raise Exception("unknown shader: <%s>" % method)


  def to_color(self,value):
    if self._max == self._min:
      return "#fffffff"

    pct = (value-self._min)/(self._max-self._min)
    bin_no = max(min(int(pct*self._n),self._n-1),0)

    color = self._scheme[bin_no]
    r,g,b = colorlover.to_numeric(colorlover.to_rgb([color]))[0]
    hexval = "#{0:02x}{1:02x}{2:02x}".format(int(r),int(g),int(b))
    return hexval

  def white(self):
    return "#ffffff"

  def red(self):
    return "#f8585a"

  def get_block_color(self,name,loc):
    value,_ = self.get_block_value(name,loc)
    if value == Shader.IGNORE:
      return self.white()
    elif value == Shader.ERROR:
      return self.red()
    else:
      return self.to_color(value)

  def get_port_color(self,name,loc,port):
    value,_ = self.get_port_value(name,loc,port)
    if value == Shader.IGNORE:
      return self.white()
    elif value == Shader.ERROR:
      return self.red()
    else:
      return self.to_color(value)

  def is_value(self,v):
    return not v == Shader.IGNORE and \
      not v == Shader.ERROR

  def all_values(self):
    raise NotImplementedError

  def get_block_value(self,name,loc):
    return Shader.IGNORE,None

  def get_port_value(self,name,loc,port):
    return Shader.IGNORE,None

class CircShader(Shader):

  def __init__(self,circ,evaluator):
    self.circ = circ
    self.evaluate = evaluator
    Shader.__init__(self)

  def normal_label(self,mean,variance):
    html = '''
    <table border="0">
    <tr><td>mu:{mean:.3e}</td></tr>
    <tr><td>std:{variance:.3e}</td></tr>
    </table>
    '''
    params = {'mean':mean,'variance':variance}
    return html.format(**params)

  def all_values(self):
    for block_name,loc,cfg in self.circ.instances():
      value,_ = self.get_block_value(block_name,loc)
      if self.is_value(value):
        yield value
      block = self.circ.board.block(block_name)
      for port in block.inputs + block.outputs:
        value,_ = self.get_port_value(block_name,loc,port)
        if self.is_value(value):
          yield value

  def get_port_value(self,name,loc,port):
    m,v = self.evaluate.get(name,loc,port)
    if m is None:
      return Shader.ERROR,"skip"
    else:
      return m+v,self.normal_label(m,v)

class GenericShader(Shader):

  def __init__(self):
    Shader.__init__(self)

  def all_values(self):
    yield 0

class CostShader(CircShader):

  def __init__(self,circ):
    CircShader.__init__(self,circ,None)

  def get_port_value(self,name,loc,port):
    cfg = self.circ.config(name,loc)
    cost = cfg.meta(port,'cost')
    if cost is None:
      return Shader.ERROR,"skip"
    else:
      return cost,"%s" % cost


class ScaleFactorShader(CircShader):

  def __init__(self,circ):
    CircShader.__init__(self,circ,None)

  def get_port_value(self,name,loc,port):
    cfg = self.circ.config(name,loc)
    scf = cfg.scf(port)
    if scf is None:
      return Shader.ERROR,"skip"
    else:
      return scf,"%s" % scf


class NoiseEvaluator:

  def __init__(self,circ):
    self._circ = circ
    self._db = ModelDB()
    self._circ = circ.metadata["method"]

  def get(self,block_name,loc,port):
    config = self._circ.config(block_name,loc)
    noise = get_variance(self._db,self._circ, \
                         block_name,loc,port, \
                         handle=None,
                         mode=self._method)
    return True,noise

class SNRShader(CircShader):

  def __init__(self,circ):
    self._db = ModelDB()
    self._method = circ.meta["model"]
    self._circ = circ
    CircShader.__init__(self,circ,None)

  def get_port_value(self,name,loc,port):
    cfg = self.circ.config(name,loc)

    ival = cfg.interval(port)
    scf = cfg.scf(port)
    if ival is None \
       or scf is None  \
       or ival.bound == 0.0:
      return Shader.ERROR,"skip"
    else:
      #print(noise,scf*ival.bound,scf)
      noise = get_variance(self._db,self._circ, \
                           name,loc,port, \
                           handle=None, \
                           mode=self._method)

      if noise == 0:
        return Shader.ERROR,"skip"

      snr = math.log10(scf*ival.bound/noise)
      return snr,"%.3f/%.3f" % (scf*ival.bound,noise)


class PercentOpRangeShader(CircShader):

  def __init__(self,circ):
    CircShader.__init__(self,circ,None)

  def get_port_value(self,name,loc,port):
    cfg = self.circ.config(name,loc)
    blk = self.circ.board.block(name)
    scf = cfg.scf(port)
    ival = cfg.interval(port)
    props = blk.props(cfg.comp_mode, \
                      cfg.scale_mode, \
                      port)

    if ival is None or scf is None or props is None:
      return Shader.ERROR,"skip"

    mathrange = ival.scale(scf)
    oprange = props.interval()
    if mathrange.spread > 0:
      pct = mathrange.spread/oprange.spread
      return pct,"%.3f/%.3f" % (mathrange.spread,oprange.spread)
    else:
      return Shader.ERROR,"ship"

class ScaledIntervalShader(CircShader):

  def __init__(self,circ):
    CircShader.__init__(self,circ,None)

  def get_port_value(self,name,loc,port):
    cfg = self.circ.config(name,loc)
    ival = cfg.interval(port)
    scf = cfg.scf(port)
    if ival is None or scf is None:
      return Shader.ERROR,"skip"
    else:
      return ival.bound*scf,"%s*%.3e" % (ival,scf)


class BandwidthShader(CircShader):

  def __init__(self,circ):
    CircShader.__init__(self,circ,None)

  def get_port_value(self,name,loc,port):
    cfg = self.circ.config(name,loc)
    ival = cfg.bandwidth(port)
    scf = cfg.scf(port)
    if ival is None or scf is None:
      return Shader.ERROR,"skip"
    else:
      return ival.bandwidth, "%s" % ival


class IntervalShader(CircShader):

  def __init__(self,circ):
    CircShader.__init__(self,circ,None)

  def get_port_value(self,name,loc,port):
    cfg = self.circ.config(name,loc)
    ival = cfg.interval(port)
    scf = cfg.scf(port)
    if ival is None or scf is None:
      return Shader.ERROR,"skip"
    else:
      return ival.bound, "%s" % ival

class DotFileCtx:

  def __init__(self,circ,method):
    self._node_stmts = []
    self._conn_stmts = []
    self.circ = circ
    self._id_to_data = {}
    self._blockloc_to_id = {}
    self.shader = Shader.get_shader(circ,method)

  def bind(self,name,loc,config):
    ident = len(self._id_to_data)
    self._id_to_data[ident] = {
      'name': name,
      'loc': loc,
      'config': config
    }
    self._blockloc_to_id[(name,loc)] = ident

  def get_id(self,name,loc):
    return self._blockloc_to_id[(name,loc)]

  def qn(self,stmt,indent=0):
    prefix = "  "*indent if indent > 0 else ""
    self._node_stmts.append(prefix + stmt)

  def qc(self,stmt,indent=0):
    prefix = "  "*indent if indent > 0 else ""
    self._conn_stmts.append(prefix + stmt)

  def program(self):
    stmts = self._node_stmts + self._conn_stmts
    prog = "digraph circuit {\n%s\n}" % ("\n".join(stmts))
    return prog

  def body_handle(self,name,loc):
    blkidx = self.get_id(name,loc)
    return "block%d" % blkidx

  def port_handle(self,name,loc,port):
    blkidx = self.get_id(name,loc)
    blkhandle = self.body_handle(name,loc)
    block = self.circ.board.block(name)
    if port in block.inputs:
        return "%s_inp%d" % (blkhandle, block.inputs.index(port))
    elif port in block.outputs:
        return "%s_out%d" % (blkhandle, block.outputs.index(port))
    else:
        raise Exception("can't find port: %s" % str(port))


def build_environment(circ,color_method=None):
  env = DotFileCtx(circ,method=color_method)
  for block_name,loc,config in circ.instances():
      env.bind(block_name,loc,config)

  return env

def build_port(env,block_name,block_loc,port):
  color = env.shader.get_port_color(block_name,block_loc,port)
  port_handle = env.port_handle(block_name,block_loc,port)
  caption_handle = "%s_caption" % port_handle

  value,label = env.shader.get_port_value(block_name,block_loc,port)
  if not label is None:
    env.qn('%s [' % caption_handle,1)
    env.qn('shape=plaintext',2)
    env.qn('label=<%s>' % (label), 2)
    env.qn(']',1)
    env.qc('%s->%s [style=dashed]' % (caption_handle,port_handle))

  env.qn('%s [' % port_handle,1)
  env.qn('shape=invtriangle',2)
  env.qn('fillcolor=\"%s\"' % color,2)
  env.qn('style=filled',2)
  env.qn("label=<%s>" % (port),2)
  env.qn(']',1)
  return port_handle

def build_body(env,block_name,block_loc,cfg):
  body = '''
    <table border="0">
    <tr><td>{block_name}</td><td>{block_loc}</td></tr>
    <tr>
    <td><font color="#5D6D7E">{scale_mode}</font></td>
    <td><font color="#5D6D7E">{comp_mode}</font></td>
    </tr>
    </table>
    '''

  params = {
      'block_name':block_name,
      'block_loc':block_loc,
      'scale_mode':cfg.scale_mode,
      'comp_mode':cfg.comp_mode
  }
  color = env.shader.get_block_color(block_name,block_loc)
  html = body.format(**params)
  body_handle = env.body_handle(block_name,block_loc)
  env.qn('%s [' % body_handle,1)
  env.qn('shape=record',2)
  env.qn('fillcolor=\"%s\"' % color,2)
  env.qn('style=filled',2)
  env.qn('shape=record',2)
  env.qn('label=<%s>' % html,2)
  env.qn(']',1)
  return body_handle

def build_block(env,block_name,block_loc,cfg):
    blkidx = env.get_id(block_name,block_loc)
    block = env.circ.board.block(block_name)
    env.qn('subgraph cluster%d {' % blkidx)
    env.qn('style=filled')
    env.qn('color=lightgrey')
    env.qn('rank=same')
    body_handle = env.body_handle(block_name,block_loc)
    for inp in block.inputs:
        port_handle = build_port(env,block_name,block_loc,inp)
        env.qc('%s -> %s' %(port_handle,body_handle),1)

    build_body(env,block_name,block_loc,cfg)

    for out in block.outputs:
        port_handle = build_port(env,block_name,block_loc,out)
        env.qc('%s -> %s' %(body_handle,port_handle),1)

    env.qn("}")

def build_scf(env,block,loc,cfg,port):
  body = '''
  <table border="0">
  <tr><td><font color="#5D6D7E">scf:{scf:.3e}</font></td></tr>
  </table>
  '''

  port_handle = env.port_handle(block,loc,port)
  label_handle = "%s_scf" % (port_handle)
  scf = undef_to_one(cfg.scf(port))
  params = {
    'scf':scf
  }
  if cfg.has_expr(port):
    label = body.format(**params)
  else:
    label = body.format(**params)

  env.qn("%s [" % (label_handle))
  env.qn("shape=cds",2)
  env.qn("label=<%s>" % label,2)
  env.qn("]")
  env.qc("%s->%s [penwidth=3.0 color=black]" % (port_handle,label_handle),1)


def build_label(env,block,loc,cfg,port,math_label,kind):
  body = '''
  <table border="0">
  <tr><td>{kind} {label}</td></tr>
  <tr><td><font color="#5D6D7E">scf:{scf:.3e}</font></td></tr>
  <tr><td><font color="#5D6D7E">tau:{tau:.3e}</font></td></tr>
  </table>
  '''

  port_handle = env.port_handle(block,loc,port)
  label_handle = "%s_label" % (port_handle)
  kind = kind.value
  scf = undef_to_one(cfg.scf(port))
  params = {
    'kind':kind,
    'label':math_label,
    'scf':scf,
    'tau':env.circ.tau,
  }
  if cfg.has_expr(port):
    label = body.format(**params)
  else:
    label = body.format(**params)

  env.qn("%s [" % (label_handle))
  env.qn("shape=cds",2)
  env.qn("label=<%s>" % label,2)
  env.qn("]")
  env.qc("%s->%s [penwidth=3.0 color=black]" % (port_handle,label_handle),1)


def build_expr(env,block,loc,cfg,port,expr):
  body = '''
  <table border="0">
  <tr><td><font color="#5D6D7E">expr:{expr}</font></td></tr>
  <tr><td><font color="#5D6D7E">in:{in}</font></td></tr>
  <tr><td><font color="#5D6D7E">out:{out}</font></td></tr>
  </table>
  '''
  port_handle = env.port_handle(block,loc,port)
  value_handle = "%s_value" % (port_handle)

  scf = undef_to_one(cfg.scf(port))
  params = {
    'expr': op.to_python(expr),
    'in':cfg.inject_var('in'),
    'out':cfg.inject_var('out'),
  }
  label = body.format(**params)
  env.qn("%s [" % (value_handle))
  env.qn("shape=cds",2)
  env.qn('label=<%s>' % label,2)
  env.qn("]")
  env.qc("%s->%s [penwidth=3.0 color=red]" % \
         (value_handle,port_handle),1)



def build_value(env,block,loc,cfg,port,value):
    body = '''
    <table border="0">
    <tr><td>val: {value:.3e}</td></tr>
    <tr><td><font color="#5D6D7E">scf:{scf:.3e}</font></td></tr>
    </table>
    '''

    port_handle = env.port_handle(block,loc,port)
    value_handle = "%s_value" % (port_handle)

    scf = undef_to_one(cfg.scf(port))
    params = {
        'value': value, 'scf': scf
    }
    label = body.format(**params)
    env.qn("%s [" % (value_handle))
    env.qn("shape=cds",2)
    env.qn('label=<%s>' % label,2)
    env.qn("]")
    env.qc("%s->%s [penwidth=3.0 color=red]" % (value_handle,port_handle),1)

def write_graph(circ,filename,color_method=None,write_png=False):
    env = build_environment(circ,color_method)
    for block,loc,cfg in circ.instances():
        build_block(env,block,loc,cfg)
        blk = circ.board.block(block)
        for port,math_label,kind in cfg.labels():
            build_label(env,block,loc,cfg,port,math_label,kind)

        for port in blk.outputs:
            build_scf(env,block,loc,cfg,port)

        for port,expr in cfg.exprs(inject=False):
            build_expr(env,block,loc,cfg,port,expr)

        for port,value in cfg.values():
            build_value(env,block,loc,cfg,port,value)

    for sblk,sloc,sport,dblk,dloc,dport in circ.conns():
      src_handle = env.port_handle(sblk,sloc,sport)
      dest_handle = env.port_handle(dblk,dloc,dport)
      env.qc("%s -> %s [penwidth=3.0 color=blue]" % (src_handle,dest_handle),1)

    prog = env.program()
    with open(filename,'w') as fh:
        fh.write(prog)

    if write_png:
        assert(".dot" in filename)
        basename = filename.split(".dot")[0]
        imgname = "%s.png" % basename
        cmd = "dot -Tpng %s -o %s" % (filename,imgname)
        os.system(cmd)
