import argparse
import json
import os
import subprocess
import sys

def read_config(cfgfile):
  defaults = {
    'n-lgraph': 1,
    'n-lscale': 1,
    'max-freq':None,
    'subset': 'extended',
    'ignore-models':"",
    'model': 'delta_maxfit'
  }
  if cfgfile is None:
    return dict(defaults)

  with open(cfgfile,'r') as fh:
    cfg = dict(defaults)
    data = fh.read()
    print(data)
    obj = json.loads(data)
    for k,v in obj.items():
      if not (k in defaults):
        raise Exception("not allowed: %s" % k)
      cfg[k] = v

    return cfg

def execute(args,params,logfile):
  argstr = args.format(**params).split(" ")
  cmd = list(filter(lambda q: q != "", \
                    ['python3', 'legno.py']+ argstr))

  cmdstr = " ".join(cmd)
  print(cmdstr)
  try:
    # stdout = subprocess.PIPE lets you redirect the output
    returncode = os.system(cmdstr)
  except OSError:
    print(cmd)
    print("error: popen")
    sys.exit(-1) # if the subprocess call failed, there's not much point in continuing

  if returncode != 0:
    print("error: exit code is nonzero")
    return False
  else:
    return True



parser = argparse.ArgumentParser(description='Legno experiment runner.')

parser.add_argument('--config',
                    help='configuration file to use')
parser.add_argument('--hwenv',help='hardware environment')
parser.add_argument('--lgraph',action='store_true',
                   help='use lgraph to generate circuits.')
parser.add_argument('prog',
                   help='benchmark to run.')
parser.add_argument("--srcgen",action="store_true", \
                    help="only generate source")
parser.add_argument("--ignore-missing", action="store_true", \
                   help="ignore missing delta models")


args = parser.parse_args()

params = read_config(args.config)
params['prog'] = args.prog
params['hwenv'] = args.hwenv

for k,v in params.items():
  print("%s=%s" % (k,v))

lgraph_args = \
  "--subset {subset} lgraph {prog} --max-circuits {n-lgraph}"
succ = True
if args.lgraph:
  succ = execute(lgraph_args,params,'arco.log')

lscale_args = \
             "--subset {subset} lscale {prog} --model {model}  " + \
             "--scale-circuits {n-lscale} --search "
if not params['max-freq'] is None:
  lscale_args += " --max-freq %f" % params['max-freq']
if args.ignore_missing:
  lscale_args += " --ignore-missing"

if len(params["ignore-models"]) > 0:
  blocks = params["ignore-models"].split(" ")
  for block in blocks:
    lscale_args += " --ignore-model %s" % block

if succ and not args.srcgen:
  succ = execute(lscale_args,params,'lscale.log')

#if succ and not args.srcgen:
#  graph_args = "--subset {subset} {prog} graph"
#  execute(graph_args,params,'graph.log')

srcgen_args = \
              "--subset {subset} srcgen {prog} --recompute --trials 1"

if not args.hwenv is None:
  srcgen_args += " --hwenv {hwenv}"

succ = execute(srcgen_args,params,'srcgen.log')



