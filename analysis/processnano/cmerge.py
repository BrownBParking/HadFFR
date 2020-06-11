'''
Postprocessing for data condor jobs.
- Merge the subjob coffea files. Result: 1 coffea file per run-period-part. 
- Convert coffea to ROOT files, for RooFit.
@arg dir = folder containing subjobs, e.g. /home/dryu/BFrag/data/histograms/condor/job20200609_115835
            (Contains folders Run2018*_part*)
'''
import os
import sys
from coffea import util
import glob
import re
from pprint import pprint
import uproot
from collections import defaultdict
from functools import partial
import numpy as np


def cmerge(output_file, input_files, force=False):
    print("cmerge(output_file={}, input_files={}".format(output_file, input_files))
    if os.path.isfile(output_file) and not force:
        raise ValueError("Output file {} already exists. Use option force to overwrite.".format(output_file))
    output = None
    for input_file in input_files:
        if not output:
            output = util.load(input_file)
        else:
            output.add(util.load(input_file))
    print(f"Saving output to {output_file}")
    util.save(output, output_file)

def coffea2roofit(input_files, input_objs, output_file, output_objs=None, combine_datasets=True):
    '''
    Convert {dataset:Bcand_accumulator} output to TTree.
    Bcand_accumulator has dict-like structure {branch: array}
    input_obj = key or keys needed to find Bcand object
    datasets are added together.
    '''
    print("Welcome to coffea2roofit")
    print("Input files:")
    print(input_files)
    print("Output file:")
    print(output_file)

    with uproot.recreate(output_file) as output_filehandle:
        # Make list of datasets and branches
        branches = {}
        branch_types = {}
        input_stuff = util.load(input_files[0])
        for input_obj in input_objs:
            branches[input_obj] = []
            branch_types[input_obj] = {}
            for k1 in input_stuff[input_obj].keys():
                for branch_name in input_stuff[input_obj][k1].keys():
                    branches[input_obj].append(branch_name)
                    branch_types[input_obj][branch_name] = input_stuff[input_obj][k1][branch_name].value.dtype
                break

        if not output_objs:
            output_objs = {}
            for input_obj in input_objs:
                output_objs[input_obj] = input_obj

        bad_input_files = []
        nevents = 0
        for input_file in input_files:
            print("Processing {}".format(input_file))
            if os.path.getsize(input_file) < 1000:
                print(f"WARNING: Input file {input_file} looks corrupt. Skipping.")
                bad_input_files.append(input_file)
                continue
            input_stuff = util.load(input_file)
            print(input_stuff["nevents"])
            for key, value in input_stuff["nevents"].items():
                nevents += value
            for input_obj in input_objs:
                for k1 in input_stuff[input_obj].keys():
                    # Determine which tree to fill, and create it if it doesn't exist
                    if combine_datasets:
                        tree_name = output_objs[input_obj]
                    else:
                        tree_name = f"{output_objs[input_obj]}_{k1}"
                    if not tree_name in output_filehandle:
                        print("Creating tree {}".format(tree_name))
                        output_filehandle[tree_name] = uproot.newtree(branch_types[input_obj])

                    # Make {branch : array} dict for filling
                    bcand_accumulator = input_stuff[input_obj][k1]
                    bcand_array = {}
                    for branch in branches[input_obj]:
                        bcand_array[branch] = bcand_accumulator[branch].value

                    # Fill
                    output_filehandle[tree_name].extend(bcand_array)
                # End loop over input branches in Bcand array
            # End loop over Bcand arrays
        
        # Write nevents to file
        output_filehandle["nevents"] = np.histogram([0], bins=[-0.5, 0.5], weights=[nevents])

        if len(bad_input_files) >= 1:
            print("Some input files were skipped due to small size:")
            print(bad_input_files)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Add coffea subjobs back together")
    parser.add_argument("-d", "--dir", type=str, help="Folder containing subjobs")
    parser.add_argument("-f", "--force", action="store_true", help="Force overwrite")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        raise ValueError("Directory {} does not exist".format(args.dir))

    print("Merging coffea subjobs...")
    runpart_dirs = sorted(glob.glob(f"{args.dir}/Run2018*_part*/"))
    runparts = [x.split("/")[-2] for x in runpart_dirs]
    for runpart in runparts:
        output_file = f"{args.dir}/{runpart}.coffea"
        input_files = glob.glob(f"{args.dir}/{runpart}/DataHistograms_Run*_part*subjob*.coffea")
        cmerge(output_file, input_files, args.force)
    print("...done merging coffea subjobs.")

    print("Converting coffea files to ROOT TTrees for RooFit")
    # Determine which objects to convert (any coffea object with "Bcands" in name)
    input_objs = []
    stuff = util.load(f"{args.dir}/{runparts[0]}.coffea")
    for key in stuff.keys():
        if "Bcands" in key:
            input_objs.append(key)
    for runpart in runparts:
        input_coffea_file = f"{args.dir}/{runpart}.coffea"
        output_root_file = f"{args.dir}/{runpart}.root"
        coffea2roofit(input_files=[input_coffea_file], input_objs=input_objs, output_file=output_root_file, combine_datasets=True)
