from enum import Enum

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np



class BoxAndWhiskerVis:

    def __init__(self,name,xaxis,yaxis,title):
        self.name = name
        self.title = title
        self.xlabel = xaxis
        self.ylabel = yaxis
        self.bounds = None
        self.data= {}
        self.styles = {}
        self.points = {}
        self.draw_minimum = False
        self.draw_maximum = False
        self.show_outliers = True
        self.show_labels = True
        self.log_scale = False

    @property
    def time_units(self):
        for wf in self.waveforms.values():
            return wf.time_units
        return None

    def set_bounds(self,minval,maxval):
        self.bounds = (minval,maxval)

    @property
    def num_series(self):
        return len(self.data.keys())

    @property
    def empty(self):
        return self.num_waveforms == 0

    def add_data(self,name,datum):
        if len(datum) == 0:
            raise Exception("cannot add empty dataset")

        self.data[name] = datum

    def add_point(self,label,point):
        self.points[label] = point

    def set_style(self,name,color,opacity=1.0):
        self.styles[name] = (color,opacity)


    def plot(self,filepath):
        dataset = []
        labels = list(self.data.keys())
        all_values = []
        for label in labels:
            dataset.append(self.data[label])
            all_values += self.data[label]

        min_line = min(all_values)
        max_line = max(all_values)

        plt.close("all")
        palette = sns.color_palette()
        ax = plt.subplot(1, 1, 1)
        title = self.title
        ax.tick_params(labelsize=24);
        ax.set_xlabel(self.xlabel,fontsize=28)
        ax.set_ylabel(self.ylabel,fontsize=28)
        ax.set_title(title,fontsize=32)

        ax.grid(False)

        if self.log_scale:
            plt.yscale("log")

        if self.draw_minimum:
            plt.axhline(y=min_line,xmin=0,xmax=len(labels))

        if self.draw_maximum:
            plt.axhline(y=max_line,xmin=0,xmax=len(labels))

        for label,point in self.points.items():
            plt.axhline(y=point,xmin=0,xmax=len(labels))

        if self.show_outliers:
            ax.boxplot(dataset)
        else:
            ax.boxplot(dataset,sym="")
            ax.margins(x=0)

        if not self.bounds is None:
            ax.set_ylim(self.bounds)

        if self.show_labels:
            ax.set_xticklabels(labels)
        else:
            ax.set_xticklabels([])

        #plt.tight_layout()
        #plt.gcf().subplots_adjust(bottom=0.15)
        plt.savefig(filepath,bbox_inches='tight')
        plt.clf()

