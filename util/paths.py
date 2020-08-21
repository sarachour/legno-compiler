import os
from enum import Enum
import util.config as config
import util.util as util
import parse as parselib

class PathHandler:
    def __init__(self,subset,prog,make_dirs=True):
        self.set_root_dir(subset,prog)
        for path in [
                self.ROOT_DIR,
                self.PROG_DIR,
                self.LGRAPH_ADP_DIR,
                self.LGRAPH_ADP_DIAG_DIR,
                self.LSCALE_ADP_DIR,
                self.LSCALE_ADP_DIAG_DIR,
                self.MEAS_WAVEFORM_FILE_DIR,
                self.GRENDEL_FILE_DIR,
                self.REF_SIM_DIR,
                self.ADP_SIM_DIR,
                self.PLOT_DIR,
                self.TIME_DIR
        ]:
          if make_dirs:
              util.mkdir_if_dne(path)

        self._subset = subset
        self._prog = prog

    @property
    def subset(self):
        return self._subset

    @staticmethod
    def path_to_args(dirname):
        paths =[ "%s/legno/{subset:w}/{prog:w}" \
                % config.OUTPUT_PATH, \
                 "%s/legno/{subset:w}/{prog:w}/{dir:w}" \
                % config.OUTPUT_PATH \
        ]
        for path in paths:
            args = parselib.parse(path,dirname)
            if not args is None:
                return dict(args.named.items())

        raise Exception("cannot parse path: %s" % dirname)

    def set_root_dir(self,name,bmark):
        self.ROOT_DIR = "%s/legno/%s" % (config.OUTPUT_PATH,name)
        self.PROG_DIR = self.ROOT_DIR + ("/%s" % bmark)
        self.LGRAPH_ADP_DIR = self.PROG_DIR + "/lgraph-adp"
        self.LGRAPH_ADP_DIAG_DIR = self.PROG_DIR + "/lgraph-diag"
        self.LSCALE_ADP_DIR = self.PROG_DIR + "/lscale-adp"
        self.LSCALE_ADP_DIAG_DIR = self.PROG_DIR + "/lscale-diag"
        self.GRENDEL_FILE_DIR = self.PROG_DIR + "/grendel"
        self.PLOT_DIR = self.PROG_DIR + "/plots"
        self.MEAS_WAVEFORM_FILE_DIR = self.PROG_DIR + "/out-waveform"
        self.TIME_DIR = self.PROG_DIR + "/times"
        self.REF_SIM_DIR = self.PROG_DIR + "/sim/ref"
        self.ADP_SIM_DIR = self.PROG_DIR + "/sim/adp"


    def adp_sim_plot(self,lgraph,lscale,opt,model,varname):
        dirpath = "{path}/{lgraph}_{lscale}_{opt}_{model}"
        cdir = dirpath.format(path=self.ADP_SIM_DIR, \
                              lgraph=lgraph, \
                              lscale=lscale, \
                              opt=opt, \
                              model=model)
        util.mkdir_if_dne(cdir)
        filename = "{dirpath}/{name}.png"
        cfilename = filename.format(dirpath=cdir, \
                                name=varname)
        return cfilename

    def ref_sim_plot(self,varname):
        path = "{path}/{name}.png"
        return path.format(path=self.REF_SIM_DIR, \
                           name=varname)


    def time_file(self,name):
        path = "{path}/{name}.txt"
        return path.format(path=self.TIME_DIR, \
                           name=name)



    def lgraph_adp_diagram_file(self,graph_index):
        path = "{path}/{prog}_g{lgraph}.gv"
        return path.format(path=self.LGRAPH_ADP_DIAG_DIR,
                           prog=self._prog,
                           lgraph=graph_index)


    def lgraph_adp_file(self,graph_index):
        path = "{path}/{prog}_g{lgraph}.adp"
        return path.format(path=self.LGRAPH_ADP_DIR,
                           prog=self._prog,
                           lgraph=graph_index)

    @staticmethod
    def lgraph_adp_to_args(path):
        name = path.split("/")[-1]
        cmd = "{prog:w}_g{lgraph:w}.adp"
        result = parselib.parse(cmd,name)
        assert(not result is None)
        return result

    def lscale_adp_diagram_file(self,graph_index,scale_index,model,opt):
        path ="{path}/{prog}_g{lgraph}_s{lscale}_{model}_{opt}.gv"
        filepath = path.format(path=self.LSCALE_ADP_DIAG_DIR, \
                               prog=self._prog, \
                               lgraph=graph_index, \
                               lscale=scale_index, \
                               model=model, \
                               opt=opt)

 
    def lscale_adp_file(self,graph_index,scale_index,model,opt):
        path ="{path}/{prog}_g{lgraph}_s{lscale}_{model}_{opt}.adp"
        filepath = path.format(path=self.LSCALE_ADP_DIR, \
                               prog=self._prog, \
                               lgraph=graph_index, \
                               lscale=scale_index, \
                               model=model, \
                               opt=opt)

        return filepath

    @staticmethod
    def lscale_adp_to_args(path):
        name = path.split("/")[-1]
        for model_cmd in util.model_format():
            cmd = "{prog:w}_g{lgraph:w}_s{lscale:d}_%s_{opt:w}.adp"  \
                  % model_cmd
            result = parselib.parse(cmd,name)
            if not result is None:
                result = dict(result.named.items())
                result['model']= util.pack_parsed_model(result)
                assert(not result is None)
                return result

        raise Exception("could not parse: %s" % name)

    def lscale_adp_diagram_file(self,graph_index,scale_index,model,opt,tag="notag"):
        path = "{path}/{prog}_g{lgraph}_s{lscale}_{model}_{opt}_{tag}.dot"
        return path.format(path=self.LSCALE_ADP_DIAG_DIR,
                           prog=self._prog, \
                           lgraph=graph_index, \
                           lscale=scale_index, \
                           model=model, \
                           opt=opt,
                           tag=tag)



    def plot(self,graph_index,scale_index,model,opt, \
             menv_subset,henv_subset,tag):
        path = "{path}/{prog}_g{lgraph}_s{lscale}_{model}_{opt}_{dssim}_{hwenv}_{tag}.png"
        return path.format(path=self.PLOT_DIR,
                           prog=self._prog,
                           lgraph=graph_index,
                           lscale=scale_index,
                           model=model,
                           opt=opt,
                           dssim=menv_subset,
                           hwenv=henv_subset, \
                           tag=tag)



    def grendel_file(self,graph_index,scale_index,model,opt, \
                     menv_subset,henv_subset):
        path = "{path}/{prog}_g{lgraph}_s{lscale}_{model}_{opt}_{dssim}_{hwenv}.grendel"
        return path.format(path=self.GRENDEL_FILE_DIR,
                           prog=self._prog,
                           lgraph=graph_index,
                           lscale=scale_index,
                           model=model,
                           opt=opt,
                           dssim=menv_subset,
                           hwenv=henv_subset)


    @staticmethod
    def grendel_file_to_args(path):
        name = path.split("/")[-1]
        for model_cmd in util.model_format():
            cmd = "{prog:w}_g{lgraph:w}_s{lscale:d}_%s_{opt:w}_{dssim:w}_{hwenv:w}.grendel" % \
                   model_cmd
            result = parselib.parse(cmd,name)
            if not result is None:
                result = dict(result.named.items())
                result['model'] = util.pack_parsed_model(result)
                assert(not result is None)
                return result

        raise Exception("could not parse: %s" % name)


    def measured_waveform_file(self,graph_index,scale_index, \
                               model,opt,\
                               dssim, \
                               hwenv, \
                               variable,trial):
        path = "{path}/{prog}_g{lgraph}_s{lscale}_{model}_{opt}"
        path += "_{dssim}_{hwenv}_{var}_{trial}.json"

        return path.format(path=self.MEAS_WAVEFORM_FILE_DIR,
                           prog=self._prog,
                           lgraph=graph_index,
                           lscale=scale_index,
                           model=model,
                           opt=opt,
                           dssim=dssim,
                           hwenv=hwenv,
                           var=variable,
                           trial=trial)



    def measured_waveform_file_to_args(self,path):
        name = path.split("/")[-1]
        for model_cmd in util.model_format():
            cmd = "{prog:w}_g{lgraph:w}_s{lscale:d}_%s_{opt:w}" % model_cmd
            cmd += "_{dssim:w}_{hwenv:w}_{var:w}_{trial:d}.json"
            result = parselib.parse(cmd,name)
            if not result is None:
                result = dict(result.named.items())
                result['model'] = util.pack_parsed_model(result)
                assert(not result is None)
                return result

        raise Exception("could not parse: %s" % name)



    def measured_waveform_dir(self):
      return self.MEAS_WAVEFORM_FILE_DIR

    def grendel_file_dir(self):
        return self.GRENDEL_FILE_DIR


    def lscale_adp_dir(self):
        return self.LSCALE_ADP_DIR


    def lgraph_adp_dir(self):
        return self.LGRAPH_ADP_DIR

    def has_file(self,filepath):
        if not os.path.exists(filepath):
          return False

        directory,filename = os.path.split(filepath)
        return filename in os.listdir(directory)
