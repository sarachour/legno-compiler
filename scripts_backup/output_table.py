import scripts.common as common
import datetime
from scripts.output_entry import OutputEntry

class OutputTable:

  def __init__(self,db):
    self.db = db
    cmd = '''CREATE TABLE IF NOT EXISTS outputs(
    subset text NOT NULL,
    prog text NULL,
    status text NOT NULL,
    lgraph text NOT NULL,
    lscale int NOT NULL,
    model text NOT NULL,
    obj text NOT NULL,
    dssim text NOT NULL,
    hwenv text NOT NULL,
    variable text NOT NULL,
    trial int NOT NULL,
    waveform text,
    runtime real,
    quality real,
    transform text,
    modif timestamp,
    PRIMARY KEY (subset,prog,lgraph,lscale,
                 model,obj,dssim,hwenv,variable,trial)
    FOREIGN KEY (subset,prog,lgraph,lscale,
                 model,obj,dssim,hwenv)
    REFERENCES experiments(subset,prog,lgraph,lscale,
                           model,obj,dssim,hwenv)
    )
    '''
    self._order = ['subset',
                   'prog','status', \
                   'lgraph','lscale', \
                   'model','opt', \
                   'dssim','hwenv',
                   'varname','trial','waveform', \
                   'runtime','quality','transform','modif']

    self._modifiable = ['runtime','quality','modif', \
                        'status','transform']
    self.db.curs.execute(cmd)
    self.db.conn.commit()


  def to_where_clause(self,subset,prog, \
                      lgraph,lscale,model,obj, \
                      dssim,hwenv, \
                      variable,trial):
    cmd = '''WHERE
      subset = "{subset}"
      AND prog = "{prog}"
      AND lgraph = "{lgraph}"
      AND lscale = {lscale}
      AND model = "{model}"
      AND obj = "{obj}"
      AND dssim = "{dssim}"
      AND hwenv = "{hwenv}"
      '''
    if not variable is None and not trial is None:
      cmd += '''
      AND variable = "{variable}"
      AND trial = {trial}
      '''

    args = common.make_args(subset,prog, \
                            lgraph,lscale, \
                            model,obj, \
                            dssim,hwenv)
    args['variable'] = variable
    args['trial'] = trial
    conc_cmd = cmd.format(**args)
    return conc_cmd

  def _get_rows(self,where_clause):
    cmd = '''SELECT * FROM outputs {where_clause}'''
    conc_cmd = cmd.format(where_clause=where_clause)
    for values in list(self.db.curs.execute(conc_cmd)):
      assert(len(values) == len(self._order))
      args = dict(zip(self._order,values))
      yield OutputEntry.from_db_row(self.db,args)


  def update(self,subset,bmark,arco_inds,jaunt_inds,model,opt, \
                    menv_name,hwenv_name,varname,trial,new_fields):
    cmd = '''
    UPDATE outputs
    SET {assign_clause} {where_clause};
    '''
    where_clause = self.to_where_clause(subset,
                                        bmark,\
                                        arco_inds,jaunt_inds,
                                        model,
                                        opt, \
                                        menv_name,hwenv_name,
                                        variable=varname,
                                        trial=trial)
    new_fields['modif'] = datetime.datetime.now()
    assign_subclauses = []
    for field,value in new_fields.items():
      assert(field in self._modifiable)
      if field == 'modif' or field == 'status' or field == 'transform':
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

  def get(self,subset,prog,lgraph,lscale,model,opt,dssim,hwenv):
    cmd = '''
     SELECT *
     FROM outputs
     {where_clause};
    '''
    where_clause = self.to_where_clause(subset,prog,\
                                        lgraph,lscale,
                                        model,opt, \
                                        dssim, \
                                        hwenv,
                                        variable=None,
                                        trial=None)
    for entry in self._get_rows(where_clause):
      yield entry

  def delete(self,subset,prog,lgraph,lscale, \
             model,opt,dssim,hwenv, \
             variable,trial):
    cmd = '''
    DELETE FROM outputs {where_clause};
    '''
    where_clause = self.to_where_clause(subset,prog,\
                                        lgraph,lscale,
                                        model, \
                                        opt, \
                                        dssim,hwenv, \
                                        variable=variable, \
                                        trial=trial)
    conc_cmd = cmd.format(where_clause=where_clause)
    self.db.curs.execute(conc_cmd)
    self.db.conn.commit()


  def add(self,path_handler, \
          subset,prog, \
          lgraph, lscale, \
          model, obj,\
          dssim,hwenv, \
          variable,trial):
    cmd = '''
      INSERT INTO outputs (
         subset,prog,lgraph,lscale,
         model,obj,dssim,hwenv,
         waveform,status,modif,
         variable,trial
      ) VALUES
      (
         "{subset}",
         "{prog}","{lgraph}",{lscale},
         "{model}","{obj}",
         "{dssim}","{hwenv}",
         "{waveform}",
         "{status}",
         "{modif}",
         "{variable}",
         {trial}
      )
      '''
    args = common.make_args(subset,prog, \
                            lgraph,lscale, \
                            model,obj, \
                            dssim,hwenv)
    args['modif'] = datetime.datetime.now()
    args['status'] = common.ExecutionStatus.PENDING.value
    args['variable'] = variable
    args['trial'] = trial
    args['waveform'] = path_handler.measured_waveform_file(lgraph, \
                                                           lscale, \
                                                           model, \
                                                           obj, \
                                                           dssim, \
                                                           hwenv, \
                                                           variable, \
                                                           trial)
    conc_cmd = cmd.format(**args)
    self.db.curs.execute(conc_cmd)
    if self.db.curs.rowcount == 0:
      raise Exception("Query Failed:\n%s" % conc_cmd)

    self.db.conn.commit()

