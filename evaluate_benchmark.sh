#!/bin/bash

BMARK=${1}
OBJECTIVE=qtytau
echo $BMARK

python3 -u legno.py lgraph  --adps 10  ${BMARK}

echo python3 legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method phys --calib-obj minimize_error ${BMARK}
python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method phys --calib-obj minimize_error ${BMARK}

echo python3 legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method phys --calib-obj maximize_fit ${BMARK}
python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method phys --calib-obj maximize_fit ${BMARK}


echo "detailed analysis on one execution"
mkdir -p tmp/
mv outputs/legno/unrestricted/${BMARK}/lgraph-adp/*.adp tmp/
mv tmp/${BMARK}_g0.adp outputs/legno/unrestricted/${BMARK}/lgraph-adp/

echo python3 legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method ideal --calib-obj minimize_error ${BMARK}
python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method ideal --calib-obj minimize_error ${BMARK}

echo python3 legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method ideal --no-scale --calib-obj minimize_error ${BMARK}
python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method ideal --no-scale --calib-obj minimize_error ${BMARK}

echo python3 legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method phys --one-mode --calib-obj minimize_error ${BMARK}
python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 10 --scale-method phys --one-mode --calib-obj minimize_error ${BMARK}

# generate 100 random circuits
OBJECTIVE=rand
echo python3 legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 100 --scale-method phys --calib-obj maximize_fit ${BMARK}
python3 -u legno.py lscale --model-number c4  --objective ${OBJECTIVE} --scale-adps 100 --scale-method phys --calib-obj maximize_fit ${BMARK}

mv tmp/${BMARK}*.adp ouputs/legno/unrestricted/${BMARK}/lgraph-adp/

python3 -u legno.py lexec ${BMARK}
python3 -u legno.py lwav ${BMARK}
