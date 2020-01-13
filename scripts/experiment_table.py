import scripts.common as common
import datetime
from scripts.experiment_entry import ExperimentEntry

class ExperimentTable:


  def __init__(self,db):
    self.db = db
    cmd = '''CREATE TABLE IF NOT EXISTS experiments
             (subset text NOT NULL,
              prog text NOT NULL,
              status text NOT NULL,
              modif timestamp,
              lgraph text NOT NULL,
              lscale int NOT NULL,
              model text NOT NULL,
              obj text NOT NULL,
              dssim text NOT NULL,
              hwenv text NOT NULL,
              grendel_script text,
              adp text,
              quality real,
              energy real,
              runtime real,
              bandwidth real,
              PRIMARY KEY (subset,prog,lgraph,lscale,
                           model,obj,dssim,hwenv)
             );
    '''
    self._order = ['subset',
                   'prog','status','modif', \
                   'lgraph', \
                   'lscale',
                   'model','obj','dssim','hwenv',
                   'grendel_script', \
                   'adp',
                   'quality', \
                   'energy', \
                   'runtime', \
                   'bandwidth']

    self._modifiable =  \
                        ['status','modif','quality', \
                         'energy','runtime','bandwidth']
    self.db.curs.execute(cmd)

  def _get_rows(self,where_clause):
    cmd = '''SELECT * FROM experiments {where_clause};'''
    conc_cmd = cmd.format(where_clause=where_clause)
    for values in list(self.db.curs.execute(conc_cmd)):
      assert(len(values) == len(self._order))
      args = dict(zip(self._order,values))
      yield ExperimentEntry.from_db_row(self.db,args)

  def get(self,subset,prog,lgraph,lscale,model,obj,dssim,hwenv):
    cmd = '''
    SELECT * WHERE subset="subset"
    AND prog="prog"
    AND lgraph="lgraph"
    AND lscale=lscale
    AND model="model"
    AND obj="objective"
    AND dssim="dssim"
    AND hwenv="hwenv"
    '''
    conc_cmd = cmd.format(subset=subset,
               prog=prog,
               lgraph=lgraph,
               lscale=lscale,
               model=model,
               obj=obj,
               dssim=dssim,
               hwenv=hwenv
    )
    for values in list(self.db.curs.execute(conc_cmd)):
      assert(len(values) == len(self._order))
      args = dict(zip(self._order,values))
      return ExperimentEntry.from_db_row(self.db,args)

    return None

  def has(self,subset,prog,lgraph,lscale,model,obj,dssim,hwenv):
    result = self.get(subset,prog,lgraph,lscale,model,obj,dssim,hwenv)
    return not (result is None)


  def get_all(self):
    for entry in self._get_rows(""):
      yield entry


  def get_by_status(self,status):
    assert(isinstance(status,common.ExecutionStatus))
    where_clause = "WHERE status=\"%s\"" % status.value
    for entry in self._get_rows(where_clause):
      yield entry

  def get_by_bmark(self,bmark):
    where_clause = "WHERE bmark=\"%s\"" % bmark
    for entry in self._get_rows(where_clause):
      yield entry

  def to_where_clause(self,subset,prog,lgraph,lscale, \
                      model,obj, \
                      dssim,hwenv):
    cmd = '''WHERE
      subset = "{subset}"
      AND prog = "{prog}"
      AND lgraph = "{lgraph}"
      AND lscale = {lscale}
      AND model = "{model}"
      AND obj= "{obj}"
      AND dssim = "{dssim}"
      AND hwenv = "{hwenv}"
      '''
    args = common.make_args(subset,prog, \
                            lgraph, \
                            lscale,model,obj, \
                            dssim, \
                            hwenv)

    conc_cmd = cmd.format(**args)
    return conc_cmd

  def filter(self,filt):
    for entry in self.get_all():
      args = entry.columns
      skip = False
      for k,v in args.items():
        if k in filt and v != filt[k]:
          skip = True
      if skip:
        continue
      yield entry



  def delete(self,prog=None,objfun=None):
    assert(not prog is None or not objfun is None)
    if not prog is None and not objfun is None:
      itertr= self.filter({'prog':prog,'opt':objfun})
    elif not objfun is None:
      itertr= self.filter({'opt':objfun})
    elif not prog is None:
      itertr= self.filter({'prog':prog})
    else:
      raise Exception("???")

    for entry in itertr:
      entry.delete()
      yield entry



  def get(self,subset,prog,lgraph,lscale,model,opt,dssim,hwenv):
    where_clause = self.to_where_clause(subset, \
                                        prog=prog ,\
                                        lgraph=lgraph, \
                                        lscale=lscale, \
                                        model=model, \
                                        obj=opt, \
                                        dssim=dssim, \
                                        hwenv=hwenv)
    result = list(self._get_rows(where_clause))
    if len(result) == 0:
      return None
    elif len(result) == 1:
      return result[0]
    else:
      raise Exception("nonunique experiment")

  def delete(self,subset,prog,lgraph,lscale, \
                        model,opt,dssim,hwenv):
    cmd = '''
    DELETE FROM experiments {where_clause};
    '''
    where_clause = self.to_where_clause(subset,prog,\
                                        lgraph,lscale,
                                        model,opt, \
                                        dssim,hwenv)
    conc_cmd = cmd.format(where_clause=where_clause)
    self.db.curs.execute(conc_cmd)
    self.db.conn.commit()



  def add(self,path_handler,
          subset,prog,lgraph, \
          lscale, \
          model,obj, \
          dssim,hwenv):
    entry = self.get(subset, \
                     prog,lgraph,lscale, \
                     model,obj,dssim,hwenv)
    if entry is None:
      cmd = '''
      INSERT INTO experiments (
         subset,prog,lgraph,lscale,
         model,obj,dssim,hwenv,
         adp,grendel_script,
         status,modif
      ) VALUES
      (
         "{subset}","{prog}","{lgraph}",{lscale},
         "{model}","{obj}","{dssim}","{hwenv}",
         "{adp}",
         "{grendel_script}",
         "{status}",
         "{modif}"
      );
      '''
      args = common.make_args(subset,
                              prog,lgraph,lscale, \
                              model,obj, \
                              dssim,hwenv)
      args['modif'] = datetime.datetime.now()
      args['status'] = common.ExecutionStatus.PENDING.value
      args['grendel_script'] = path_handler.grendel_file(lgraph, \
                                                         lscale,
                                                         model,
                                                         obj,
                                                         dssim,
                                                         hwenv)
      args['adp'] = path_handler.lscale_adp_file(lgraph, \
                                                 lscale, \
                                                 model, \
                                                 obj)

      conc_cmd = cmd.format(**args)
      self.db.curs.execute(conc_cmd)
      if self.db.curs.rowcount == 0:
        raise Exception("Query Failed:\n%s" % conc_cmd)
      self.db.conn.commit()
      entry = self.get(subset,prog,lgraph,lscale, \
                       model,obj,dssim,hwenv)
      assert(not entry is None)
    return entry



  def update(self,subset,prog,lgraph,lscale,model, \
             obj,dssim,hwenv,new_fields):
    cmd = '''
    UPDATE experiments
    SET {assign_clause} {where_clause};
    '''
    where_clause = self.to_where_clause(subset,prog,\
                                        lgraph,lscale,model,obj, \
                                        dssim,hwenv)
    new_fields['modif'] = datetime.datetime.now()
    assign_subclauses = []
    for field,value in new_fields.items():
      assert(field in self._modifiable)
      if field == 'modif' or field == 'status':
        subcmd = "%s=\"%s\"" % (field,value)
      else:
        subcmd = "%s=%s" % (field,value)
      assign_subclauses.append(subcmd)

    assign_clause = ",".join(assign_subclauses)
    conc_cmd = cmd.format(where_clause=where_clause, \
                          assign_clause=assign_clause)
    self.db.curs.execute(conc_cmd)
    if self.db.curs.rowcount == 0:
      raise Exception("Query Failed:\n%s" % conc_cmd)

    self.db.conn.commit()

