#! /usr/bin/env python
from __future__ import print_function, division
from collections import defaultdict, OrderedDict
import os
import sys
import math
import concurrent.futures
import gzip
import pickle
import json
import time
import numexpr
import array
from functools import partial
import re

import uproot
import numpy as np
from coffea import hist
from coffea import lookup_tools
from coffea import util
import coffea.processor as processor
import awkward
import copy
from coffea.analysis_objects import JaggedCandidateArray

from brazil.aguapreta import *
import brazil.dataframereader as dataframereader
from brazil.Bcand_accumulator import Bcand_accumulator

np.set_printoptions(threshold=np.inf)

class DataProcessor(processor.ProcessorABC):
  def __init__(self):
    # Histograms
    dataset_axis = hist.Cat("dataset", "Primary dataset")
    selection_axis = hist.Cat("selection", "Selection name")

    self._accumulator = processor.dict_accumulator()
    self._accumulator["nevents"] = processor.defaultdict_accumulator(int)
    self._accumulator["run_counter"] = processor.defaultdict_accumulator(partial(processor.defaultdict_accumulator, int))

  @property
  def accumulator(self):
    return self._accumulator

  def process(self, df):
    output = self._accumulator.identity()
    dataset_name = df['dataset']
    #print(np.unique(df["run"]))
    (runs, counts) = np.unique(df["run"], return_counts=True)
    output["run_counter"][dataset_name] += dict(zip(runs, counts))
    output["nevents"][dataset_name] += df.size
    return output

  def postprocess(self, accumulator):
      return accumulator

if __name__ == "__main__":

  import argparse
  parser = argparse.ArgumentParser(description="Make histograms for B FFR data")
  #parser.add_argument("--datasets", "-d", type=str, help="List of datasets to run (comma-separated")
  parser.add_argument("--workers", "-w", type=int, default=16, help="Number of workers")
  parser.add_argument("--quicktest", "-q", action="store_true", help="Run a small test job")
  parser.add_argument("--save_tag", "-s", type=str, help="Save tag for output file")
  parser.add_argument("--nopbar", action="store_true", help="Disable progress bar (do this on condor)")
  args = parser.parse_args()

  #datasets = args.datasets.split(",")

  # Inputs
  from data_index import in_txt
  re_runp = re.compile("(?P<runp>Run2018.*_part\d)_subjob")
  dataset_files = {}
  for runp, filelist in in_txt.items():
    match_runp = re_runp.search(runp)
    runp2 = match_runp.group("runp")
    if not runp2 in dataset_files:
      dataset_files[runp2] = []
    with open(filelist, "r") as filelisthandle:
      dataset_files[runp2].extend(x.strip() for x in filelisthandle.readlines())

  if args.quicktest:
    for runp in dataset_files:
      dataset_files[runp] = dataset_files[runp][:20]

  ts_start = time.time()
  print(dataset_files)
  output = processor.run_uproot_job(dataset_files,
                                treename='Events',
                                processor_instance=DataProcessor(),
                                executor=processor.futures_executor,
                                executor_args={'workers': 16, 'flatten': False, 'status':not args.nopbar},
                                chunksize=50000,
                                # maxchunks=1,
                            )
  print(output)
  util.save(output, f"RunCounts_{args.save_tag}.coffea")

  # Performance benchmarking and cutflows
  ts_end = time.time()
  total_events = 0
  dataset_nevents = {}
  for k, v in output['nevents'].items():
    if k in dataset_nevents:
      dataset_nevents[k] += v
    else:
      dataset_nevents[k] = v
    total_events += v

  print("Total time: {} seconds".format(ts_end - ts_start))
  print("Total rate: {} Hz".format(total_events / (ts_end - ts_start)))

