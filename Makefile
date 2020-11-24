
VISUALIZE=--visualize
VISUALIZE=

mount-remote-dirs:
	sshfs jray@lab-bench.csail.mit.edu:/Users/JRay/Documents/SaraAchour-Workspace/legno-compiler/device-state device-state
	sshfs jray@lab-bench.csail.mit.edu:/Users/JRay/Documents/SaraAchour-Workspace/legno-compiler/outputs outputs

unmount-remote-dirs:
	fusermount -u device-state
	fusermount -u outputs

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

