#!/bin/bash
if uname -r | grep -q el6; then
  source /cvmfs/sft.cern.ch/lcg/views/LCG_95apython3/x86_64-slc6-gcc8-opt/setup.sh
else
  source /cvmfs/sft.cern.ch/lcg/views/LCG_95apython3/x86_64-centos7-gcc8-opt/setup.sh
fi

python -m venv --copies venv

echo -e "\nexport PYTHONPATH=$PWD/venv/lib/python3.6/site-packages:$PWD:\$PYTHONPATH\n" >> venv/bin/activate

source venv/bin/activate
#python -m pip install setuptools pip --upgrade
#python -m pip install coffea
#python -m pip install xxhash
pip install --editable . 
