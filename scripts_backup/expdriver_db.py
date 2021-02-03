import util.config as CONFIG
import sqlite3
from scripts.experiment_table import ExperimentTable
from scripts.output_table import OutputTable
from scripts.common import get_output_files
import util.paths as paths
import os

class ExpDriverDB:


  def __init__(self):
    self.path = CONFIG.EXPERIMENT_DB
    self.open()
    self.experiment_tbl = ExperimentTable(self)
    self.output_tbl = OutputTable(self)

  def open(self):
    self.conn = sqlite3.connect(self.path)
    self.curs = self.conn.cursor()


  def close(self):
    self.conn.close()


  def add(self,path_handler,subset,prog, \
          lgraph, \
          lscale, \
          model, \
          obj, \
          dssim,hwenv):
    entry = self.experiment_tbl.add(path_handler, \
                                    subset=subset, \
                                    prog=prog, \
                                    lgraph=lgraph, \
                                    lscale=lscale, \
                                    model=model, \
                                    obj=obj, \
                                    dssim=dssim, \
                                    hwenv=hwenv)

    for out_file in get_output_files(entry.grendel_script):
      fargs = path_handler \
              .measured_waveform_file_to_args(out_file)
      self.output_tbl.add(path_handler, \
                          subset=subset, \
                          prog=prog, \
                          lgraph=lgraph, \
                          lscale=lscale, \
                          model=model, \
                          obj=obj, \
                          dssim=dssim, \
                          hwenv=hwenv, \
                          variable=fargs['var'], \
                          trial=fargs['trial'])

    entry.synchronize()
    return entry

  def scan(self):
    for dirname, subdirlist, filelist in os.walk(CONFIG.LEGNO_PATH):
      for fname in filelist:
        if fname.endswith('.grendel'):
          fargs = paths.PathHandler.path_to_args(dirname)
          ph = paths.PathHandler(subset=fargs['subset'], \
                                 prog=fargs['prog'], \
                                 make_dirs=False)
          gargs = \
                ph.grendel_file_to_args(fname)
          if self.experiment_tbl.has(  \
                                       subset=fargs['subset'], \
                                       prog=fargs['prog'], \
                                       lgraph=gargs['lgraph'], \
                                       lscale=gargs['lscale'], \
                                       model=gargs['model'], \
                                       obj=gargs['opt'], \
                                       dssim=gargs['dssim'], \
                                       hwenv=gargs['hwenv']):
            continue

          exp = self.add(ph, \
                         subset=fargs['subset'], \
                         prog=fargs['prog'], \
                         lgraph=gargs['lgraph'], \
                         lscale=gargs['lscale'], \
                         model=gargs['model'], \
                         obj=gargs['opt'], \
                         dssim=gargs['dssim'], \
                         hwenv=gargs['hwenv'])
          if not exp is None:
            yield exp
