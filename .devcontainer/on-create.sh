#!/bin/bash

conda init bash
source ~/.bashrc

conda install -c conda-forge mamba
mamba env create -f environment.yml
