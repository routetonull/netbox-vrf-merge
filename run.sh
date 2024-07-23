#!/usr/bin/env bash
start=$(date)
echo START $start >> nb-merge.log
source .venv/bin/activate
./nb-merge-vrf.py          
finish=$(date)
echo FINISH $finish >> nb-merge.log