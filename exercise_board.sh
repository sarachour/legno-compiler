#!/bin/bash

MODEL_NUMBER=$1

echo "====== BOARD <${1}> ====="
python3 compile.py --num-lgraph 1 --yes cos ${MODEL_NUMBER}
python3 compile.py --num-lgraph 1 --yes cosc ${MODEL_NUMBER}
python3 compile.py --num-lgraph 1 --yes pend ${MODEL_NUMBER}
python3 compile.py --num-lgraph 1 --yes spring ${MODEL_NUMBER}
python3 compile.py --num-lgraph 1 --yes vanderpol ${MODEL_NUMBER}
python3 compile.py --num-lgraph 1 --yes heatN4X2 ${MODEL_NUMBER}
python3 compile.py --num-lgraph 1 --yes forced ${MODEL_NUMBER}
python3 compile.py --num-lgraph 1 --yes pid ${MODEL_NUMBER}
python3 compile.py --num-lgraph 1 --yes kalsmooth ${MODEL_NUMBER}
python3 compile.py --num-lgraph 1 --yes smmrxn ${MODEL_NUMBER}
python3 compile.py --num-lgraph 1 --yes gentog ${MODEL_NUMBER}
python3 compile.py --num-lgraph 1 --yes bont4 ${MODEL_NUMBER}

echo "===== TESTING BOARD <${1}> ====="
python3 meta_grendel.py test_board --minimize-error --maximize-fit ${MODEL_NUMBER}


