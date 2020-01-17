#!/bin/bash
python3 setup_exp_data.py backup
python3 setup_exp_data.py install
python3 exp_driver.py scan
python3 exp_driver.py analyze
python3 exp_driver.py visualize paper-quality-graphs
python3 exp_driver.py visualize paper-quality-energy-runtime

