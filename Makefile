
VISUALIZE=--visualize
VISUALIZE=

calibrate-minerr:
	python3 -u grendel.py calibrate --no-oscilloscope --calib-obj min_error device-state/calibrate/min_error.grendel 

calibrate-maxfit:
	python3 -u grendel.py calibrate --no-oscilloscope --calib-obj max_fit device-state/calibrate/max_fit.grendel 
	python3 -u grendel.py calibrate --no-oscilloscope --calib-obj min_error device-state/calibrate/max_fit.grendel 

profile-maxfit:
	python3 -u grendel.py profile --no-oscilloscope --calib-obj max_fit device-state/calibrate/max_fit.grendel 
	python3 -u grendel.py profile --no-oscilloscope --calib-obj min_error device-state/calibrate/max_fit.grendel 

profile-minerr:
	python3 -u grendel.py profile --no-oscilloscope --calib-obj min_error device-state/calibrate/min_error.grendel 

models-maxfit:
	python3 model_builder.py infer --calib-obj max_fit ${VISUALIZE}

models-minerr:
	python3 model_builder.py infer --calib-obj min_error ${VISUALIZE}

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

clean-models:
	rm -rf device-state/datasets
	rm -rf device-state/models/*
	rm -rf device-state/model.db
