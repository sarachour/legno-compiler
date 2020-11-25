
VISUALIZE=--visualize
VISUALIZE=

remote-update:
	rm -rf device-state*
	rm -rf outputs*
	scp -r jray@lab-bench.csail.mit.edu:/Users/JRay/Documents/SaraAchour-Workspace/legno-compiler/device-state device-state
	scp -r jray@lab-bench.csail.mit.edu:/Users/JRay/Documents/SaraAchour-Workspace/legno-compiler/outputs outputs
	#sshfs jray@lab-bench.csail.mit.edu:/Users/JRay/Documents/SaraAchour-Workspace/legno-compiler/device-state device-state
	#sshfs jray@lab-bench.csail.mit.edu:/Users/JRay/Documents/SaraAchour-Workspace/legno-compiler/outputs outputs
	

clean-executions:
	rm -f outputs/experiments.db
	rm -rf outputs/legno/*/*/grendel
	rm -rf outputs/legno/*/*/lscale-adp
	rm -rf outputs/legno/*/*/lscale-diag
	rm -rf outputs/legno/*/*/out-waveform
	rm -rf outputs/legno/*/*/plots
	rm -rf outputs/legno/*/*/sim
	rm -f outputs/legno/*/*/times/srcgen.txt
	rm -f outputs/legno/*/*/times/lscale.txt

