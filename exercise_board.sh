#!/bin/bash

MODEL_NUMBER=$1

echo "====== BOARD <${1}> ====="
python3 -u compile.py --num-lgraph 1 --yes dbgadc ${MODEL_NUMBER}
python3 -u run.py dbgadc
python3 -u compile.py --num-lgraph 1 --yes dbgfan ${MODEL_NUMBER}
python3 -u run.py dbgfan
python3 -u compile.py --num-lgraph 1 --yes dbgmult ${MODEL_NUMBER}
python3 -u run.py dbgmult

python3 compile.py --num-lgraph 1 --yes cos ${MODEL_NUMBER}
python3 run.py cos
python3 -u compile.py --num-lgraph 1 --yes cosc ${MODEL_NUMBER}
python3 -u run.py cosc
python3 -u compile.py --num-lgraph 1 --yes pend ${MODEL_NUMBER}
python3 -u run.py pend
python3 -u compile.py --num-lgraph 1 --yes spring ${MODEL_NUMBER}
python3 -u run.py spring
python3 -u compile.py --num-lgraph 1 --yes vanderpol ${MODEL_NUMBER}
python3 -u run.py vanderpol
python3 -u compile.py --num-lgraph 1 --yes heatN4X2 ${MODEL_NUMBER}
python3 -u run.py heatN4X2
python3 -u compile.py --num-lgraph 1 --yes forced ${MODEL_NUMBER}
python3 -u run.py forced
python3 -u compile.py --num-lgraph 1 --yes pid ${MODEL_NUMBER}
python3 -u run.py pid
python3 -u compile.py --num-lgraph 1 --yes kalsmooth ${MODEL_NUMBER}
python3 -u run.py kalsmooth
python3 -u compile.py --num-lgraph 1 --yes smmrxn ${MODEL_NUMBER}
python3 -u run.py smmrxn
python3 -u compile.py --num-lgraph 1 --yes gentog ${MODEL_NUMBER}
python3 -u run.py gentog
python3 -u compile.py --num-lgraph 1 --yes bont4 ${MODEL_NUMBER}
python3 -u run.py bont4

echo "===== TESTING BOARD <${1}> ====="
python3 -u meta_grendel.py test_board --minimize-error --maximize-fit ${MODEL_NUMBER}


