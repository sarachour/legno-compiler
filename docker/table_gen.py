#!/usr/bin/python
import sys

def proc(s):
	res=s.replace("%", "\\%") \
             .replace("#","\\#")
	return res

if len(sys.argv) < 2:
	print("USAGE: filename")
	sys.exit(1)

def execute(name):
        lines = []
        q = lambda x: lines.append(x)
        with open(name,'r') as fh:
                type=fh.readline().rstrip();
                flags = fh.readline().rstrip();
                caption=fh.readline().rstrip();
                label=fh.readline().rstrip();
                format=fh.readline().rstrip();

                q("\\begin{"+type+"}["+flags+"]")
                q("\\centering")
                q("\\footnotesize")
                q("\\begin{tabular}{"+format+"}")
                for line in fh:
                        words=line.rstrip()
                        if words == "HLINE":
                                q("   \hline")
                        else:
                                fields = words.split(',')
                                nline = "   ";
                                for f in fields:
                                        nline += proc(f) + " & "

                                nline=nline[:-2]+"\\\\";
                                q(nline)
                q("\\end{tabular}")
                q("\\caption{"+caption+"}")
                q("\\label{"+label+"}")
                q("\\end{"+type+"}")


        for line in lines:
          print(line)


execute(sys.argv[1])
