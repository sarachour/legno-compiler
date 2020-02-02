#!/bin/bash
python3 exp_driver.py scan
python3 exp_driver.py analyze --include-pending
python3 exp_driver.py visualize paper-circuit-summary
python3 exp_driver.py visualize paper-chip-summary
python3 exp_driver.py visualize paper-benchmark-summary
python3 exp_driver.py visualize paper-compile-time
python3 exp_driver.py visualize paper-energy-runtime
