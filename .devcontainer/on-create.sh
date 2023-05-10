#!/bin/bash

conda init bash
source ~/.bashrc

conda install -y -c conda-forge mamba
mamba env create -f environment.yml
