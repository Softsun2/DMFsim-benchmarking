# -*- coding: utf-8 -*-
"""
11/11/21

@author: Andrew Stephan

The Scheduler object bridges the gap between the Interpreter and the Lab.
It is responsible for choosing when to create droplets, which destinations to assign them and when to perform chemical operations i.e. Gibson assembly.

It interfaces with the Nodes in the assembly tree and coordinates their activities, translating the instruction codes into actual Lab commands.

This is also where the AStar routing library is called.

"""
import time
import random
import numpy as np
import matplotlib.pyplot as plt
from AStar import Get_Route
from Lab import Calculate_Shape, Calculate_Shell
import time
import copy
from functools import reduce

class Scheduler():
    #Takes in grid data and a set of instruction nodes.
    #Turns the instructions into Lab commands. 
    
    def __init__(self, nodes, inst_locs, pull_data, lab, perm_forbidden = [], verbose = 1):
        # random.seed(42)
        self.nodes = nodes  #This is the instruction list provided by the Interpreter and Protocol.
        self.inst_locs = inst_locs #The locations where certain instructions can be executed.
        self.pull_data = pull_data #places where droplets can be pulled
        self.current_nodes = []
        self.perm_forbidden = perm_forbidden
        self.time = -1
        self.verbose = verbose
        self.astar_calls = 0
        self.move_calls = 0
        self.astar_visits = 0
        self.dest_sets = 0
        self.failed_routes = 0
        self.most_visits = 0
        self.no_progress_tracker = 0 #Tracks how long it has been since progress was made.
        
        #for debugging
        self.debug = None

        #Identify the router's attached lab and a few subordinate values as well
        self.lab = lab
        self.grid_dim = lab.grid_dim
        
        #Record all the locations of interest--droplet reservoirs, gibson sites etc.
        self.all_sites = reduce((lambda x, y: x[1:] + y[1:]), inst_locs) + [loc for key in pull_data for loc in pull_data[key]['loc']]

        #Record all the permanently forbidden gridpoints
        [self.lab.grid[x].Set_Forbidden(True) for x in perm_forbidden];

    def Compile_Instructions(self, num = 10000, makeplot = False, saveplot = False, wait_time = 2, version = 1):
        #This loops over the various levels of depths in the tree, starting from the 
        #level above the bottom (since all bottom nodes are leaf nodes)
        #It runs all of the nodes at a given depth in parallel. 
        ax = None
        start_time = time.time()
        if makeplot:
            plt.ion()
            fig, ax = plt.subplots()
            
        #Get the non-leaf nodes
        if version == 1:             #For the old version
            self.current_nodes = [x for x in self.nodes[1] if not x.Is_Leaf()]
        elif version == 2:           #For the new version
            self.current_nodes = [node for sublist in self.nodes for node in sublist if node.Is_Leaf()] 

        #Loop until the root node has concluded or until the num limit is reached
        while (time.time() - start_time < float('inf')) and (self.no_progress_tracker < float('inf')) and (self.time < num) and (not self.nodes[-1][-1].Concluded()):
        # while (time.time() - start_time < 600) and (self.no_progress_tracker < 500) and (self.time < num) and (not self.nodes[-1][-1].Concluded()):
            #Update the time tracker
            self.time += 1
            self.no_progress_tracker += 1
        
            #Check node progress
            for node in self.current_nodes:
                self.Check_Node_Progress(node)
                
            #Advance nodes to the next instruction if they're finished with the current one
            for node in self.current_nodes:
                self.Advance_Node_Instructions(node)

            #Plan the route for each droplet that isn't currently assigned a route and isn't locked in place for a chemical process I.E. gibson
            # self.Route_Droplets([x for x in self.lab.droplets if (x.route == []) and (not x.locked) and (not x.At_Dest())])
            self.Route_Droplets([x for x in self.lab.droplets if (not x.Is_Routed()) and (not x.locked) and (not x.At_Dest())])
            
            #Send one round of movement commands
            self.Send_Movement_Commands(makeplot=makeplot, saveplot=saveplot, wait_time=wait_time, ax=ax)
            
            #Update old keys and attach new ones
            self.Update_Keys()
            self.Attach_Keys()
             
            #Loop over the nodes and reset the pulling_sites data
            for node in self.current_nodes:
                for index in node.pulling_sites:
                    if index:
                        self.lab.grid[index].pulled_by = None
            
            #Check for sets of siblings that have all finished their work.
            #If there are any, add their parent to the current nodes list.
            new_nodes = []
            for node in self.current_nodes[:]:
                if not node.parent:
                    continue
                
                #Check if this node, and all of its siblings, have concluded.
                if all([(child.Concluded() and child in self.current_nodes) for child in node.parent.children]) and node.parent.children != []:
                    #If so, remove all of them from the list and add their parent instead.
                    new_nodes.append(node.parent)
                    
            #Add the new nodes to the current_nodes list, but avoid duplicates
            new_nodes = set(new_nodes)
            self.current_nodes += new_nodes
            
            #Remove the children of the new nodes from the current_nodes listt
            for n in new_nodes:
                for c in n.children:
                    #The parent inherits the childrens' selected sites (i.e. shunting sites)
                    c.Clear(grid=self.lab.grid, time=self.time, parent = n)
                    self.current_nodes.remove(c)            
        
        # while (time.time() - start_time < 600) and (self.no_progress_tracker < 500) and (self.time < num) and (not self.nodes[-1][-1].Concluded()):
        print('\nReason for exiting:')
        print('(time.time() - start_time < 600):', not (time.time() - start_time < 600))
        print('(self.no_progress_tracker < 500):', not (self.no_progress_tracker < 500))
        print('(self.time < num):', not (self.time < num))
        print('(not self.nodes[-1][-1].Concluded()):', not (not self.nodes[-1][-1].Concluded()))

    def Check_Node_Progress(self, node):
        #Checks on the node's progress in its current instruction.
        
        #If the node is pulling droplets, skip this check round
        if node.waiting:
            return
        
        #See if the node has only been initialized and hasn't run any instructions yet
        if node.inst_i == -1:
            #If so, check the child nodes and add their droplets.
            for key, dp in [(key, child.droplets[key]) for child in node.children for key in child.droplets]:
                node.droplets[key] = dp
                node.droplets[key].node = node  #Update the node reference to the parent node
        
        #Remove any droplets that aren't in the lab anymore
        poplist = []
        for key in node.droplets:
            if node.droplets[key] not in self.lab.droplets:
                poplist.append(key)
                
        for key in poplist: #You can't remove items from the dict while iterating over it.
            del node.droplets[key]
        
        #Does the node have a timer, and has the time come?
        if node.timer and node.timer <= self.time:
            self.lab.Add_Commands(dict()) #Add an empty dictionary to track the passage of time
            node.timer = 0  #Set the timer to 0 so the In_Progress function will know it's done
            
                
            #Shunt the inactive droplets.
            # self.Shunt(node, exclude_active=True)
    
    def Advance_Node_Instructions(self, node):
        #If the node has finished its current instruction, starts the next one
        
        #If has concluded all of its instructions, do nothing other than shunt its droplets away from crucial real estate
        if node.Concluded():
            self.Shunt(node, exclude_active=False)
            return
        
        #Has it just finished an instruction, or alternatively, is it currently pulling droplets?
        if node.inst_i == -1 or node.waiting or not node.In_Progress():    
                
            #If the node has newly-arrived at this step, update its instruction tracker.
            if not node.waiting:
                self.no_progress_tracker = 0
                node.inst_i += 1        #Increment the instruction index          
                node.Clear(grid=self.lab.grid, time=self.time)       #Also clear its selected sites, timer, etc.
                
                #Also reset all of the droplets' following values and shunting trackers
                for dp in node.droplets.values():
                    dp.following = None
            
            #Get the instruction
            inst = node.inst_list[node.inst_i] 
            
            #Break up the instruction data into the type and species list
            inst_type = inst[0]
            species_list = [list(node.droplets.keys())[x] if (type(x) == int) else tuple(x) for x in inst[1:]]  
            # if species_list[0] == ('0',):
            #     print('yes')
            #     species_list[0] == list(node.droplets.keys())[0]
                    
            #Add the species_list droplets to the actives list, if they exist
            #Otherwise they'll be added to the list when they get Pulled and Attached
            node.active_droplets += [node.droplets[key] for key in species_list if key in node.droplets and node.droplets[key] not in node.active_droplets] 

            #Pull the needed species if possible
            node.pulling_sites = []
            for x in species_list:
                if x not in node.droplets:
                    #Find the pull locationi
                    pair = self.Find_Pull_Options(x, node)
                    
                    #Get the radius and shape of the future droplet
                    radius = np.sqrt(self.pull_data[x[0]]['area']/np.pi)
                    # shape = Calculate_Shape(radius)
                    shape = Calculate_Shape(area=self.pull_data[x[0]]['area'])
                    
                    #Record the affected locations
                    self.Node_Pull(node, pair, shape)
            
            #If we're not finished pulling droplets, wait another round before advancing.
            if (node.pulling_sites != []) or any(not x.At_Dest() for x in node.droplets.values()):
                node.waiting = True
                #If any of the droplet pull locations couldn't be selected this round, shunt the other droplets, including active ones
                
                if not all(node.pulling_sites):
                    self.Shunt(node, exclude_active=False)
                return
            
            
            #If you make it this far, that means it's finally done pulling all the needed droplets
            #for this instruction. The pulling_sites list must be empty.
            node.waiting = False
            self.no_progress_tracker = 0
            
            #Go through the instruction options with an if-else stack
            if inst_type[-5:] == '_Move':
                #Unlike the other operation types, we don't immediately reset the no-progress counter here.
                #Instead, we wait and see if it's able to select a site first.
                
                #Identify the group of droplets
                dps = [node.droplets[key] for key in species_list]
                
                #Allow collisions within this group of droplets
                self.Allow_Collisions(dps)
                
                #Choose a site
                dest = self.Find_Work_Location(dps[0].Get_Loc(), inst_type[:-5], node, droplets=dps)
                
                #If no site viable site was found yet
                if not dest:
                    node.waiting = True
                    return
                
                #If you made it past the check above, move forward with the chosen site
                node.waiting = False
                
                #Find the net area and shape to block off for the conglomerate droplet at the chosen site
                tot_area = sum(dp.area for dp in dps)
                radius = np.sqrt(tot_area/np.pi)
                
                self.Node_Select(node, dest, Calculate_Shape(area=tot_area), Calculate_Shell(area=tot_area))
                
                #Set the droplets to move to the destination
                for dp in dps:
                    dp.Set_Dest(dest)
                    self.dest_sets += 1
                    # print("setting droplet {} destination t0 {}".format(dp.Get_Key(), dest))
                
                #To catch errors:
                if inst_type[:-5] not in ['Gibson', 'Purify', 'PCR']:
                    raise ValueError('Move-instruction type not "Gibson" or "Purify" or "PCR".')
                
            elif inst_type == 'Gibson':    
                #Recall the Gibson location by checking where the droplet is
                key = species_list[0]
                gibson_loc = node.droplets[key].Get_Loc()
                node.droplets[key].Set_Dest(gibson_loc)
                
                #Add the gibson command to the list at the relevant location
                gibson_dict = dict(inst_type = 'Gibson', runtime = 2, 
                                          reactants = ['gibson_mix'], args = None)
                self.lab.Add_Commands(dict(inst_indices = [gibson_loc], insts = [gibson_dict]))
                node.timer = self.time + 2
                
                #Lock the droplet in place
                node.droplets[key].locked = True
                
            elif inst_type == 'Purify':
                #Recall the purify location by checking where the droplet is
                key = species_list[0]
                purify_loc = node.droplets[key].Get_Loc()
                node.droplets[key].Set_Dest(purify_loc)
                
                #Add the purify command to the list at the relevant location
                purify_dict = dict(inst_type = 'Purify', runtime = 2,
                                   reactants = ['purify_mix'], args = 'longest')
                self.lab.Add_Commands(dict(inst_indices = [purify_loc], insts = [purify_dict]))
                
                #Set the node's timer
                node.timer = self.time + 2
                
                #Lock the droplet in place
                node.droplets[key].locked = True
                
            elif inst_type == 'PCR':
                #Recall the purify location by checking where the droplet is
                key = species_list[0]
                PCR_loc = node.droplets[key].Get_Loc()
                node.droplets[key].Set_Dest(PCR_loc)
                
                #Add the purify command to the list at the relevant location
                PCR_dict = dict(inst_type = 'PCR', runtime = 2,
                                   reactants = ['PCR_mix'], args = 'longest')
                self.lab.Add_Commands(dict(inst_indices = [PCR_loc], insts = [PCR_dict]))
                
                #Set the node's timer
                node.timer = self.time + 2
                
                #Lock the droplet in place
                node.droplets[key].locked = True
    
    def Route_Droplets(self, dps, step_limit = 5000):
        #Takes in a list of all droplets in the lab that are not currently locked and do NOT have a planned route.
        #Calls the AStar library to plan a complete route to the destination for each droplet, making using a 3D time-multiplexed A* method.
        #Priority is given to droplets based on their distance from their destination, in descending order.
        
        #Note that, unlike the older routing versions, very little special treatment is given to droplets in the same collision group.
        #The only difference in their treatment is that the current location of a droplet in the same collision group is excluded IF it is also at its destination.
        #This allows droplets that are meant to merge on the same site to come in one at a time and settle there, but they won't collide mid-route.
                
        #Get a set of the collision groups, but use shallow copies
        a = [copy.copy(dp.collision_group) for dp in dps]
        groups = []
        [groups.append(grp) for grp in a if grp not in groups];
        
        #Order the groups by max distance to destination within each group, descending
        groups.sort(key = lambda grp: max(Dist(dp.Get_Loc(), dp.Get_Dest()) for dp in grp if not dp.Is_Routed()), reverse=True)
        
        for grp in groups:
            #Order the droplets in the group by distance to destination, ascending.
            grp.sort(key = lambda dp: Dist(dp.Get_Loc(), dp.Get_Dest()))
            
            #Loop over the droplets in the group
            for index, dp in enumerate(grp):
                
                #Skip droplets that don't need to be routed right now
                if dp not in dps:
                    continue
                
                dp.delay_amount = 0
                first_or_2nd_route = 1
        
                #Get all the locations blocked by the routes of other droplets
                blocked = [(*x, odp) for odp in self.lab.droplets for step in odp.route for x in Get_Blocked(step, odp.Get_Shape(), odp.Get_Shell()) if odp is not dp]
                
                #Add the locations blocked by their starting locations, whether they're moving or not.
                blocked += [(*x, odp) for odp in self.lab.droplets for x in Get_Blocked((self.time, *odp.Get_Loc()), odp.Get_Shape(), odp.Get_Shell()) if odp is not dp]
                
                #Find the latest time that dp's destination is blocked by ANY other droplet.
                try:
                    delay_data = max([x for x in blocked if x[1:3] == dp.Get_Dest()], key = lambda x: x[0])
                    # print("Maximum blocked time for dp number {} carrying {} is".format(dp.index, dp.species), delay)
                except:
                    delay_data = (0, None, None, None)
                    
                #Calculate a delay estimate of up to 4 + (# of steps into the future that destination is blocked) - (# of steps to destination in Manhattan distance)
                #This means it can't possibly arrive near the destination until after it's no longer blocked. Thus it won't be loitering around the area.
                delay = max(0, 1 + (delay_data[0] - self.time) - Dist(dp.Get_Loc(), dp.Get_Dest()))
                dp.delayed_by = delay_data[3]
                dp.delay_amount = delay
                
                #Get the permanently blocked locations for droplets that may be stationary, or simply haven't yet planned their routes
                perm_blocked = [pair for odp in self.lab.droplets for pair in Get_Blocked(odp.Get_Loc(), shape = odp.Get_Shape(), shell = odp.Get_Shell()) if (not odp.Is_Routed()) and not (odp is dp or (odp in dp.collision_group and odp.At_Dest()))]
                # perm_blocked = []
    
                #Add all the gridpoints that are permanently forbidden for all droplets
                perm_blocked += self.perm_forbidden
    
                #Add the destinations so that no route directly blocks another route's destination
                perm_blocked += [pair for odp in self.lab.droplets for pair in Get_Blocked(odp.Get_Dest(), shape = odp.Get_Shape(group_total=True), shell = odp.Get_Shell(group_total=True)) if (odp not in dp.collision_group)]
                
                #Add the pull sites selected this round
                pull_shape = [(0,0), (1,0), (0,1), (-1,0), (0,-1)]
                pull_shell = list(set([(x + X, y + Y) for (x,y) in pull_shape for X in [-1, 0, 1] for Y in [-1, 0, 1] if (x + X, y + Y) not in pull_shape and X*Y == 0]))
                perm_blocked += [pair for node in self.current_nodes for site in node.pulling_sites for pair in Get_Blocked(site, shape = pull_shape, shell = pull_shell) if site != dp.Get_Loc()]
                
                #Add the end of any other droplet's route that does not match that droplet's own destination. These are the droplets that are finishing a shunt route. 
                for odp in [x for x in self.lab.droplets if x.route != [] and x.route[-1][1:3] != x.Get_Dest() and x is not dp]:
                    perm_blocked += [pair for pair in Get_Blocked(odp.route[-1][1:3], shape = odp.Get_Shape(), shell = odp.Get_Shell())]
                
                #Convert to sets so that it is faster to check membership
                blocked = set(blocked)
                perm_blocked = set(perm_blocked)
                
                dp.Set_Blocks(blocked, perm_blocked) #record which droplets are doing the blocking
                blocked = [x[0:3] for x in blocked] #Now drop the droplets
                
                #If the destination is perm-blocked, just skip this droplet.
                conglom_shape = dp.Get_Shape(True)
                conglom_occ = [(dp.Get_Dest()[0] + pair[0], dp.Get_Dest()[1] + pair[1]) for pair in conglom_shape]
                if any(pair in perm_blocked for pair in conglom_occ):
                    print("Droplet number {} carrying {} is indefinitely blocked from its destination during this routing stage. Continuing...".format(dp.index, dp.species))
                    continue
                
                #Note that blocked coordinates are actually coordinate triples, where the first entry is time. 
                #Permanently blocked coordinates are the usual coordinate pairs, without time.
                
                try:
                    #Get all the droplets in this collision group (NOT THE SAME THING AS 'grp') that have been routed to the destination already. They should be arriving first, and will merge with this droplet when it arrives.
                    priors = [odp for odp in dp.collision_group if ((odp.Is_Routed() and odp.Get_Dest() == dp.Get_Dest()) or odp.Get_Loc() == dp.Get_Dest()) and odp is not dp]
                    prior_area = sum(odp.area for odp in priors)
                    prior_radius = np.sqrt(prior_area/np.pi)
                        
                    #If the droplet failed to route previously, we'll check if it was because there is no viable path,
                    #or if it ran out of time trying to find its way past a maze of permanent blockers
                    if dp.cannot_route and (dp.prev_perm_blocked != []) and all(Y in dp.perm_blocked for Y in dp.prev_perm_blocked):
                        # print("Droplet index {} carrying {} has no viable path to destination at time {}. Waiting one round.".format(dp.index, dp.Get_Key(), self.time))
                        continue
                    
                    elif dp.cannot_route and (dp.prev_perm_blocked != []) and not all(Y in dp.perm_blocked for Y in dp.prev_perm_blocked):
                        print("Droplet index {} carrying {} has changed its permanent blocks. Checking for a new routing solution...".format(dp.index, dp.Get_Key()))

                    
                    #Now route the droplet
                    limit = 2*self.lab.grid_dim[0]*self.lab.grid_dim[1]
                    first_or_2nd_route = 1
                    dp.cannot_route, route1, endpoint, visit_count = Get_Route(grid_shape=self.lab.grid_dim, start=dp.Get_Loc(), end=dp.Get_Dest(), prior_radius=prior_radius, dp_radius=dp.Get_Radius(), blocked=blocked, perm_blocked=perm_blocked, start_time=self.time, delay=delay, limit=limit)

                    #Track some data for analysis later
                    self.astar_visits += visit_count
                    self.most_visits = max(self.most_visits, visit_count)
                    self.astar_calls += 1
                    
                    #If it failed to route, wait a round.
                    if dp.cannot_route:
                        dp.prev_perm_blocked = dp.perm_blocked.copy()
                        print("Droplet index {} carrying {} has no viable path to destination at time {}. Waiting for a change...".format(dp.index, dp.Get_Key(), self.time))
                        continue
                    
                    #If it succeeded, reset the no-progress tracker
                    self.no_progress_tracker = 0
                    first_or_2nd_route = 2
                    
                    #If it will merge with another droplet in its group at the periphery of the true destination:
                    if endpoint != dp.Get_Dest():
                        #Run another route (this one should be extremely short) from the location of the collision to the true destination
                        #But now include the new conglomerate droplet shape.
                        tot_rad = np.sqrt((prior_area + dp.area))/np.pi
                        _, route2, _, visit_count = Get_Route(grid_shape=self.lab.grid_dim, start=endpoint, end=dp.Get_Dest(), prior_radius=0, dp_radius=tot_rad, blocked=blocked, perm_blocked=perm_blocked, start_time=route1[-1][0]+1, delay=0, limit=limit)
                        self.astar_visits += visit_count
                    else:
                        route2 = [(route1[-1][0] + 1, *endpoint)]
                        
                except AssertionError as e:
                    raise e
                    #If it failed to find a valid route, send a warning and skip it. Try to route it again next round.
                    print("Droplet index {} carrying {} encountered a 'temporary' block that outlasted the time limit on route number {} at time {}.".format(dp.index, dp.Get_Key(), first_or_2nd_route, self.time))
                    self.failed_routes += 1                    
                    if dp.cannot_route:
                        dp.prev_perm_blocked = dp.perm_blocked.copy()
                    continue

                dp.Set_Route(route1 + route2, time = self.time)   
                
    def Send_Movement_Commands(self, status_update = False, makeplot = False, saveplot = False, wait_time = 2, ax = None):
        #Collects the activation list needed to step forward all the droplets along their routes and sends it to the lab.
        coords = []
        for dp in self.lab.droplets:
            coords += self.Generate_Active_Gridpoints(dp)
                
        self.lab.Add_Commands({'pot_indices':coords, 'pots':len(coords)*[1]})
        self.lab.Compile_Commands(status_update=status_update, makeplot=makeplot, saveplot=saveplot, wait_time=wait_time, ax=ax)

    def Find_Pull_Options(self, species, node):
        #Finds the locations where a given species from the instructions can be pulled.
        #Reserves that spot for the node
        if len(species) == 1:
            area = self.pull_data[species[0]]['area']
            radius = np.sqrt(self.pull_data[species[0]]['area']/np.pi)
            # shape = Calculate_Shape(radius)
            shape = Calculate_Shape(area = area)
            # options = [x for x in self.pull_data[species[0]]['loc'] if all(not self.Forbidden_Gridpoint(indices=Z, radius=radius)[0] for Z in Get_Blocked(x, shape=shape, shell=[]))]
            options = [x for x in self.pull_data[species[0]]['loc'] if not self.Forbidden_Gridpoint(indices=x, radius=radius)[0]]
        else:
            raise AssertionError('Trying to pull an invalid species: {}'.format(species))
        
        # blocked = set([pair for dp in self.lab.droplets for step in dp.route for pair in Get_Blocked(step[1:3], shape = dp.Get_Shape(), shell = dp.Get_Shell())]) 
        # options = [x for x in options if x not in blocked]
        
        if options == []:
            # print("Cannot pull {} this round.".format(species))
            return False
        
        #Try to pick the closest pull option to the other droplets in the node,
        #otherwise just choose one at random. 
        if node.active_droplets != []:
            #By default, try to pull closest to an active droplet
            loc = min(options, key=(lambda z: Dist(z, node.active_droplets[-1].Get_Loc())))
        else:
            #Otherwise, pick a random option
            loc = random.choice(options)
        
        #Generate the pull command and the electrostatic command
        self.lab.Add_Commands(dict(pull_indices = [loc], keys = [species], nodes = [node]))
        self.lab.Add_Commands(dict(pot_indices = [loc], pots = [1]))
        
        return loc
             
    def Find_Work_Location(self, loc, inst_type, node, droplets):
        #Finds an available location for a specific instruction type, like Gibson or Purify.
        
        #Find the total area of the conglomerate droplet that will be created from merging the existing droplets
        tot_area = sum(dp.area for dp in droplets)
        radius = np.sqrt(tot_area/np.pi)
        
        #Start by getting a list of all locations capable of the given instruction type.
        options_a = [inst_loc[1:] for inst_loc in self.inst_locs if inst_loc[0] == inst_type][0]
        
        #Find locations that are at a safe distance from any forbidden sites
        options_b = [pair for pair in options_a if not self.Forbidden_Gridpoint(indices = pair, allowed_droplets = droplets, node = node, radius = radius)[0]]
                
        #Get the location with the minimum distance to loc, unless the list is empty.
        if options_b == []:
            if self.verbose > 1:
                print("No {} site options this round!".format(inst_type))
            return False
        else:
            return min(options_b, key=lambda x: Dist(x, loc))
        
    def Forbidden_Gridpoint(self, indices, droplet = None, allowed_droplets = [], node = None, radius = None):
        #Returns true if a given gridpoint or its neighbors are forbidden
        
        if droplet is not None:
            Z = droplet.Get_Shape()
            shell = droplet.Get_Shell()
        elif radius is not None:
            Z = Calculate_Shape(np.pi*radius**2)
            shell = Calculate_Shell(np.pi*radius**2)
        else:
            raise ValueError('Shape and Droplet cannot both be "None" in call to Forbidden_Gridpoint()!')
        
        #Get all the gridpoints around the given index pair that would be touched by this droplet
        gridpoints = [self.lab.grid[coords] for coords in Get_Occupied(indices, Z, self.lab.grid_dim) if coords in self.lab.grid]
        
        #Are any of them forbidden?
        F = [x.Is_Forbidden(dp=droplet, allowed_droplets=allowed_droplets, node=node) for x in gridpoints]
        
        #Are any of them on the prescheduled paths of any droplets?
        on_path = indices in set([pair for dp in self.lab.droplets for step in dp.route for pair in Get_Blocked(step[1:3], shape = dp.Get_Shape(), shell = dp.Get_Shell())])

        #Return a boolean, plus the offending droplets if any        
        return on_path or any([x[0] for x in F]), [drop for x in F for drop in x[1] if drop is not None]
                 
    def Attach_Keys(self):
        #This looks for newly-pulled droplets and assigns them to the relevant nodes
        for dp in self.lab.droplets:
            if not dp.assigned:
                dp.assigned = True #Record that the droplet is now being assigned
                dp.node.droplets[dp.Get_Key()] = dp
                    
                #Add the droplet to the node's active list
                dp.node.active_droplets.append(dp)

    def Update_Keys(self):
        #Make sure that the keys associated with the droplets according to the nodes
        #accurately reflect the contents of the droplets
        
        for node in self.current_nodes:
            poplist = [];
            #Find each key in the node that doesn't match anymore
            for key, dp in node.droplets.items():
                if dp.Get_Key() != key:
                    poplist.append((dp.Get_Key(), key))
            
            #Fix the key
            for new_key, old_key in poplist:
                node.droplets[new_key] = node.droplets.pop(old_key)
                node.droplets[new_key].node = node  #Update the reference to the node                                         
              
    def Generate_Active_Gridpoints(self, dp):
        #Determines which gridpoints to activate in order to move the droplet to the first position on its route.
        #If the droplet has no route, activate all its currently-occupied gridpoints, excluding edges, to hold it in place.

        gp_indices = dp.Get_Shadow(region='interior', asindex=True)
        if not dp.route:
            return gp_indices
        
        #Find the direction the droplet is moving
        target = dp.route[0][1:3]
        X,Y = target - np.array(dp.Get_Loc())
            
        return [(x + X, y + Y) for (x,y) in gp_indices]
        
    def Merge(self, grp = []):
        #Sets the droplets in the group to merge.
        #Not used in the current version, but potentially useful at some point.
        grp[0].Set_Follow(grp[1])
        
        #For now, just set them all to follow the 0th droplet.
        for dp in grp[1:]:
            dp.Set_Follow(grp[0])
            
        self.Allow_Collisions(grp)
            
    def Allow_Collisions(self, grp):
        #Sets the collision group for each droplet in the group,
        #allowing exceptions for them to collide when routing.
        for dp in grp:
            dp.Set_Collision_Group(grp)
            
    def Shunt(self, node, exclude_active = False):
        #Shunts all the droplets in the node to random locations in the grid that aren't currently occupied
        #or required for droplet pulling, gibson assembly, etc.
        
        #If the droplet is already  or is excluded because it's active, skip over it
        for dp in list(node.droplets.values()):  
            if dp.Is_Routed() or dp.shunting or (exclude_active and dp in node.active_droplets):
                continue
            
            #Generate a random non-forbidden location
            rad = dp.Get_Radius()
            options = [key for key in self.lab.grid if (2 + rad < key[0] < self.lab.grid_dim[0] - rad - 2) and (2 + rad < key[1] < self.lab.grid_dim[1] - rad - 2)]
            choices = []
            for i in range(50):
                option = random.choice(options)
                if (not self.Forbidden_Gridpoint(option, radius=dp.Get_Radius())[0]) and not any(x in self.all_sites for x in Get_Blocked(option, dp.Get_Shape(), dp.Get_Shell())):
                    choices.append(option)
            if choices != []:
                dest = min(choices, key=lambda x: Dist(dp.Get_Loc(), x))
                self.Node_Select(node, dest, dp.Get_Shape(), dp.Get_Shell())
                dp.Set_Dest(dest, shunting = True)
                self.dest_sets += 1
            
    def Node_Select(self, node, loc, shape, shell = []):
        #Records the selection of a given site and surrounding area, depending on droplet shape, for a given node.
        blocked = Get_Blocked(loc, shape, shell)
        for x in blocked:
            if x in self.lab.grid:
                self.lab.grid[x].selected_by = node
                node.selected_sites.append(x)
    
    
    def Node_Pull(self, node, loc, shape):
        #Records an incoming droplet in a given pull site and surrounding area for a given node.
        if not loc:
            node.pulling_sites.append(loc)
        else:
            blocked = Get_Blocked(loc, shape, [])
            for x in blocked:
                if x in self.lab.grid:
                    self.lab.grid[x].pulled_by = node
                    node.pulling_sites.append(x)

def Dist(a,b, cartesian=False):
    if cartesian:
        return np.linalg.norm(np.array(a) - np.array(b))
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def Get_Blocked(coords, shape, shell):
    #Gets a list of blocked coordinates in 3-D or 2-D (time, x, y) for a single coordinate and time input
    if coords == False:
        return []
    if len(coords) >= 3:
        blocked = [(coords[0], coords[1] + X, coords[2] + Y) for (X, Y) in shape + shell]
        blocked += [(coords[0] + 1, coords[1] + X, coords[2] + Y) for (X, Y) in shape + shell]
        blocked += [(coords[0] - 1, coords[1] + X, coords[2] + Y) for (X, Y) in shape + shell]
    else:
        blocked = [(coords[0] + X, coords[1] + Y) for (X, Y) in shape + shell]
    return blocked
        
def Get_Occupied(indices, shape, grid_dim):
    x,y = indices
    return [(x + X, y + Y) for (X, Y) in shape if 0 <= (x + X) < grid_dim[0] and 0 <= (y + Y) < grid_dim[1]]
