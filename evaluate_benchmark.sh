#!/bin/bash

TMPDIR=eval-tmpdir
BMARK=${1}
FLAGS=${2}
OBJECTIVE=qtytau
echo $BMARK

if [[ "$FLAGS" == *"g"* ]]; then
	python3 -u legno.py lgraph  --adps 10  ${BMARK}
fi


if [[ "$FLAGS" == *"e"* ]]; then
	python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method phys --calib-obj minimize_error ${BMARK}
	python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method phys --calib-obj maximize_fit ${BMARK}


	echo "detailed analysis on one execution"
	mkdir -p ${TMPDIR}/
	mv outputs/legno/unrestricted/${BMARK}/lgraph-adp/*.adp ${TMPDIR}/
	mv ${TMPDIR}/${BMARK}_g0.adp outputs/legno/unrestricted/${BMARK}/lgraph-adp/

	# no scaling transform, no mode selection
	python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method ideal --one-mode --no-scale --calib-obj minimize_error ${BMARK}

	# no scaling transform, allow for mode selection
	python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method ideal --no-scale --calib-obj minimize_error ${BMARK}
	# scaling transform, no mode selection 
	python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method ideal --one-mode --calib-obj minimize_error ${BMARK}
	# scaling transform + mode selection, no physical model
	python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method ideal --calib-obj minimize_error ${BMARK}

	python3 -u legno.py lexec ${BMARK}
	python3 -u legno.py lwav ${BMARK}

	mv ${TMPDIR}/${BMARK}_*.adp outputs/legno/unrestricted/${BMARK}/lgraph-adp/
fi

if [[ "$FLAGS" == *"x"* ]]; then
	# generate up to 500 signal maximizing circuits
 	mkdir -p ${TMPDIR}/
	mv outputs/legno/unrestricted/${BMARK}/lgraph-adp/*.adp ${TMPDIR}/
	mv ${TMPDIR}/${BMARK}_g0.adp outputs/legno/unrestricted/${BMARK}/lgraph-adp/

	OBJECTIVE=rand
	MIN_AQM=1.0
	MIN_DQM=5.0
	MIN_DQME=5.0
	MIN_TAU=0.001
        NUM_CIRCS=500
	python3 -u legno.py lscale --model-number c4  --min-aqm ${MIN_AQM} --min-dqme ${MIN_DQME} --min-dqm ${MIN_DQM} --min-tau ${MIN_TAU} --objective ${OBJECTIVE} --scale-adps ${NUM_CIRCS} --scale-method phys --calib-obj maximize_fit ${BMARK}

	python3 -u legno.py lexec ${BMARK}
	python3 -u legno.py lwav ${BMARK}
	mv ${TMPDIR}/${BMARK}_*.adp outputs/legno/unrestricted/${BMARK}/lgraph-adp/
fi

if [[ "$FLAGS" == *"r"* ]]; then
	# generate up to 500 signal maximizing circuits
 	mkdir -p ${TMPDIR}/
	mv outputs/legno/unrestricted/${BMARK}/lgraph-adp/*.adp ${TMPDIR}/
	mv ${TMPDIR}/${BMARK}_g0.adp outputs/legno/unrestricted/${BMARK}/lgraph-adp/

	OBJECTIVE=rand
	MIN_AQM=1.0
	MIN_DQM=5.0
	MIN_DQME=5.0
	MIN_TAU=0.001
        NUM_CIRCS=500
	python3 -u legno.py lscale --model-number c4  --min-aqm ${MIN_AQM} --min-dqme ${MIN_DQME} --min-dqm ${MIN_DQM} --min-tau ${MIN_TAU} --objective ${OBJECTIVE} --scale-adps ${NUM_CIRCS} --scale-method phys --calib-obj minimize_error ${BMARK}

	python3 -u legno.py lexec ${BMARK}
	python3 -u legno.py lwav ${BMARK}
	mv ${TMPDIR}/${BMARK}_*.adp outputs/legno/unrestricted/${BMARK}/lgraph-adp/
fi

