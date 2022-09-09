# -*- coding: utf-8 -*-
"""
11/11/21

@author: Andrew Stephan

This script goes over all the steps needed to instantiate a virtual lab, populate it
with gridpoints and droplet reservoirs, then run a DNA assembly on it.

It's broken into sections blocked off by:
    #############
    <text>
    #############
    
Section 1 contains a function that checks if the outcome was correct, a coordinate pair generator for later use,
and a linker-strand nucleotide generator. It's not crucial to understanding the rest, so you can skip over it.

Section 2 instantiates the lab and populates it with gridpoints, reservoirs (i.e. pull sites) and other reaction
sites such as Gibson, purify, etc. You can do this manually or let the system randomly choose them.

Section 3 is where all the magic happens. First you set the data, then you call the Interpreter
to build an assembly tree. Then you call the Scheduler to compile the assembly instructions and generate Lab commands.
It also makes a sequence of figures so you can watch the droplets moving in "real-time".

In order to see the complete sequence of all lab commands in the proper order, print out
the lab's history variable. It's going to be rather a rather lengthy list of dictionaries.
The order index corresponds to the time at which that command dictionary was executed.

"""

#Import the libraries. 
from tkinter import W
import Interpreter as Int
from Scheduler import *
from Lab import *
import copy
import random
import sys
import pandas
import subprocess


#########################################################
#SECTION 0
#Command line arg parsing
#########################################################

# Command line arg patch -- Softsun2
def parse_benchmark_cmdline_args():
    gridsize = 1000     # default gridsize
    gene_length = 5     # default gene length 
    host_string = None
    b_round = None

    for arg in sys.argv[1:]:
        if "--gridsize=" in arg:
            gridsize_string = arg.split("=")[1]
            if gridsize_string.isdigit():
                gridsize = int(gridsize_string)
        elif "--gene-length=" in arg:
            gene_length_string = arg.split("=")[1]
            if gene_length_string.isdigit():
                gene_length = int(gene_length_string)
        elif "--host-string=" in arg:
            host_string = arg.split("=")[1]
        elif "--round=" in arg:
            round_string = arg.split("=")[1]
            if round_string.isdigit():
                b_round = int(round_string)

    return gridsize, gene_length, host_string, b_round


#########################################################
#SECTION 1
#Some basic functions and generators, you can probably ignore this section
#########################################################

#A function to check if the lab output matches the input data
def Check(lab, data):
    if len(lab.droplets) != 1:
        return False
    checkdata = ''.join(''.join(data).split('_')[1::2])
    lab_output = ''.join(str(lab.droplets[0].species).split('_')[1::2])
    
    if checkdata == lab_output:
        print('\nSuccess!')
        return True
    else:
        print('\nFailure.')
        return False
        
#Generator for the coordinates around the boundary of the grid
#which is where the droplet pull reservoirs will be located
def coordgen(width):
    coords = [(0, i) for i in range (2, width-1, 2)] #coordinates on the top row
    coords += [(width-1, i) for i in range(2, width-1, 2)] #coordinates on the bottom row
    coords += [(i, 0) for i in range(0, width, 2)] #Coordinates on the left side
    coords += [(i, width-1) for i in range(0, width, 2)] #Coordinates on the right side

    while coords != []:
        yield(coords.pop(random.randint(0, len(coords)-1)))
        
#Generator for 512 linker pairs
#Their overhanging DNA strands must match only each other regarding Watson-Crick pairing.
def linker_ends():
    #Generate the right ends
    rl = ['A', 'T', 'G', 'C']
    right_ends = [(w + x + y + z + z0) for w in rl for x in rl for y in rl for z in rl for z0 in rl]
    for i in range(len(right_ends), 0, -1):
        right_ends.insert(i, 'T')
        
    #Generate the left ends
    ll = ['T', 'A', 'C', 'G']
    left_ends = [(w + x + y + z + z0) for w in ll for x in ll for y in ll for z in ll for z0 in ll]
    for i in range(len(left_ends)-1, -1, -1):
        left_ends.insert(i, 'C')

    #Yield the endcaps
    for i in range(len(right_ends)):
        yield [left_ends[i], right_ends[i]]

#########################################################
#SECTION 2
#This is where we set up the Lab.
#Mostly that involves populating it with Gibson sites
#and reservoirs from which you can pull droplets of the various symbols, linkers, etc.
#No routing takes place here, this is all just setup.
#########################################################
random.seed(42)

### Initialization stage ###

#Set the gene's symbol length (The number of symbols to be assembled into a single gene)
#and the lab grid width
width, datalen, host_string, b_round = parse_benchmark_cmdline_args()

#Get a list of the interior grid coordinates.
#This is where the reaction sites *could* be placed.
coords = [(x,y) for x in range(4,width-4,4) for y in range(4,width-4,4)]

num_gibson_sites = 5
num_PCR_sites = 5
num_purify_sites = 5
gibson_limit = 3 #Assume 3 strands can be attached at a time, no more.
        
#Randomly select some points to act as gibson, purify and PCR sites.
# gibson += [(), (), ()]   #Your entries here  
# purify += [(), (), ()]   #Your entries here  
# PCR += [(), (), ()]   #Your entries here  
gibson = ['Gibson']
gibson += [coords.pop(random.randint(0, len(coords) - 1)) for i in range(num_gibson_sites)]
purify = ['Purify']
purify += [coords.pop(random.randint(0, len(coords) - 1)) for i in range(num_purify_sites)]
PCR = ['PCR']
PCR += [coords.pop(random.randint(0, len(coords) - 1)) for i in range(num_PCR_sites)]

#Collect the instruction locations
inst_locs = [gibson, purify, PCR]

#Define the base DNA species dictionary
#All symbols will have a left overhanging 'A' and right overhanging 'G'. 
base_dict = {'type':'DNA', 'ends':['A','G'], 'loc':[(0,0)], 'area':1}

#Generate the symbols and their pull locations
gen = coordgen(width)
symbols = []
symbol_dicts = []
num_symbols = int(width/2) #This number is arbitrary
for i in range(num_symbols):
    symbols.append('_S' + str(i) + '_')
    d = copy.copy(base_dict)
    d['loc'] = [next(gen)]
    symbol_dicts.append(d)
    
#Generate the linkers and their pull locations
ends = linker_ends()
linkers = []
linker_dicts = []
num_linkers = width #This is arbitrary
for i in range(num_linkers):
    linkers.append('L' + str(i))
    d = copy.copy(base_dict)
    d['loc'] = [next(gen)]
    d['ends'] = next(ends)
    linker_dicts.append(d)

#Compile the pull data dictionary
pull_data = dict(zip(symbols,symbol_dicts))
pull_data.update(dict(zip(linkers,linker_dicts)))
pull_data.update({'gibson_mix':{'type':'reagent', 'loc':[next(gen) for i in range(int(width/8 - 2))], 'area':1}})
pull_data.update({'purify_mix':{'type':'reagent', 'loc':[next(gen) for i in range(int(width/16 - 1))], 'area':1}})
pull_data.update({'PCR_mix':{'type':'reagent', 'loc':[next(gen) for i in range(int(width/16 - 1))], 'area':1}})

#########################################################
#SECTION 3
#This is where we input the desired symbol sequence and actually run the Scheduler.
#This is where all the routing takes place.
#########################################################

#Generate the gene
#Alternatively, you could manually enter the data as strings: ['_S0_', '_S4_', ...]
data = [random.choice(symbols) for i in range(datalen)]  
# data = ['','',''] #Your input here
grid_dim = np.array([width, width])


#This line calls the Interpreter and generates an assembly tree.
#The assembly tree is a trinary tree structure that contains information
#about the operations needed to assemble the given data, as well as the
#ordering and which operations are parallelizable.
root, nodes = Int.Build_Tree(data, gibson_limit, linkernum = len(linkers))

#This line instantiates the virtual Lab object and all of its electrostatic gridpoints.
#All commands that the router generates will be sent to the Lab for execution, and
#the Lab will generate new results for the Router to use.
grid_spacing = 1
lab = Lab(grid_dim, grid_spacing, inst_locs, pull_data, record_congestion=True)

# This line instantiates the Router, which reads in data concerning both the Lab
#and the Interpreter's assembly tree.
sch = Scheduler(nodes, inst_locs, pull_data, lab)

#Finally, this line runs the routing function.
#The Router moves one time-step at a time, directing droplets towards their destinations
#and setting new destinations when they arrive.
#One time-step corresponds to the time it takes a droplet to move one gridspace.
sch.Compile_Instructions(num=float('inf'), makeplot=False, wait_time=0.025, version=Int.version)

#Check if it succeeded in generating the symbols you asked for.
if Check(lab, data):
    # export droplet count
    total_droplets, max_droplet_count = lab.Get_Droplet_Counts()
    congestion_history = lab.Get_Congestion_History()

    gene_length_data_path = f'raw-data/{host_string}/'

    gene_length_data = [
        ('total droplets', 'max droplets', 'max congestion'),
        (total_droplets, max_droplet_count, max(congestion_history))
    ]
    pandas.DataFrame(tuple(gene_length_data)).to_csv(
        f'{gene_length_data_path}cg-{datalen}-{b_round}.csv',
        index=False,
        header=False
    )
