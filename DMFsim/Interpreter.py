# -*- coding: utf-8 -*-
"""
11/11/21

@author: Andrew Stephan

This is the library that converts a list of symbol strings into an assembly tree.

Each Node in the tree encodes a subset of the symbol list and contains instructions for
chemically constructing that subset out of its constituent parts. 

Leaf nodes contain a single symbol and no instructions at all; nodes just above the leaf layer contain
instructions that operate upon single-symbol droplets. Their parents operate upon their product droplets, and so on.

Note that the assembly tree implicitly encodes the dependcies between the nodes. Two Nodes with no direct descendant relationship
can be compiled in parallel by the Scheduler. But a given node cannot be compiled until all of its descendants (if any) have been compiled.


"""
from functools import reduce

version = 1

def Linkers(linkernum = None):
    if linkernum is None:
        for i in range(2048):
            yield(['L' + str(i)])
    else:
        for i in range(linkernum):
            yield(['L' + str(i)])
        
class Node():
    #This is the building-block of the assembly tree. Contains instructions for assembling one subset of the data.
    def __init__(self, data = None, parent = None, inst_list = None):
        self.data = data
        self.children = []
        self.depth = 0
        self.parent = parent
        self.inst_list = inst_list
        
        #The variables below here are for future use by the router, not the interpreter
        self.droplets = {}  #Keeps track of the locations of the species used in this node
        self.timer = None       #Keeps track of any delay commands in this node, for executing Gibson, Purify, etc.
        self.selected_sites = []#Tracks the instruction sites selected at the current step
        self.pulling_sites = [] #Tracks where the node has decided to pull a droplet
        self.inst_i = -1       #Tracks the index of the current instruction being advanced
        self.waiting = False #Used to indicate the node is in the process of pulling droplets
        self.record = [] #Used to record what the node is currently working on, in case it needs to be annealed
        self.active_droplets = [] #References the droplets that are active during this instruction
        self.last_cleared = None #The last time this was cleared
        
        if parent is not None:
            parent.Add_Child(self)
            
    def Set_Data(self, data, inst_list):
        self.data = data
        self.inst_list = inst_list
        
    def Add_Child(self, child):
        self.children.append(child)
        child.parent = self
        child.depth = self.depth + 1
        
    def Correct_Depths(self):
        #In case the parent's depth has increased, reset this node's depth
        if self.parent:
            self.depth = self.parent.depth + 1       
        
        #Now that this node's depth is correct, fix its child nodes' depths also.
        for child in self.children:
            child.Correct_Depths()
            
    def Is_Leaf(self):
        #If it has no children, it is a leaf node by definition
        return self.children == []
    
    def Record_State(self, delete_grp=True):
        #Records the current status of the node.
        #Used for Annealing, but this is not implemented in current version. 11/11/21
        self.record = []
        
        #If the node has concluded, record nothing
        if self.Concluded():
            return
        
        #Otherwise, get the current instruction and associated key list
        inst = self.inst_list[self.inst_i]
        key_list = [tuple(x) for x in inst[1:] if tuple(x) in self.droplets]
        
        #For all the droplets that are currently in use, record their key, destination, and following-target if any.
        for key, dp in self.droplets.items():
            self.record.append((key, dp.dest, dp.following, dp.collision_group))
            if delete_grp:
                dp.following = None
                dp.Set_Collision_Group([dp])
    
    def Resume(self):
        #Resumes the droplets from where they left off.
        #Resets their destinations, following, and collision group data
        #Note: this is not used in the current setup, but may be convenient later if 
        #Annealing needs to be reintroduced. 11/11/21
        
        #By default, tell all the droplets to stop moving right where they are.
        for dp in self.droplets.values():
            dp.Set_Dest(dp.Get_Loc(asindex = True))
        
        #For any droplet with recorded data, overwrite.
        for (key, dest, following, grp) in self.record:
            self.droplets[key].Set_Follow(following)
            self.droplets[key].Set_Collision_Group(grp)
            
            #Reset the destination only if this is an active droplet
            if self.droplets[key] in self.active_droplets:
                self.droplets[key].Set_Dest(dest)
        
        #Clear the record
        self.record = []
        
    def Clear(self, grid, time, parent = None):
        #Clears the droplet and gridpoint activity
        self.last_cleared = time
        self.timer = None
        for index in self.selected_sites:
            grid[index].selected_by = parent
        #The parent inherits the child's selected sites (I.E. shunting sites)
        if parent:
            parent.selected_sites += self.selected_sites
        self.selected_sites = []
        self.active_droplets = []
        for dp in self.droplets.values():
            dp.locked = False   #Unlock the droplets
            
    def Concluded(self):        
        #Tells you if the node has finished all its instructions
        return (not self.In_Progress()) and (not self.waiting) and (self.inst_i == (len(self.inst_list) - 1))
    
    def In_Progress(self):
        #Tells you if the node is waiting on a timer/waiting on its droplets to complete this step.
        if self.timer:
            return self.timer != 0 #Check if it has reached zero
        return not all([dp.At_Dest() or dp.shunting or (dp not in self.active_droplets) for dp in self.droplets.values()])

 
def Partition(arg,n):
    #Convenience function for partitioning strings and lists into segments of length n
    
    #If n or fewer parts, just return the args split into singleton lists.
    if len(arg) <= n:
        return [[x] for x in arg]
    else:
        output = [arg[i*n:(i+1)*n] for i in range(int(len(arg)/n))]
        remainder = len(arg)%n
        if remainder != 0:
            output.append(arg[-remainder:])
    
    return output

            
def Build_Tree(data, n, linkernum=None):
    #Builds assembly tree and fills in the Node data, assembly instructions, etc.
    #This yields a data structure that encodes the dependency (or lack thereof) between
    #all of the individual assembly operations needed to build the final product.
    
    #Nodes that do not share a descendant-ancestor relationship can be compiled in parallel
    #by the Scheduler. On the other hand, any node with a descendant cannot be compiled
    #until all of its descendants have been compiled.
    
    linkers = Linkers(linkernum)
    
    #Instantiate the bottom level of nodes, without any parents yet.
    # nodes = [Node([next(linkers), x, next(linkers)]) for x in data]
    nodes = [Node([x]) for x in data]
    
    #Until there is only one node in the list, repeat this process
    while len(nodes) > n:
        #Partition the nodes 
        node_partition = Partition(nodes, n)
        
        #Reset the nodes list for next iteration
        nodes = [] 
        
        #For each partition, make a new parent node above all the children in the partition
        for partition in node_partition:
            
            #Instantiate the parent node
            parent_data = []
            parent = Node()
            
            #If there is only one node in the partition, just pass the data
            #up the tree
            if len(partition) == 1:
                parent.Add_Child(partition[0])
                parent.data = partition[0].data
                parent.inst_list = []
            
            else:
                for node in partition:
                    #Compile the child's data for the parent
                    parent_data += node.data
                    
                    #Add the child to the parent node
                    parent.Add_Child(node)
                    
                #Set the parent's data
                try:
                    parent.Set_Data(*Assemble(parent, linkers))
                except StopIteration:
                    # print("\nWarning: Linker count overflow, returning to beginning.")
                    linkers = Linkers(linkernum)
                    parent.Set_Data(*Assemble(parent, linkers))
            
            #Update the nodes list with the new parent node
            nodes.append(parent)
            
    #Once there are only n or fewer nodes, repeat the process one final time to make the root node.
    root = Node()
    for node in nodes:
        root.Add_Child(node)
        
    try:
        root.Set_Data(*Assemble(root, linkers))
    except StopIteration:
        linkers = Linkers(linkernum)
        root.Set_Data(*Assemble(root, linkers))

        
    #Correct the depths in the tree
    root.Correct_Depths()
    
    #Now we will assemble the nodelist
    #Start by getting the depth
    node = root
    while node.children != []:
        node = node.children[0]
    depth = node.depth
    
    #Initialize the nodelist
    nodes = [[] for i in range(depth + 1)]
    
    #Fill in the nodelist
    nodes[0] = [root]
    for i in range(1, depth+1):
        nodes[i] = [child for node in nodes[i-1] for child in node.children]
        
    #Reverse the nodelist so that the leaf nodes are at index 0
    nodes.reverse()
    
    #Return the root node
    return root, nodes    
            
def Assemble(node, linkers, include_extras = True):    
#This is where the specific chemical protocol is hard-coded.
#This looks at the node and writes a series of commands to merge and assemble
#the elements contained within the node's children. 
#Then, it overwrites the data in the node with the new species list,
#including any linkers attached during the process.

#First, generate commands merging and gibson-ing the individual args with the linkers
#Note that once the linkers and args have been merged, the 'droplet' is no longer
#identified by the [arg, linker] combo but just by arg.
#This is because I have decided to always identify droplets by their data-corresponding components,
#if they have any. So a linker droplet will be identified by the linker, but a droplet
#with symbols in it will be identified by its symbols even if it also has linkers.
#Of course, this is just on the Interpreter side. The Lab's Droplet objects will contain
#references to the overhanging ends, which may be linker or symbol ends. 
    
    instructions = []
    arglist = [child.data for child in node.children]
    n = len(arglist)
    species_sets = []
    for i in range(n):
        merge = []
        
        #Don't put on redundant end-linkers
        if i == 0:
            l1 = []
        else:
            l1 = next(linkers)
                    
        if i == n-1:
            l2 = []
        else:
            l2 = next(linkers)
        
        #Add the left-linker to the merge instruction
        if l1 != []:
            merge.append(l1)
            
        #Add the symbol
        merge.append(arglist[i])
        
        #Add the right-linker
        if l2 != []:
            merge.append(l2)
            
        #Sort the list. This is to preserve consistency for referencing later on
        merge.sort()
        
        #Add the 'Merge' text to the start of the instruction
        
        merge.insert(0,'Gibson_Move') #For V3
        merge.append(['gibson_mix']) #For V1 and V3
        
        #Append the completed Merge instruction to the list
        instructions.append(merge)
        
        #Add this species set to the total list
        z = l1 + arglist[i] + l2
        species_sets.append([reduce((lambda x, y: x + y), z[:])])
        
        z.sort()    #Then sort z
        
        #Build the gibson command
        instructions.append(['Gibson'] + [z + ['gibson_mix']])
        
    #Now generate commands merging the resultsd
    pre_net = reduce((lambda x,y: x + y), species_sets) #This will be for the 'data' output
    species_sets.sort()     #Sort the species sets for preserve referencing consistency
    net = reduce((lambda x, y: x + y), species_sets) #This will be for the instructions
    
    instructions.append(['Gibson_Move'] + species_sets + [['gibson_mix']])
    instructions.append(['Gibson', net + ['gibson_mix']])
    
    #Add the PCR and purify commands
    if include_extras:
        #I can leave out the PCR and purification steps for ease of reading when testing this code.
        #Here '0' is a code meaning 'use the droplet in position 0' rather than a specific key.
        instructions.append(['Purify_Move', 0, ['purify_mix']])
        instructions.append(['Purify', 0,])
        instructions.append(['PCR_Move', 0, ['PCR_mix']])
        instructions.append(['PCR', 0])
    
    return [reduce((lambda x, y: x + y), pre_net)], instructions