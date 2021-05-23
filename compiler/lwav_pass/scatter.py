from enum import Enum

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np


class ScatterVis:

    def __init__(self,name,title,xlabel,ylabel):
        self.name = name
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = title
        self.points = {}
        self.styles = {}
        self.show_legend = False
        self.x_logscale = False
        self.y_logscale = False
        self.order = None


    @property
    def time_units(self):
        for wf in self.waveforms.values():
            return wf.time_units
        return None

    @property
    def num_series(self):
        return len(self.points.keys())

    @property
    def empty(self):
        return self.num_series== 0

    def add_series(self,name,xs,ys):
        assert(len(xs) == len(ys))
        self.points[name] = (xs,ys)


    def set_style(self,name,color,pointstyle,size=100,opacity=1.0):
        self.styles[name] = (color,pointstyle,size,opacity)


    def plot(self,filepath):
        palette = sns.color_palette()
        ax = plt.subplot(1, 1, 1)
        title = self.title
        ax.tick_params(labelsize=24);
        ax.set_xlabel(self.xlabel,fontsize=28)
        ax.set_ylabel(self.ylabel,fontsize=28)
        ax.set_title(title,fontsize=32)
        ax.grid(False)

        if not self.order is None:
            assert(all(map(lambda k: k in self.order, self.points.keys())))
            series = self.order
        else:
            series = self.points.keys()

        for name in series:
            xs,ys = self.points[name]
            if not name in self.styles:
                ax.scatter(xs,ys,label=name,
                           marker='x',
                           s=100)
            else:
                color,pointstyle,size,opacity = self.styles[name]
                ax.scatter(xs,ys,label=name,
                           marker=pointstyle, \
                           s=size,\
                           color=color, \
                           alpha=opacity)

        if self.x_logscale:
            plt.xscale("log")
        if self.y_logscale:
            plt.yscale("log")

        #ax.set_ylim(ymin=ymin*1.1,ymax=ymax*1.1)
        #ax.set_xlim(xmin=xmin*1.1,xmax=xmax*1.1)
        if self.show_legend:
            ax.legend()

        plt.tight_layout()
        plt.savefig(filepath)
        plt.clf()

