import matplotlib.pyplot as plt
import json
import numpy as np

def waveform(entry,path_h,trial,tag,t,x):
  filename = path_h.plot(entry.program,
                         entry.lgraph,
                         entry.lscale,
                         entry.model,
                         entry.obj,
                         entry.dssim,
                         entry.hwenv,
                         '%s-%d-%s' % (entry.variable,trial,tag))
  filename = filename.split(".png")[0] + ".txt"
  with open(filename,'w') as fh:
    fh.write(json.dumps({ \
                          't':list(t), \
                          'x':list(np.real(x)) \
    }))

def compare_plot(entry,path_h,trial,tag,tpred,xpred,tobs,xobs):
  plt.plot(tobs,xobs,label="obs")
  plt.plot(tpred,xpred,label="pred")
  bot,top = plt.ylim()
  plt.ylim(min(bot,0),top)
  plt.legend()
  filename = path_h.plot(entry.lgraph,
                         entry.lscale,
                         entry.model,
                         entry.obj,
                         entry.dssim,
                         entry.hwenv,
                         '%s-%d-%s' % (entry.variable,trial,tag))
  print(filename)
  plt.savefig(filename)
  plt.clf()


def simple_plot(entry,path_h,trial,tag,t,x):
  plt.plot(t,x,label=tag)
  bot,top = plt.ylim()
  plt.ylim(min(bot,0),top)
  plt.legend()
  filename = path_h.plot(entry.lgraph,
                         entry.lscale,
                         entry.model,
                         entry.obj,
                         entry.dssim,
                         entry.hwenv,
                         '%s-%d-%s' % (entry.variable,trial,tag))
  print(filename)
  plt.savefig(filename)
  plt.clf()


def mean_std_plot(entry,path_h,trial,tag,t,mean,std):
  UPPER = list(map(lambda a: a[0]+a[1],zip(mean,std)))
  LOWER = list(map(lambda a: a[0]-a[1],zip(mean,std)))
  plt.plot(t,UPPER,label='+std',color='red')
  plt.plot(t,LOWER,label='-std',color='red')
  plt.plot(t,mean,label='mean',color='black')
  plt.legend()
  filename = path_h.plot(entry.program,
                         entry.lgraph,
                         entry.lscale,
                         entry.model,
                         entry.obj,
                         entry.dssim,
                         entry.hwenv,
                         '%s-%d-%s' % (entry.variable,trial,tag))
  plt.savefig(filename)
  plt.clf()


