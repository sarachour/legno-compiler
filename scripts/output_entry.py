from scripts.common import read_only_properties, ExecutionStatus
import json
import util.util as util

class OutputTransform:

  def __init__(self,varname):
    self.variable = varname
    self.handle = None
    self.time_constant = 1.0
    self.legno_time_scale = 1.0
    self.legno_ampl_scale = 1.0
    self.expd_time_scale = 1.0
    self.expd_time_offset = 0.0

  @property
  def bandwidth(self):
    return (self.time_constant*self.legno_time_scale);

  def to_json(self):
    return self.__dict__

  @staticmethod
  def from_json(varname,obj):
    xform = OutputTransform(varname)
    if not obj is None:
      xform.__dict__ = obj
    return xform

  def __repr__(self):
    s = "{\n"
    for k,v in self.__dict__.items():
      s += " %s=%s\n" % (k,v)
    s += "}"
    return s

@read_only_properties('subset','prog','lgraph','lscale', \
                      'objective_fun', 'model', 'dssim', \
                      'hwenv', 'waveform',  \
                      'trial','varname')
class OutputEntry:

  def __init__(self,db,status,modif,subset,
               prog,
               lgraph,
               lscale,
               model,
               objective_fun, \
               dssim,hwenv,
               variable,
               waveform,
               trial,transform,quality,runtime):
    self._db = db
    self.subset = subset
    self.program = prog
    self.lgraph = lgraph
    self.lscale = lscale
    self.obj = objective_fun
    self.model = model
    self.dssim = dssim
    self.hwenv = hwenv
    self.variable = variable
    self.trial = trial
    self.waveform = waveform

    self._modif =modif
    self._status = status
    self._quality =quality
    self._transform = transform
    self._runtime =runtime

  @staticmethod
  def from_db_row(db,args):
    if not args['transform'] is  None:
      args['transform'] = OutputTransform.from_json(args['varname'], \
                                          util \
                                          .decompress_json(args['transform']))
    entry = OutputEntry(
      db=db,
      status=ExecutionStatus(args['status']),
      modif=args['modif'],
      subset=args['subset'],
      prog=args['prog'],
      lgraph=args['lgraph'],
      lscale=args['lscale'],
      model=args['model'],
      objective_fun=args['opt'],
      dssim=args['dssim'],
      hwenv=args['hwenv'],
      waveform=args['waveform'],
      variable=args['varname'],
      trial=args['trial'],
      quality=args['quality'],
      runtime=args['runtime'],
      transform=args['transform']
    )
    return entry

  @property
  def modif(self):
    return self._modif

  @modif.setter
  def modif(self,new_modif):
    assert(isinstance(new_modif,ExecutionStatus))
    self.update_db({'modif':new_status.value})
    self._modif = new_status

  @property
  def status(self):
    return self._status

  @status.setter
  def status(self,new_status):
    assert(isinstance(new_status,ExecutionStatus))
    self.update_db({'status':new_status.value})
    self._status = new_status

  @property
  def runtime(self):
    return self._runtime

  @runtime.setter
  def runtime(self,new_runtime):
    assert(new_runtime >= 0)
    self.update_db({'runtime':new_runtime})
    self._runtime = new_runtime

  @property
  def quality(self):
    return self._quality

  @quality.setter
  def quality(self,new_quality):
    self.update_db({'quality':new_quality})
    self._quality = new_quality

  @property
  def transform(self):
    if self._transform is None:
      obj = None
    else:
      obj = self._transform.__dict__

    xform = OutputTransform \
            .from_json(self.variable, \
                       obj)
    return xform

  @transform.setter
  def transform(self,new_xform):
    assert(isinstance(new_xform,OutputTransform))
    self.update_db({'transform':util.compress_json(new_xform.to_json())})
    self._transform = new_xform


  def delete(self):
     self._db.output_tbl.delete(self.subset, \
                                self.program, \
                                self.lgraph, \
                                self.lscale, \
                                self.model, \
                                self.obj, \
                                self.dssim, \
                                self.hwenv, \
                                self.variable, \
                                self.trial)

  def update_db(self,args):
    self._db.output_tbl.update(self.subset, \
                               self.program, \
                               self.lgraph, \
                               self.lscale, \
                               self.model, \
                               self.obj, \
                               self.dssim, \
                               self.hwenv, \
                               self.variable, \
                               self.trial, \
                               args)




  def __repr__(self):
    s = "{\n"
    s += "prog=%s\n" % (self.program)
    s += "lscale=%s lgraph=%s\n" % (self.lscale,self.lgraph)
    s += "model=%s obj=%s\n" % (self.model,self.obj)
    s += "status=%s\n" % (self.status.value)
    s += "variable=%s\n" % (self.variable)
    s += "trial=%d\n" % (self.trial)
    s += "waveform=%s\n" % (self.waveform)
    s += "quality=%s\n" % self.quality
    s += "transform=%s\n" % self.transform
    s += "runtime=%s\n" % self.runtime
    s += "}\n"
    return s

