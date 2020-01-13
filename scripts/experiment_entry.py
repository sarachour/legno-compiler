from scripts.common import read_only_properties, ExecutionStatus
import os
import logging

logger = logging.getLogger('exptbl')
logger.setLevel(logging.WARN)

@read_only_properties('bmark', 'subset', 'lgraph','lscale', \
                      'objective_fun','model', \
                      'dssim','hwenv', \
                      'grendel_script',\
                      'adp')
class ExperimentEntry:

  def __init__(self,db, \
               status, \
               modif, \
               subset, \
               program, \
               lgraph, \
               lscale, \
               grendel_script,
               adp, \
               model, \
               obj, \
               dssim, \
               hwenv, \
               energy, \
               runtime, \
               bandwidth, \
               quality):

    self.program = program
    self.subset = subset
    self.lgraph= lgraph
    self.lscale= lscale
    self.obj = obj
    self.model = model
    self.dssim = dssim
    self.hwenv = hwenv
    self.grendel_script = grendel_script
    self.adp = adp

    self._status = status
    self._modif = modif
    self._energy= energy
    self._runtime= runtime
    self._bandwidth = bandwidth
    self._quality= quality
    self._db = db

  @property
  def modif(self):
    return self._modif

  @modif.setter
  def modif(self,new_modif):
    assert(isinstance(new_modif,ExecutionStatus))
    self.update_db({'modif':new_status.value})
    self._modif = new_status

  @property
  def bandwidth(self):
    return self._bandwidth

  @bandwidth.setter
  def bandwidth(self,new_bandwidth):
    self.update_db({'bandwidth':new_bandwidth})
    self._bandwidth = new_bandwidth


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
  def energy(self):
    return self._energy

  @energy.setter
  def energy(self,new_energy):
    self.update_db({'energy':new_energy})
    self._energy = new_energy


  @property
  def quality(self):
    return self._quality

  @quality.setter
  def quality(self,new_quality):
    self.update_db({'quality':new_quality})
    self._quality = new_quality



  def outputs(self):
    for outp in self._db.output_tbl.get(self.subset,
                                          self.program, \
                                          self.lgraph, \
                                          self.lscale, \
                                          self.model, \
                                          self.obj, \
                                          self.dssim, \
                                          self.hwenv):
      yield outp

  def synchronize(self):
    # delete if we're missing relevent files
    if not os.path.isfile(self.grendel_script):
      logger.warn("file doesn't exist: <%s>" % self.grendel_script)
      self.delete()
      return
    if not  os.path.isfile(self.adp):
      logger.warn("file doesn't exist: <%s>" % self.adp)
      self.delete()
      return

    clear_computed = False
    not_done = False
    for output in self.outputs():
      if os.path.isfile(output.waveform):
        if output.status == ExecutionStatus.PENDING:
          output.status = ExecutionStatus.RAN
      else:
        if output.status == ExecutionStatus.RAN:
          output.status = ExecutionStatus.PENDING

      not_done = not_done or \
                 (output.status == ExecutionStatus.PENDING)

    if not not_done:
      self.status = ExecutionStatus.RAN
    else:
      self.status = ExecutionStatus.PENDING

  def update_db(self,args):
    self._db.experiment_tbl.update( \
                                    self.subset, \
                                    self.program, \
                                    self.lgraph, \
                                    self.lscale, \
                                    self.model, \
                                    self.obj, \
                                    self.dssim, \
                                    self.hwenv, \
                                    args)

  def set_status(self,new_status):
    assert(isinstance(new_status,ExecutionStatus))
    self.update_db({'status':new_status.value})
    self._status = new_status

  def set_quality(self,new_quality):
    self.update_db({'quality':new_quality})
    self._quality = new_quality

  def set_energy(self,new_energy):
    self.update_db({'energy':new_energy})
    self._energy = new_energy

  def set_runtime(self,new_runtime):
    self.update_db({'runtime':new_runtime})
    self._runtime = new_runtime

  def delete(self):
    for outp in self.get_outputs():
      outp.delete()

    self._db.experiment_tbl.delete(self.subset,
                               self.program,
                               self.lgraph,
                               self.lscale,
                               self.model,
                               self.obj,
                               self.dssim,
                               self.hwenv)

  def get_outputs(self):
    return self._db.output_tbl.get(self.subset,
                                     self.program, \
                                     self.lgraph,
                                     self.lscale,
                                     self.model,
                                     self.obj,
                                     self.dssim, \
                                     self.hwenv)

  @staticmethod
  def from_db_row(db,args):
    entry = ExperimentEntry(
      db=db,
      status=ExecutionStatus(args['status']),
      modif=args['modif'],
      subset=args['subset'],
      program=args['prog'],
      lgraph=args['lgraph'],
      lscale=args['lscale'],
      model=args['model'],
      grendel_script=args['grendel_script'],
      adp=args['adp'],
      obj=args['obj'],
      dssim=args['dssim'],
      hwenv=args['hwenv'],
      energy=args['energy'],
      runtime=args['runtime'],
      bandwidth=args['bandwidth'],
      quality=args['quality'],
    )
    return entry

  @property
  def identifier(self):
    return "%s::%s(%s,%s)" % (self.subset,
                          self.program,
                          self.lgraph,
                          self.lscale)

  '''
  @property
  def ident(self):
    return "%s[%s,%s](%s,%s)" % (self.adp_ident, \
                                 self.obj, \
                                 self.model, \
                                 self.dssim, \
                                 self.hwenv)
  '''

  def __repr__(self):
    s = "{\n"
    s += "prog=%s\n" % (self.program)
    s += "lscale=%s lgraph=%s\n" % (self.lscale,self.lgraph)
    s += "model=%s obj=%s\n" % (self.model,self.obj)
    s += "status=%s\n" % (self.status.value)
    s += "grendel_script=%s\n" % (self.grendel_script)
    s += "adp=%s\n" % (self.adp)
    s += "energy=%s\n" % (self.energy)
    s += "runtime=%s\n" % (self.runtime)
    s += "bandwidth=%s\n" % (self.bandwidth)
    s += "quality=%s\n" % (self.quality)
    s += "}\n"
    return s

