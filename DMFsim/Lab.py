# -*- coding: utf-8 -*-
"""
11/11/21

@author: Andrew Stephan
    
This library represents the physical lab-on-a-chip and attempts to simulate it.

The Lab object contains a dictionary of Gridpoint objects which interact with Droplet objects.

Droplet objects move around in simulated time by checking which nearby Gridpoint objects have nonzero electrical potentials
and using a simple heuristic to determine the droplet's response. This heuristic should probably be replaced by a more sophisticated calculation,
or at least updated to more accurately reflect such a calculation.
    
When Droplet objects undergo Gibson assembly, they explicitly check for DNA strand matching and hybridize according to Watson-Crick pairing.

Note that Gridpoint objects have the ability to track residues, but this does not currently impact the system in any way.
It's just there so that you can use it in the future.
        
    
"""
import numpy as np
import copy
import matplotlib.pyplot as plt
import matplotlib.colors as colors

class Lab():
    #This object represents a single 2D chip. 
    #It curates a set of Droplet and Gridpoint objects, determining how the
    #Droplets move and change, and allowing external code to control the Gridpoints.
    #Has methods for looping through all droplets and updating their locations/contents, updating gridpoint commands, etc.
    def __init__(self, grid_dim, grid_spacing, inst_capable_locations, pull_data, record_congestion = False, alpha = 1/3, beta = 2):
        #Note that the input inst_capable_locations should be a list of lists,
        #and each sublist should contain first a string identifying the instruction type,
        #and then a group of tuples identifying the gridpoint indices that can execute that instruction.
        
        #Also note that the grid volumes as currently programmed are uniform, but 
        #this could easily be modified. There could be a default volume, and then a 
        #list of alternate volumes and corresponding index pairs.
        
        self.grid_dim = grid_dim
        self.inst_capable_locations = inst_capable_locations
        self.pull_data = pull_data
        self.grid_spacing = grid_spacing
        self.time = -1
        self.comm_dicts = [] #Set of individual command dictionaries that will be compiled into one command.
        self.history = [] #Tracks all of the compiled command dictionaries
        self.n_drops = [] #Tracks how many droplets are on the lab at a given time
        self.record_congestion = record_congestion #Whether the lab should calculate congestion values or not
        self.congestion_tracker = []
        self.alpha = alpha
        self.beta = beta

        #Initialize the Gridpoint array
        rows, cols = grid_dim
        self.grid = dict([((row, col), Gridpoint(gridpoint_size = grid_spacing, indices = (row, col))) for col in range(cols) for row in range(rows)])
        for gp in self.grid.values():
            gp.Initialize_Neighbors(self.grid)

        #Initialize the Droplet list and instructions
        self.droplets = []
        self.Initialize_Insts()

        # Variables for benchmarking purposes
        self.n_total_droplets = 0
        
    def Initialize_Insts(self):
        #Add the instructions to the relevant Gridpoints
        if self.inst_capable_locations is not None:
            for sublist in self.inst_capable_locations:
                for index_pair in sublist[1:]:
                    self.grid[index_pair].Append_Inst_Types(sublist[0])
                
        #Set the pull data
        #The pull data is a dictionary with string species as keys.
        #Each value is itself a dictionary with the keys 'type', 'area' and 'loc'
        for species in list(self.pull_data.keys()):
            for loc in self.pull_data[species]['loc']:
                dic = self.pull_data[species]
                dic['species'] = species
                self.grid[loc].Set_Pull_Data(dic)
        
    def Update_Inst(self, index_list, inst_list):
        #The instructions should be passed as a list of dictionaries,
        #and each dictionary must have at least the following keys:
        #'inst_type' - the type of operation
        #'runtime' - the number of time-steps to complete this operation.
        #Indices should be passed as a list of tuples [(row, col)]
        if index_list is not None:
            for i in range(len(index_list)):
                self.grid[index_list[i]].Update_Inst(inst_list[i])
         
    def Advance(self, inst_indices=None, insts=None, pot_indices=None, pots=None, pull_indices=None, keys=None, nodes=None):
        #Reset all of the gridpoint potentials to 0
        for gp in self.grid.values():
            gp.Set_Potential(0)
            
        self.time += 1

        #Update the Gridpoint instructions.
        self.Update_Inst(inst_indices, insts)
        
        #Update the Gridpoint potentials
        self.Set_Potentials(pot_indices, pots)
        
        #Pull droplets
        self.Pull_Droplets(pull_indices, keys, nodes)
        
        #Move Droplets according to electrostatic control points.
            #Check that no droplets are outside the bounds of the grid.
            #Update droplet 'container' Gridpoints.
            #Update Gridpoint residues
        for droplet in self.droplets:
            droplet.Move(self.grid, self.time)
            
        #Advance Gridpoint instructions by one step.
            #Convert droplets according to mixing and heating controls, etc.
        for gridpoint in self.grid.values():
            try:
                gridpoint.Advance()
            except ValueError as e:
                print(gridpoint.indices)
                raise e
            
        #Delete all droplets marked for removal.
        self.Delete_Droplets()
        
        #Update the droplet counter
        self.n_drops.append(len(self.droplets))
        
        #Update the droplets' step trackers
        for dp in self.droplets:
            dp.steps.append((self.time, *dp.Get_Loc()))
          
        if self.record_congestion:
            self.congestion_tracker.append(self.Get_Congestion(self.alpha, self.beta))
            
    def Get_Congestion(self, alpha, beta):
        #Calculate congestion value and report it

        #For now, congestion is sum of area occupied by droplets divided by total area
        # sum([x.area for x in self.droplets])/(self.grid_dim[0]*self.grid_dim[1])

        # TODO(SS2): Derive a sensible congestion calculation
        """
        congestion is the sum of the unique gridpoints being used for routing,
        the gridpoints containing droplets, and the occluded gridpoints, divided
        by the total number of gridpoints

        """
        coords = []
        for i, droplet in enumerate(self.droplets):
            route = droplet.Get_Route()
            for coord_3d in route:
                # where coord_3d takes the format
                # (time, x, y)
                coord_2d = (coord_3d[1], coord_3d[2])

                area_gridpoints = [gridpoint.indices for gridpoint in droplet.gridpoints]
                area_gridpoints += [gridpoint.indices for gridpoint in droplet.occluded]

                if coord_2d not in coords:
                    coords.append(coord_2d)

                for gridpoint in area_gridpoints:
                    if gridpoint not in coords:
                        coords.append(gridpoint)


        congestion = 100 * (len(coords)/(self.grid_dim[0] ** 2))

        return congestion


            
    def Pull_Droplets(self, index_list, keys = None, nodes = None):
        #Pulls the droplets at the appropriate gridpoint.
        #Also passes along their key and summoning node information.
        if index_list is None:
            return
        
        for num, ind in enumerate(index_list):
            try:
                key = keys[num]
                node = nodes[num]
            except TypeError:
                key = None
                node = None
            #Indices should be passed as a list of tuples
            droplet_index = len(self.droplets)
            droplet = self.grid[ind].Pull_Droplet(droplet_index, key = key, node = node, grid = self.grid)

            # SS2
            self.n_total_droplets += 1

            self.droplets.append(droplet)
            
    def Set_Potentials(self, index_list, potential_list):
        if index_list is not None:
            for i, index_pair in enumerate(index_list):
                self.grid[index_pair].Set_Potential(potential_list[i])
            
    def Delete_Droplets(self):
        #It's important to loop through the list in reverse, otherwise the removal process
        #will not work properly due to shuffling the indices mid-loop.
        for index in range(len(self.droplets)-1, -1, -1):
            dp = self.droplets[index]
            if dp.to_delete:
                self.droplets.remove(dp)
                
                #Reset the collision group
                self.Reset_Collision_Group(dp)
                
        #Now reset the droplet indices.
        for i in range(len(self.droplets)):
            self.droplets[i].index = i

    def Reset_Collision_Group(self, dp):
        #Remove the given droplet from its own collision group
        grp = dp.collision_group
        grp.remove(dp)
        
        #If the group is down to one
        if len(grp) == 1:
            if grp[0].following is not None:
                grp[0].Set_Dest(None)
            grp[0].Set_Follow(None)
            grp[0].Set_Collision_Group(grp)
        else:
            #Updpate the droplets left in the group
            for droplet in grp:
                droplet.Set_Collision_Group(grp)
                
                #If one of them was following this droplet, redirect it to the nearest target
                if droplet.following is dp:
                    a = dp #For some reason I need this line.... the frame inside the list comprehension below loses track of what 'dp' is but not what 'a' is?!
                    droplet.Set_Follow(min([x for x in grp if x != droplet], key=(lambda z: Cartesian_Dist(z.Get_Loc(), a.Get_Loc()))))

        #Finally, delete the droplet object entirely to free up resources
        del dp;
            
    def Status_Update(self):
        print("\nStatus update at time = {}:".format(self.time))
        for dp in self.droplets:
            print("Droplet {} is in gridpoint {} containing species {}.".format(dp.index, dp.gridpoint.indices, dp.species))
        for gp in self.grid.values():
            if gp.in_process:
                print('Gridpoint {} is running process of type {} with remaining runtime {}.'.format(gp.indices,gp.state_inst['inst_type'],gp.runtime))
                
    def Add_Commands(self, comm):
        #The input should be a dict or list of dicts containing some or all of the following keys:
            #inst_indices
            #insts
            #pot_indices
            #pots
            #pull_indices
            #These five keys should match the inputs of the same names that the Lab's 
            #Advance() method takes. 
        #This dict will be put into a temporary holding area
        if type(comm) is list:
            self.comm_dicts += comm
        else:
            self.comm_dicts.append(comm)    
        
    def Compile_Commands(self, status_update = False, makeplot = False, saveplot = False, wait_time = 2, ax = None):
        #Combine the dictionaries into one
        comms = self.Combine_Dicts(*self.comm_dicts)
        self.history.append(comms)
        
        #Clear the command holding-list
        self.comm_dicts = []
        
        #Advance the lab
        self.Advance(**comms)
        
        if status_update:
            self.Status_Update()
        
        if makeplot:
            Plot_Droplets(self, ax, wait_time = wait_time, step = self.time, saveplot=saveplot)

    def Combine_Dicts(self, *args):
        #Convenience function for combining multiple dictionaries
        if len(args) == 1:
            return args[0]
        
        if len(args) == 0:
            return {}
        
        output = args[0]
        for arg in args[1:]:
            for key in arg.keys():
                #Is this key in the output dict yet?
                if key in output.keys():
                    #If so, combine the values matching key
                    output[key] += arg[key]
                else:
                    #Otherwise, add this key:value pair to the output
                    output[key] = arg[key]
        return output   
            
    def Get_Droplet_Counts(self):
        return self.n_total_droplets, max(self.n_drops)

    def Get_Congestion_History(self):
        if self.record_congestion:
            return self.congestion_tracker
                
class Droplet():
    #This object represents a single droplet of liquid on the chip.
    #It has state variables such as coordinates, area and chemical species and various routing data.
    #The droplet has methods for simulating its movement based on nearby gridpoint activations,
    #tracking the chemical species contained within it and updating DNA strands based on Gibson assembly and Watson-Crick pairing.

    
    def __init__(self, coords, species, area, gridpoints, index, dest = None, key = None, node = None, time = None):
        self.coords = coords #numpy array with the coordinates of the droplet's center
        if type(species) is not list:
            self.species = [species]
        else:
            self.species = species #This should be a list of one or more strings and/or DNA objects
        self.area = area #This should be a number
        self.gridpoints = gridpoints #This is the Gridpoint currently holding the Droplet.
        self.index = index #This is the Droplet's index in the master list.
        self.to_delete = False #Toggle this on to let the Lab know to remove this Droplet from the list.
        self.skip_over = False #Toggle this on to skip over the droplet during the Move() checks.
        
        #Routing variables for Comp v1 (Some of these are shared by the other routers as well)
        self.following = None #The droplet that this droplet is chasing, if any
        self.dest = dest #The destination of this droplet, if any. Should be passed as a tuple to __init__
        self.sub_dest = None #The sub-destination of the droplet, used for simulations where the droplets don't necessarily move exactly one grid-step in exactly one time-step.
        self.collision_group = [self] #The allowed-collision group of this droplet, if any
        self.steps = [] #Tracks the history of this droplet's movements
        self.key = key  #records the key associated with this droplet
        self.node = node #records the node that pulled this droplet
        self.assigned = False #Records whether this droplet has been assigned to a node yet
        self.shunting = False #Indicates whether the droplet is shunting 
        self.moving = False #Tracks whether the droplet is moving yet this round.
        self.blocked_by = [] #Tracks the droplet(s) that blocked this droplet's optimal movements last round.
        self.targets = [] #Tracks the droplet's targeted gridpoints for this round of movement.
        self.occluded = [] #Tracks the gridpoints occluded by the droplet. 
        self.direction = None #Tracks the direction this droplet travelled last, 'N', 'S', 'E', 'W'
        self.merges = 0 #Tracks how many merges this droplet has been involved in

        #Routing variables for Coop routing v1 and v2
        self.locked = False #Indicates that the droplet is locked in place and can't move due to an ongoing chemical process. Used in the cooperative router. 
        self.route = []     #For planning the route in cooperative routing version 2
        self.blocked = []   #For tracking blocked coordinates along the droplet's route in 3D (time, space, space)
        self.perm_blocked = [] #For tracking 2D coordinates that are permanently blockded along this droplet's route
        self.last_routed = -1 #Last time this droplet's route was set.
        self.delayed_by = None #Which droplet is delaying this droplet's route to destination
        self.delay_amount = 0 #Amount by which droplet was delayed last time it routed
        self.reference_path = [] #Reference path for path heuristic
        self.cannot_route = False #If it can't currently route
        self.prev_perm_blocked = [] #Last time's perm blocked, for comparing routability
    
    #### ROUTING METHODS ####    

    def Get_Key(self):
        self.key = [str(x) for x in self.species]
        self.key.sort()
        self.key = tuple(self.key)
        return self.key
    
    def Is_Routed(self):
        #Returns true is the droplet has a nonempty route.
        return self.route != []
    
        #Returns True if the droplet has a route planned and it coincides with the current destination
        # return self.route != [] and self.Get_Dest() == self.route[-1][1:]
    
    def Set_Route(self, route, blocked=[], perm_blocked=[], time = None):
        #Set the droplet route and record where its temporary and permanent blocks are.
        #Also record what time the route was set at.
        self.route = route
        self.routed = True
        self.last_routed = time
        
    def Set_Blocks(self, blocked=[], perm_blocked=[]):
        #Record the blocks this droplet faces on its route.
        self.blocked = blocked
        self.perm_blocked = perm_blocked
    
    def Set_Dest(self, dest, shunting=False):
        #Record the destination.
        self.dest = dest
        self.shunting = shunting
        self.routed = False
        
    def Set_Collision_Group(self, group):
        #Set the collision group.
        self.collision_group = group
    
    def Set_Follow(self, dp):
        #Record which droplet this droplet is following. 
        #Not used in current version 11/11/21
        self.following = dp
        if dp is not None:
            self.Set_Dest(dp.Get_Loc())
            
    def Get_Dest(self):
        #Updates and returns the destination of the droplet            
        
        #Update the destination if it's following a droplet
        if self.following:
            if self.following.targets:
                self.Set_Dest(self.following.targets[0]) #Set the destination as the followed droplet's target for this round if possible
            else:
                self.Set_Dest(self.following.Get_Loc())
        elif self.dest is None:
            self.Set_Dest(self.Get_Loc())
            
        #return the dest
        return self.dest
        
    def At_Dest(self):
        #Check if the droplet is centered at its destination and has no ongoing route planned
        return (self.Get_Loc() == self.Get_Dest()) and not self.Is_Routed()
    
    def Get_Route(self):
        return self.route
    
    def Get_Shape(self, group_total = False):
        #Returns the shape of the droplet if group_total is False, else the shape of the droplet's entire collision group once merged
        if group_total:
            area = sum(dp.area for dp in self.collision_group)
        else:
            area = self.area
        return Calculate_Shape(area)
    
    def Get_Shell(self, group_total = False):
        #Returns the occlusion shell of the droplet if group_total is False, else the shape of the droplet's entire collision group once merged
        if group_total:
            area = sum(dp.area for dp in self.collision_group)
        else:
            area = self.area
        return Calculate_Shell(area)
    
    def Get_Shadow(self, region='edge', asindex = False):
        #Returns a list of indices or gridpoints for either the edge or non-edge gridpoints that the droplet touches.
        shape = self.Get_Shape()
        
        if region == 'edge':
            #Find all gps in the droplet's list that have at least one neighbor that is NOT in the droplet's list.
            #Note that this will include the center gridpoint if the droplet is too small to reach past its corners.
            # out = [(x,y) for (x,y) in shape if any((x+X, y+Y) not in self.gridpoints for X in [-1, 0, 1] for Y in [-1, 0, 1])]
            out = [gp for gp in self.gridpoints if any(ogp not in self.gridpoints for ogp in gp.neighbors)]
        
        elif region == 'interior':
            #Find all gps in the droplet's list that have NO neighbors that are outside of the droplet.
            # out = [(x,y) for (x,y) in shape if (all((x+X, y+Y) in self.gridpoints for X in [-1, 0, 1] for Y in [-1, 0, 1])]
            out = [gp for gp in self.gridpoints if all(ogp in self.gridpoints for ogp in gp.neighbors) and len(gp.neighbors) == 8]
            
            #If the droplet is small enough that even the center gridpoint counts as an 'edge',
            #then manually include it.
            if out == []:
                out = [x for x in self.gridpoints if x.indices == self.Get_Loc()]
        
        if asindex:
            return [x.indices for x in out]
        return out

    #### MOVEMENT AND CHEMISTRY METHODS ####
    def Get_Radius(self):
        #Returns the radius of the droplet
        return np.sqrt(self.area/np.pi)
    
    def Get_Loc(self, asindex = False):
        return tuple(np.floor(self.coords).astype('int'))
        
    def React(self, inst):
        #Instructions are passed as a dictionary.
        #Instruction dictionaries have three keys: 
            #'inst_type' - the name of the instruction, which also encodes its expected outcome
            #'reactants' - the necessary non-DNA reactants
            #'args' - additional args that may be necessary depending on the reaction type
            
        #If reactants are requied and any of them are missing
        if inst['reactants'] and any([x not in self.species for x in inst['reactants']]):
            raise ValueError('Missing reactant for instruction set: ' + inst['inst_type'])
        else:
            #If the reaction succeeds, first consume the reactants.
            #Note that the 'reactants' means only the non-DNA type chemicals
            #such as gibson mix, PCR mix, etc.
            if inst['reactants']:
                for x in inst['reactants']:
                    self.species.remove(x)
            
            #Now check the reaction type and act accordingly.
            if inst['inst_type'] == 'Gibson':
                self.Gibson(inst['args'])
                #Temporarily, I"ll add Purify to the Gibson commands just to simply debugging
                self.Purify('longest')
            elif inst['inst_type'] == 'PCR':
                self.PCR(inst['args'])
            elif inst['inst_type'] == 'Purify':
                self.Purify(inst['args'])
                
    def Gibson(self, args = None):
        #Attempts to assemble the DNA strands in this droplet by hybridizing their overhanging strands.
        counter = 0
        no_match_found = False
        while (counter < 3) and (not no_match_found):
            #Get the DNA objects in this droplet's species list
            dna_list = [x for x in self.species if type(x) is not str]
            
            no_match_found = True #Update the end conditions
            counter += 1
            
            #Attempt to match them.
            for i, dna1 in enumerate(dna_list):
                for dna2 in dna_list[i:]:
                    match = dna1.Match(dna2)
                    
                    #If they have a match, make a new combined strand and add it to this Droplet.
                    if match:
                        no_match_found = False #Since a match was found, reset the end condition
                        new_dna_list = dna1.Combine(dna2, side=match)
                        for new_dna in new_dna_list:
                            if new_dna not in self.species:
                                # print("Adding {} to species list: {}".format(new_dna, self.species))
                                self.species.append(new_dna)

    def PCR(self, args = None):
        #Multiplies a particular DNA strand in this droplet, if present. I need to account for
        #the ability to select a specific droplet.
        pass
    
    def Purify(self, args):
        #Purifies the DNA strands in the droplet.
        
        #If args is 'longest', select the longest strand and remove all others.
        if args == 'longest':
            #Find the length of the longest sequence
            try:
                desired_length = max([len(x.seq) for x in self.species if type(x) is not str])
            except ValueError as e:
                print(self.index)
                raise e
        else:
            desired_length = args
            
        #Get a list of all sequences that are NOT of the correct length
        non_matches = [x for x in self.species if type(x) is not str and len(x.seq) != desired_length]
        
        #Delete all of them
        for x in non_matches:
            self.species.remove(x)
            
    def Move(self, grid, time = None):     
        #Handles the movement of the droplet in coordination with the gridpoint objects.
        #Checks for a number of activated gridpoints within range equal to the droplet's
        #area. If such a set exists, move the droplet to them. 
        #If none exist, does not move.
        
        #Check to see if we're supposed to skip this droplet,
        #due to it already being processed during a merger with an earlier
        #droplet.
        #If so, reset the skip tracker and skip return without doing any calculations.
        if self.skip_over:
            self.skip_over = False
            return

        #Find out where the droplet is moving to
        current_coords = self.coords
        self.coords = self.Find_Gradient()
                
        try:
            if self.route != []:
                step = self.route.pop(0)[1:]
            # assert self.route == [] or self.Get_Loc() == step
        except AssertionError as e:
            print("Droplet number {} carrying {} strayed from its route onto site {} instead of {}.".format(self.index, self.species, self.Get_Loc(), step))
            raise e
            
        #If it's not moving, don't update its gridpoints.
        if np.array_equal(current_coords, self.coords):
            return
        
        #Find out what gridpoints the droplet now occupies and record them  
        self.Update_Gridpoints(grid, time = time)        

    
    def Find_Gradient(self, compass = True):
        #Overly simplified version of the function that used to calculate movement based on
        #vectors pointing towards activated gridspaces from the droplet's center.
        #Now it just checks the droplet's chosen direction and assumes one step of movement that way.
        
        #Find all active gps on the edge of the droplet. Ignore those fully inside the droplet.
        edge_gps = self.Get_Shadow(region='edge')
        active_gps = [gp for gp in edge_gps if gp.potential > 0]
        
        #Double-check to see if any droplets in different merge groups have activated any of the active gps
        if any(odp.collision_group is not self.collision_group for gp in active_gps for odp in gp.droplets):
            raise ValueError('Droplet {} at gridpoint {} detecting activation by another droplet of different collision group!'.format(self.index, self.Get_Loc()))

        if active_gps:
            #Get a list of vectors pointing from the droplet's center toward the active gps
            # arrays = [gp.coords - self.Get_Loc() for gp in active_gps]
            arrays = [gp.coords - self.coords for gp in active_gps]
            
            #Ignore zero-arrays
            #If it's just the center gridpoint that activated, do nothing.
            arrays = [x for x in arrays if not np.array_equal(x, (0,0))]
            if all(np.array_equal(x, np.array([0.0,0.0])) for x in arrays):
                return self.coords
            
            #Normalize the vectors and take the mean
            unit_arrays = [x/np.linalg.norm(x) for x in arrays]
            direction = np.array(np.mean(unit_arrays, axis=0))
            
            #For a simple heuristic, we'll correct any slight deviations from the four cardinal directions
            if compass:
                s2 = 1/np.sqrt(2)
                direction = np.sign(max([np.array([1,0]), np.array([s2,s2]), np.array([0,1]), np.array([-s2, s2]), np.array([-1,0]),np.array([-s2, -s2]), np.array([0,-1]), np.array([s2, -s2])], key = lambda x: np.dot(x, direction)))
            
            return self.coords + direction
        else:
            return self.coords
            
    
    def Clear_Gridpoints(self):
        #Clears all gridpoint occupation/occlusion data from self and gridpoints.
        #Does NOT clear gridpoint target data.
        for gp in self.gridpoints:
            gp.Remove_Droplet(self)
        self.gridpoints = []
        
        for gp in self.occluded:
            gp.occluded_by.remove(self)
        self.occluded = []
        
    def Update_Gridpoints(self, grid, time = None, moving = True):
        #Updates the list of gridpoints occupied by this droplet using the 
        #recorded center coordinate.
        #Also checks the new occlusion zone and looks for droplet mergers
        
        #Clear the current occupied gridpoint data        
        self.Clear_Gridpoints()
        
        #Run a search that fills in all the occupied gridpoints
        x,y = self.Get_Loc()
        shape_gps = [grid[(x + loc[0], y + loc[1])] for loc in self.Get_Shape() if (x + loc[0], y + loc[1]) in grid]
        shell_gps = [grid[(x + loc[0], y + loc[1])] for loc in self.Get_Shell() if (x + loc[0], y + loc[1]) in grid]
        
        for gp in shape_gps:
            #Check if the return value from Add_Droplet is something besides None
            #If so, a merger happened and Update_Gridpoint was re-called during the merger.
            #Therefore, end the current call.
            if gp.Add_Droplet(self, grid, time, moving):
                return
            
        #Now record the occluded gridpoints
        for gp in shell_gps:
            self.occluded.append(gp)
            gp.occluded_by.append(self)
        
        #### #### This version is for more flexible droplets, uses a Dijkstra-like neighbor-searching algorithm to fill in gridpoints
        # gps_to_check = [grid[self.Get_Loc()]]
        # gps_already_checked = []
        # while gps_to_check != [] and not self.to_delete:
        #     gp = gps_to_check.pop()
        #     gps_already_checked.append(gp)
        #     if self in gp.droplets:
        #         raise ValueError(gp.indices, self.index)
            
        #     #If the droplet touches the gridpoint in question, add it to the gridpoint object
        #     #Then add the gridpoint's unchecked neighbors to the to_check list
        #     if gp.Is_Touched_By(self):
        #         #Check if the return value from Add_Droplet is something besides None
        #         #If so, a merger happened and Update_Gridpoint was re-called during the merger.
        #         #Therefore, end the current call.
        #         if gp.Add_Droplet(self, grid, time, moving):
        #             return
                
        #         #Add all un-checked neighboring gridpoints to the list
        #         gps_to_check += [ogp for ogp in gp.neighbors if (ogp not in gps_already_checked) and (ogp not in gps_to_check)]
            
        #     #If the droplet doesn't touch this gridpoint, it is only occluded by the droplet.
        #     else:
        #         self.occluded.append(gp)
        #         gp.occluded_by.append(self)
    
    def Combine(self, droplet, grid, time = None):
        #Concatenate the species lists, then mark the other droplet for removal.

        #However, use the younger droplet (as indicated by its index in the master list)
        #This ensures that when droplets merge, the resulting droplet is based on the age of the
        #younger of the two. 
        #Thus, when looping over the master list in order, 
        #the older a droplet is/the longer it's been since it merged, 
        #the closer to the front of the list it will be. This gives it priority in routing.

        if self.index < droplet.index:        
            #Make sure this droplet is in its updated position for this time-step
            droplet.coords = droplet.Find_Gradient(compass = False)
            droplet.skip_over = True
            return droplet.Combine(self, grid, time)
            
                        
        if self.collision_group is not droplet.collision_group:
            raise IndexError("Warning: Two droplets of different collision groups merging. Indices {}, {}. Species {}, {}".format(self.index, droplet.index, self.species, droplet.species))
            
        self.merges += (1 + droplet.merges)
        self.species += droplet.species
        droplet.to_delete = True 
                
        #Estimate the new droplet center as the weighted average of the two droplets' centers
        self.coords = np.average([self.coords, droplet.coords], weights = [self.area, droplet.area], axis=0)
        
        #Find the nearest gridpoint center by rounding down, then shift the droplet to that location.
        self.coords = np.array(self.Get_Loc()) + (0.5, 0.5)       
        
        #Combine the volumes/areas of the two droplets
        self.area += droplet.area  
        
        #Now clean out the gridpoint containers for the other droplet
        droplet.Clear_Gridpoints()
        
        #And then re-update this droplet's gridpoints
        self.Update_Gridpoints(grid, time)
        
        #One of the droplet should have an empty route (be stationary) while the other still has a few steps to go.
        #Make sure the new droplet takes over the non-empty route so it doesn't get stranded. 
        if self.route == [] and droplet.route != []:
            self.route = copy.copy(droplet.route)
            
        #If this Combine call was made recursively, we need to pop the last step from the route
        if self.route[0][0] == time:
            self.route.pop(0)
        
        return self
            
    def Get_Circle(self, zorder = 10):
        #Returns a matplotlib Circle artist representing this droplet.
        circ = plt.Circle(self.coords, self.Get_Radius(), edgecolor = (0,0,0), zorder = zorder)
        if self.shunting or (self.route != [] and self.route[-1][1:] != self.Get_Dest()):
            circ.set_color((0.3, 0.05, 0.65))
        return circ
            
        #The color varies depending on the status of the droplet.
            #If it's a mixed droplet, red.
            #If it's a non-DNA singlet, green.
            #If it's a DNA singlet, black.
            #If it's not at its destination, a lighter version of its base color.

        
        if len(self.species) > 1:
            if self.At_Dest():
                circ.set_color((1, 0, 0))
            else:
                circ.set_color((1, 0.8, 0.8))
        elif type(self.species[0]) == str:
            if self.At_Dest():
                circ.set_color((0, 1, 0))
            else:
                circ.set_color((0.8, 1, 0.8))
        else:
            if self.At_Dest():
                circ.set_color((0, 0, 0))
            else:
                circ.set_color((0.5, 0.5, 0.5))
            
        return circ
   
class DNA():
    #A chemical species consisting of a double-strand of DNA,
    #and overhangs on the left and right.
    
    def __init__(self, seq, left, right):
        self.seq = seq   #The sequence of this DNA as a string (only the 'top' strand for simplicity)
        self.left = left #The left overhang string
        self.right = right#The right overhang string
        self.match_dict = {'A':'T', 'T':'A', 'G':'C', 'C':'G', '1':'1', '0':'0'} #Watson-Crick pairing dict
        self.to_delete = False   #In case this needs to be marked for deletion later
        
    def Match(self, DNA):
        #Checks to see if this object's overhangs match with another's.
        #Returns either None, 'left', 'right' or 'both' indicating no match, or a match on the left and/or right of this object's overhangs.
        #Check for a left match
        try:
            left = all([self.match_dict[self.left[i]] == DNA.right[i] for i in range(max(len(DNA.right),len(self.left)))])
        except IndexError:
            left = False
            
        #Check for a right match
        try:
            right = all([self.match_dict[self.right[i]] == DNA.left[i] for i in range(max(len(DNA.left),len(self.right)))])
        except IndexError:
            right = False
            
        #Return the outcome
        if left and right:
            return 'both'
        elif left:
            return 'left'
        elif right:
            return 'right'
        else:
            return None
        
    def Combine(self, dna, side):
        #Makes a new DNA object by combining the data of this one and another.
        #I arbitrarily decide that the right-hand overhang is the 'top' strand,
        #so it gets added to the sequence upon a successful match.
        

        if side == 'left':
            new = [DNA(seq = (dna.seq + self.seq), left = dna.left, right = self.right)]
        elif side == 'right':
            new = [DNA(seq = (self.seq + dna.seq), left = self.left, right = dna.right)]
        elif side == 'both':
            new = [DNA(seq = (dna.seq + self.seq), left = dna.left, right = self.right), 
                   DNA(seq = (self.seq + dna.seq), left = self.left, right = dna.right)]
            
        else:
            new = None
            
        return new
    
    def __str__(self):
        return str(self.seq)
    
    def __repr__(self):
        return str(self.seq)
    
    def __eq__(self, other):
        if type(self) == type(other):
            return (self.left == other.left) and (self.seq == other.seq) and (self.right == other.right)
        else:
            return False
        
class Gridpoint():
    #This object represents a single Gridpoint.
    #It may be only an electrostatic control point, or it may have mixing
    #and heating protocols available as well.
    #Has methods for updating current commands, creating droplets, checking for droplets that are 
    #moving over this gridpoint or colliding on it, setting the electric potential, etc.
    
    def __init__(self, gridpoint_size, indices, pull_type = None, pull_data = None, grid_dim = None, neighbors = None):
        #Variables that store information about the gridpoint
        self.state_inst = None #These are the instructions currently under execution.
        self.runtime = None #This is the remaining runtime of the current instructions.
        self.droplets = [] #The list of droplets currently touching thed Gridpoint, if any.
        self.inst_types = ['ES'] #The list of functions this gridpoint is allowed to perform.
        self.pull_data = pull_data #Data about the type of droplet this gridpoint can pull from a reservoir, if any.
        self.residues = [] #A list of the residue species in the Gridpoint.
        self.in_process = False #Tracks whether the Gridpoint is in the middle of executing a function.
        self.potential = 0 #Electrostatic potential
        self.indices = indices #This Gridpoint's indices in the lab's dictionary
        self.gridpoint_size = gridpoint_size #This Gridpoint's length (and width, assuming a square shape)
        self.coords = gridpoint_size*(np.array(indices) + 1/2)
        self.neighbors = neighbors #A list of neighboring gridpoints
        self.reactions = 0
        
        #Variables for routing purposes
        self.occluded_by = [] #Indicates which droplets are neighboring this gridpoint, rendering it off-limits temporarily for most other droplets
        self.is_forbidden = False #Indicates that this gridpoint has been declared off-limits for all droplets
        self.selected_by = None #Indicates which node has selected this gridpoint, if any.
        self.pulled_by = None #Indicates which node is pulling at this gridpoint, if any.
        self.targeted_by = None #Indicates which droplet is targeting this gridpoint for movement, if any.

    def Initialize_Neighbors(self, grid):
        #Used by default to set all gridpoints with neighboring indices as the neighbors of this gridpoint
        indices = np.array(self.indices)
        self.neighbors = [grid[tuple(indices + [x,y])] for x in [-1, 0, 1] for y in [-1, 0, 1] if (not x == y == 0) and (tuple(indices + [x,y]) in grid)]
        
    def Is_Forbidden(self, dp = None, allowed_droplets = None, node = None, include_occluded=True):
        #Returns True if this gridpoint is forbidden to the input for any reason.
        if self.is_forbidden:
            return True, [None]
                
        #There will be three cases. 
        #Either dp is given,
        #or allowed_droplets and Node are given,
        #or none of them are.
        blocker_droplets = self.droplets + self.occluded_by + [self.targeted_by]

        if None in blocker_droplets:
            blocker_droplets.remove(None)
            
        if dp:
            if ((self.selected_by not in [None, dp.node]) or #If it's been selected by another node
                (self.droplets != [] and any(x.collision_group is not dp.collision_group for x in self.droplets)) or #If it's occupied by a droplet not in the same collision group
                (self.droplets != [] and any(x.moving for x in self.droplets)) or #If it's occupied by a droplet that's already moving this round
                (self.targeted_by is not None and self.targeted_by.collision_group is not dp.collision_group) or #If it's targeted by a droplet not in the same collision group
                (self.pulled_by is not None) or #If it's been selected for pulling by ANY node
                (include_occluded and any(odp.collision_group is not dp.collision_group for odp in self.occluded_by))): #If it's occluded by a droplet not in the same collision group
                    return True, blocker_droplets
        
        elif (allowed_droplets) and (node):
            if ((self.selected_by not in [None, node]) or
                (self.droplets != [] and any(x not in allowed_droplets for x in self.droplets)) or
                (self.droplets != [] and any(x.moving for x in self.droplets)) or
                (self.targeted_by is not None and self.targeted_by not in allowed_droplets) or
                (include_occluded and any(x not in allowed_droplets for x in self.occluded_by)) or
                (self.pulled_by is not None)):
                return True, blocker_droplets
        else:
            if ((self.selected_by is not None) or
                (self.droplets != []) or
                (self.targeted_by is not None) or
                (include_occluded and self.occluded_by != []) or
                (self.pulled_by is not None)):
                return True, blocker_droplets
        
        #If none of the conditions are met, return False
        return False, [None]
    
    def Is_Touched_By(self, dp):
        #Returns 1 if droplet dp touches this gridpoint, 0 otherwise.
        #This is determined by checking two conditions:
            #The center of the droplet is inside the gridpoint, or outside but within (radius) of an edge
            #The center of the droplet is within (radius) of one of the corners
            
        a,b = dp.Get_Loc()    
        r = dp.Get_Radius()
        x0,y0 = self.indices
        x1,y1 = x0 + self.gridpoint_size, y0 + self.gridpoint_size
        
        #Case 1, the center of the droplet is inside the gridpoint or within (radius) of an edge
        if ((x0 - r <= a <= x1 + r) and (y0 <= b <= y1)) or ((x0 <= a <= x1) and (y0 - r <= b <= y1 + r)):
            return True

        #Case 2, the center of the droplet is within radius of a corner
        return any(Cartesian_Dist((a,b), Z) <= r for Z in [(x0,y0), (x1,y0), (x0,y1), (x1,y1)])
    
    def Set_Forbidden(self, boolean):
        self.is_forbidden = boolean
        
    def Update_Inst(self, state_inst):
        #Check to be sure that the Gridpoint isn't currently executing some instructions
        #before setting a new instruction (unless it's None).
        if (self.state_inst is not None) and (state_inst is not None):
            raise ValueError('Gridpoint has not finished executing instructions before adding new commands!')
            
        if state_inst is None:
            self.in_process = False
            self.runtime = None
            self.state_inst = None
        else:
            #Throw an error if this gridpoint is not allowed to execute that instruction type.
            if state_inst['inst_type'] not in self.inst_types:
                raise ValueError('Gridpoint {} is not equipped to perform instruction of type '.format(self.indices) + state_inst['inst_type'] + '!')
            
            #If it passed all of the checks, update the instructions
            self.state_inst = state_inst
            
            #If the new instructions are not empty, reset the in_progress tracker
            #and the runtime
            self.in_process = True
            self.runtime = state_inst['runtime']
    
            if self.droplets is []:
                print('Warning: Empty Gridpoint has begun executing instructions!')
        
    def Advance(self):
        #Decrement the runtime variable.
        if self.runtime is not None:
            self.runtime -= 1
            #If runtime has completed, Convert the Droplet and clear the instructions
            if self.runtime == 0:
                self.in_process = False
                self.runtime = None
                if self.droplets != []:
                    if len(self.droplets) != 1:
                        raise ValueError('Gridpoint {} executed instructions while containing multiple separate droplets!'.format(self.indices))
                    self.droplets[0].React(self.state_inst)
                    self.reactions += 1
                else:
                    print('Warning: Empty Gridpoint finished executing instructions!')
                self.Update_Inst(None)
    
    def Set_Inst_Types(self, inst_types):
        self.inst_types = inst_types
    
    def Append_Inst_Types(self, inst_type):
        if inst_type not in self.inst_types:
            self.inst_types.append(inst_type)
        
    def Pull_Droplet(self, index, node = None, key = None, grid = None):
        if self.pull_data['type'] == 'DNA':
            species = DNA(seq = self.pull_data['species'], left = self.pull_data['ends'][0], right = self.pull_data['ends'][1])
        else:
            species = self.pull_data['species']
        
        #Instantiate a new Droplet
        droplet = Droplet(self.coords, species, self.pull_data['area'], gridpoints = [], index = index, key = key, node = node)
        
        #Add the new Droplet to this Gridpoint and any others it touches
        droplet.Update_Gridpoints(grid = grid, moving = False)
        
        #Return the new Droplet object so the Lab can append it to the list.
        return droplet
    
    def Set_Pull_Data(self, data):
        #Record the data
        self.pull_data = data
        
        #Now that this gridpoint can Pull, add it to the instruction list.
        self.Append_Inst_Types('Pull')
    
    def Add_Droplet(self, droplet, grid, time = None, moving = True):
        #Adds the droplet to the gridpoint and handles merging it with the
        #existing droplet, if there is one.
        #If a merge occurred, returns True, otherwise False
        
        #Throw an error if the Gridpoint is in the process of executing a function.
        if self.in_process:
            raise ValueError('Attempted to add droplet number {} carrying {} to Gridpoint mid-execution!'.format(droplet.index, droplet.species))
            
        if self.occluded_by != [] and any(x.collision_group is not droplet.collision_group for x in self.occluded_by):
            # raise ValueError('Droplet number {} carrying {} moving into gridpoint {} occluded by droplet(s) from other merge group(s)!'.format(droplet.index, droplet.species, self.indices))
            # print('Warning! At time {}, droplet number {} carrying {} moving into gridpoint {} occluded by droplet(s) from other merge group(s)!'.format(time, droplet.index, droplet.species, self.indices))
            pass
        #If it's a new droplet being pulled, it shouldn't be sharing the gridpoint with any other droplets
        if (not moving) and self.droplets != []:
                raise ValueError('Droplet carrying {} pulled at NON-EMPTY gridpoint {}!'.format(droplet.species, self.indices))
        
        #Raise an error if any of the current droplets don't share the new droplet's collision group
        if any(x.collision_group is not droplet.collision_group for x in self.droplets):
            # raise ValueError('Droplet {} carrying {} joined gridpoint {} with another droplet of a different collision group!'.format(droplet.index, droplet.species, self.indices))
            print('WARNING! Droplet {} carrying {} joined gridpoint {} at time {} with another droplet of a different collision group! No collision detected, safe to continue.'.format(droplet.index, droplet.species, self.indices, time))
        
        #Update the mutual droplet and gridpoint containers
        droplet.gridpoints.append(self)
        self.droplets.append(droplet)
            
        #Update the residues list
        self.Add_Residue(droplet.species)
        
        #Find which, if any, occupying droplets will merge with the new droplet
        mergers = [x for x in self.droplets if x is not droplet and Cartesian_Dist(x.Get_Loc(), droplet.Get_Loc()) <= x.Get_Radius() + droplet.Get_Radius()]
        
        #If there are no mergers, add the droplet and end the call by returning False
        if mergers == []:
            return False
        
        #Otherwise, run the mergers and return True
        for x in mergers:
            droplet = droplet.Combine(x, grid, time)
        
        return True
            
            
    def Remove_Droplet(self, dp):
        self.droplets.remove(dp)
    
    def Clean_Residues(self):
        self.residues = []
        
    def Set_Potential(self, potential):
        self.potential = potential
        
    def Add_Residue(self, species):
        if species not in self.residues:
            self.residues.append(species)
            
    def Get_Square(self, color = (0, 0, 1), zorder = 1):
        #Returns a pyplot Rectangle object representing this gridpoint. Default color is blue.
        center = np.array(self.coords) - 2*[float(self.gridpoint_size)/2]
        square = plt.Rectangle(center, self.gridpoint_size, self.gridpoint_size, fc = color, ec = 'black', zorder = zorder)
        return square

def Get_Neighbors(indices_or_coords, grid_dim, include_loc = False, astuple = False, include_extremes = False):
    #Returns neighboring coordinates in a list
    try:
        if indices_or_coords in [None, False, []]:
            return []
    except ValueError:
        pass
    
    #Convert to np array for convenience
    x = np.array(indices_or_coords)
    directions = [np.array([1,1]), np.array([1,0]), np.array([1,-1]), np.array([0,-1]), np.array([-1,-1]), np.array([-1,0]), np.array([-1,1]), np.array([0,1])]
    
    #Include all neighboring coordinates that aren't outside of the lab grid
    if astuple:
        out = [tuple(x + vec) for vec in directions if (x + vec >= 0).all() and (x + vec < grid_dim).all()]
        if include_loc:
            out.append(indices_or_coords)
        if include_extremes:
            out += [tuple(x + np.array([i,j])) for i in [-2,0,2] for j in [-2,0,2] if i*j == 0 and i != j]
    else:
        out = [x + vec for vec in directions if (x + vec >= 0).all() and (x + vec < grid_dim).all()]
        if include_loc:
            out.append(x)
        if include_extremes:
            out += [x + np.array([i,j]) for i in [-2,0,2] for j in [-2,0,2] if i*j == 0 and i != j]
        
    return out #Return a list of coords surrounding the given coords.

def Plot_Droplets(lab, ax=None, wait_time = 0, step=None, saveplot = False, name_str = 'Fig'):    
    if ax == None:
        fig, ax = plt.subplots()
        
    ax.clear() #Clear the axes object, then we'll repopulate it
    ax.set_xlim([0, lab.grid_dim[0]])
    ax.set_ylim([0, lab.grid_dim[1]])

    if step is not None:
        ax.set_title(f'Lab time: {step}, Congestion: {round(lab.Get_Congestion(0, 0), 3)}')
        
    #Loop through the droplets and plot all the occlusion boxes
    for dp in lab.droplets:
        #Add a circle representing the droplet itself
        ax.add_artist(dp.Get_Circle(zorder = 20))
        x,y = dp.coords
        ax.text(x-0.5,y+0.7,dp.species,color='red', zorder = 100)
        
        #Add the droplet's route in gray boxes
        if dp.Is_Routed():
            [ax.add_artist(lab.grid[x[1:3]].Get_Square(color=(0.5, 0.5, 0.5), zorder=1)) for x in dp.route]
       
        #Add the occupied and occluded gridpoints as yellow and blue boxes, respectively.
        [ax.add_artist(gp.Get_Square(color = (1,1,0), zorder = 10)) for gp in dp.gridpoints];
        [ax.add_artist(gp.Get_Square(zorder = 15)) for gp in dp.occluded];
        
        #If it has a destination, draw that as a red box and an arrow pointing to it.
        if dp.Get_Dest():
            ax.add_artist(lab.grid[dp.Get_Dest()].Get_Square(color=(1,0,0), zorder = 1))
            ax.add_artist(plt.arrow(*dp.coords, *(np.array(dp.Get_Dest()) - dp.Get_Loc()), zorder = 25))
            
    #For any active gridpoints, color them orange.
    for gp in lab.grid.values():
        if gp.is_forbidden:
            ax.add_artist(gp.Get_Square(color=(0,0,0), zorder=30))
            continue
        if gp.potential > 0:
            # ax.add_artist(gp.Get_Square(color=(1, 0.64, 0), zorder = 18))
            # ax.add_artist(gp.Get_Square(color=(1, 0.64, 0), zorder = 50))
            pass
        
        
    if saveplot:
        plt.savefig('Figures/' + name_str + str(step) + '.png')

    if wait_time > 0:
        plt.pause(wait_time)
    return ax
        
class Dummy():
    def __init__(self, coords = None, dest = None, targets = [], area = 1):
        self.coords = coords
        self.dest = dest
        self.targets = targets
        self.collision_group = []
        self.area = area
        self.route = []
        
    def Set_Route(self, route):
        self.route = route
        
    def Get_Loc(self):
        return self.coords
    
    def Get_Dest(self):
        return self.dest
    
    def Get_Radius(self):
        return np.sqrt(self.area/np.pi)
    
    def Test(self, x):
        Dummy.Test.thing = x
        print(self.Test.thing)
             
def Calculate_Shape(area):
    #Gives a shape list from the radius of a droplet. 
    #Used for calculations based on as-of-yet non-instantiated droplets.
    if area in Calculate_Shape.shapes:
        return Calculate_Shape.shapes[area]
    
    rad = np.sqrt(area/np.pi)
    int_rad = int(np.ceil(rad))
    
    #Get a set of options in a square region of width 2*rad
    options = [(x, y) for x in range(-int_rad, int_rad+1) for y in range(-int_rad, int_rad+1)]
    shapelist = []
    
    #For each x0, y0 coordinate pair:
    for x0,y0 in options:
        x1, y1 = x0 + 1, y0 + 1
        
        #Is the center of the imaginary droplet within radius of an edge, or actually inside the gridpoint?
        if ((x0 - rad <= 0.5 <= x1 + rad) and (y0 <= 0.5 <= y1)) or ((x0 <= 0.5 <= x1) and (y0 - rad <= 0.5 <= y1 + rad)):
            shapelist.append((x0, y0))
        #Alternatively, is the imaginary droplet's center within radius of a corner of the gridpoint?
        elif any(Cartesian_Dist((0.5, 0.5), Z) <= rad for Z in [(x0,y0), (x0, y1), (x1, y0), (x1, y1)]):
            shapelist.append((x0, y0))
    
    Calculate_Shape.shapes[area] = shapelist
    
    return shapelist

Calculate_Shape.shapes = {} #Initialize the shape dict

def Calculate_Shell(area):
    if area in Calculate_Shell.shells:
        return Calculate_Shell.shells[area]
    shape = Calculate_Shape(area)        #Returns the occlusion shell of the droplet if group_total is False, else the shape of the droplet's entire collision group once merged
    shell = []
    for (x,y) in shape:
        #Append all neighbors (excluding diagonals) to any element in shape list, while avoiding duplicates
        [shell.append((x + X, y + Y)) for X in [-1, 0, 1] for Y in [-1, 0, 1] if (x + X, y + Y) not in shell + shape and X*Y == 0];
    
    Calculate_Shell.shells[area] = shell
    
    return shell

Calculate_Shell.shells = {} #Initialize the shell dict
    
def Cartesian_Dist(a,b):
    return np.linalg.norm(np.array(a) - np.array(b))
