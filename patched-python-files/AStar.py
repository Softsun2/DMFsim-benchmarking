# -*- coding: utf-8 -*-
"""
11/11/21

@author: Andrew Stephan

This is an A* routing library that allows for time-dependent droplet routes to be computed.
Assumes perfectly round droplets with variable radii and allows for the existence of other droplets
that currently (or shortly will) occupy the destination and determines how the collision will go.

Decomposes the 3D routing problem into a pair of 2D routing problems as a way of reducing computational burden.
Makes a slight tradeoff in route efficiency to significantly improve compute time.


"""
import numpy as np
import random
import copy
import time
dist_weight = 2


def Get_Route(grid_shape, start, end, dp_radius, blocked, prior_radius=0, perm_blocked=[], start_time=0, delay=0, limit=0):
    #Finds a route for a droplet with a given radius from start to end while avoiding blocks.
    #Instead of directly calculating a 3D route through timespace, calculates two 2D routes in succesion.
    
    #First, calculate a 2D route ignoring transient blocks and only avoiding the permanent blocks.
    #This iteration ignores the time dimension and moves freely in two spatial dimensions.
    path, endpoint, visit_count = Single_Route_Without_Time(grid_shape=grid_shape, start=start, end=end, dp_radius=dp_radius, perm_blocked=perm_blocked)
    
    #Now use that route as a reference path for a time-dependent route.
    #This iteration is allowed to move along one spatial dimension (progress along the route)
    #and one time dimension.
    route, endpoint, more_visits = Single_Route_With_Time(grid_shape=grid_shape, start=start, end=end, dp_radius=dp_radius, blocked=blocked, prior_radius=prior_radius, perm_blocked=perm_blocked, start_time=start_time, delay=delay, reference_path=path)

    #Return a boolean indicating if the droplet could not route
    #plus the route itself, its endpoint, and the number of A* visits performed for data analysis purposes.
    return (route == []), route, endpoint, (visit_count + more_visits)

def Single_Route_With_Time(grid_shape, start, end, dp_radius, blocked, prior_radius = 0, perm_blocked = [], start_time = 0, delay = 0, step_limit = float('inf'), reference_path = []):
    #Runs 3D time-multiplexed A* algorithm on arbitrary grids assuming non-diagonal movement, where
    #each move costs 1. Allows for blocked areas but will stop after steps exceeds step_limit, and thereby assume there is no viable (or easily determinable) route.
    #Uses Manhattan distance as a heuristic for the A* point selection calculation.
    #Inputs:
        #grid_shape. A tuple, list, or other iterable with two elements indicating the shape of the grid to be searched
        #start. A tuple containing the starting point indices
        #end. The primary and ultimate destination. A tuple containing the destination point indices
        #dp_radius. The radius of the droplet
        #blocked. A list of coordinate triples containing a time and the blocked or unavailable indices
        #prior_radius. The radius of the prior droplet--if any--occupying the destination, with which this droplet will merge.
        #perm_blocked. Permanently blocked coordinate pairs.
        #start_time. The lab time at which this route begins.
        #delay. The number of delayed steps before the destination is freed up.
        #step_limit. How far to go before calling it quits because there is probably no available route.
        #reference_path. A list which, if it is nonempty, will contain the only points the system is allowed to traverse. 
            #This is used to speed up the search process by essentially turning this into a 2D problem--one spatial axis along the reference path, one temporal axis.
    
    #Initialize the score grid with large values
    sx,sy = start
    ex,ey = end
    t = start_time + delay
    prior_occ = []
    disallowed = []
    
    dp_shape = Shape_from_Radius(dp_radius)
    if prior_radius > 0:
        prior_shape = Shape_from_Radius(prior_radius)
        prior_occ = [(ex + Z[0], ey + Z[1]) for Z in prior_shape if (0 <= ex + Z[0] < grid_shape[0]) and (0 <= ey + Z[1] < grid_shape[1])]
    
    inf = 2*(grid_shape[0]*grid_shape[1])
    scores = {} #Dictionary to hold the search distance scores of each coordinate center
        
    #Assign the destination node a score of 0    
    scores[(t, sx, sy)] = 0  
    
    #Initialize the unvisited list
    unvisited = [(t,sx,sy)]
    visited = []
    steps = 0
    
    endpoint = end #Where the droplet will be when this is finished. If it collides with another droplet, this may not be equal to 'end'.
    
    #Iterate until start has been visited
    while visited == [] or visited[-1][1:] != end:
        steps += 1

        if (steps + 1) % 100 == 0:
            # print(steps)
            pass
        if steps >= step_limit:
            raise AssertionError("Step limit reached during Dijkstra route after searching up to time = {}!".format(max([x[0] for x in visited])) + str(reference_path))
            
        #Find the minimum-scoring coordinate pair in the unvisited list
        #Use an A*-type ranking that incorporates an estimate of the distance from each point to the destination
        if reference_path:
            #In this option, we compare the points to an existing path developed in a static grid 
            t,x,y = min(unvisited, key = lambda Q: Get_Score(Q, inf, scores) + dist_weight*Dist((Q[1],Q[2]), (ex,ey)))

        else:
            #In this option, we use a simple distance heuristic.
            t,x,y = min(unvisited, key = lambda Q: Get_Score(Q, inf, scores) + dist_weight*Dist((Q[1],Q[2]), (ex,ey)))
        
        #If there are prior droplets on the destination and we've collided,
        #we might be concluding here but first we need to be sure this is a valid place to merge.
        #We could either collide because the droplets touch at this point, OR because once this point is activated the prior droplet will move toward the new droplet and merge.
        if prior_radius > 0 and (Dist((x,y), end, cartesian=True) <= (prior_radius + dp_radius) or ((x,y) in prior_occ)):

            #First figure out if the other droplet will be moving.
            #This assumes that (x,y) is the coordinate of the gridpoint closest to the other droplet that has
            #been activated, and we'll estimate that the other droplet will move in the direction of (x,y) if at all.
            prior_shape = Shape_from_Radius(prior_radius)
            delta = np.array((0,0))
            if (x,y) in [(ex + X, ey + Y) for (X,Y) in prior_shape]:
                delta = np.array((x,y)) - end
                delta = delta/np.linalg.norm(delta)
                
            #Now calculate the net center of the new combined droplet
            center = np.average([(x+0.5, y+0.5), (ex+0.5 + delta[0], ey+0.5 + delta[1])], weights = [dp_radius**2, prior_radius**2], axis=0)
            # center = np.average([(x+0.5, y+0.5), (ex+0.5, ey+0.5)], weights = [dp_radius**2, prior_radius**2], axis=0)
            center = tuple(np.floor(center).astype('int'))
            
            #Now check if, with the new shape, any boundaries will be violated.
            new_dp_radius = np.sqrt((prior_radius**2 + dp_radius**2))
            new_dp_shape = Shape_from_Radius(new_dp_radius)
            occupied = [(t, center[0] + pair[0], center[1] + pair[1]) for pair in new_dp_shape] 
            
            #First check  if it's a perm_block violation or a temporary block violation
            if any((cx, cy) in perm_blocked for (t, cx, cy) in occupied):
                #If it's a permanent block, remove this site from all possible future exploration
                disallowed.append((x,y))
                scores[(t,x,y)] = inf
                continue
            
             #If it is blocked either way, backtrack a step. Set this point to a score of inf, and choose a new t,x,y.
            elif any((t, cx, cy) in blocked for (t, cx, cy) in occupied):
                scores[(t,x,y)] = inf
                continue
            
            #Otherwise, record the new endpoint and break the loop.
            endpoint = center
            visited.append((t,x,y))
            break
        
        #If we've otherwise arrived at the destination, conclude.
        if (x,y) == end:
            visited.append((t,x,y))
            break
            
        #Get a list of move options from here
        #Exclude any options that have previously been added to the disallowed group
        #because they caused a merge that collided with a permanently forbidden zone
        if reference_path == []:
            options = [(t + 1, x + X, y + Y) for X in [1, 0, -1] for Y in [1, 0, -1] if X*Y == 0 and (x + X, y + Y) not in disallowed]
        else:
            options = [(t + 1, x + X, y + Y) for X in [1, 0, -1] for Y in [1, 0, -1] if X*Y == 0 and (x + X, y + Y) not in disallowed and (x + X, y + Y) in reference_path]
                
        #Check each move option for a few conditions
        for ct, cx, cy in options:
            #First, it hasn't been checked yet and it's not already in the to-check list
            if (ct, cx, cy) not in unvisited and (ct, cx, cy) not in visited:
                #Find the the positions the droplet would occupy 
                #if it centered on (cx, cy) at time (ct)
                occupied = [(ct, cx + pair[0], cy + pair[1]) for pair in dp_shape] 

                #The second condition is: it's either 1) at the starting point or 
                #2) none of the points the droplet would occupy are temporarily or permanently blocked or out of bounds
                if (cx, cy) == (sx, sy) or (((-1 + dp_radius) <= cx < (1 + grid_shape[0] - dp_radius) and (-1 + dp_radius) <= cy < (1 + grid_shape[1] - dp_radius)) and (all((zt, zx, zy) not in blocked and (zx, zy) not in perm_blocked for (zt, zx, zy) in occupied))):

                    #If all conditions are met, add a score for this new option
                    scores[(ct, cx, cy)] = min(Get_Score((ct, cx, cy), inf, scores), scores[(t, x, y)] + 1)
                    unvisited.append((ct, cx, cy))

                
        #Remove (x,y) from the unvisited list and add it to the visited list.
        unvisited.remove((t,x,y))
        visited.append((t,x,y))

    #Now that the score of 'start' has been determined, let's map out the route
    #to the destination from the starting point.
    
    #Beginning with 'start', append the lowest-scoring neighbor
    #of the most recent coordinate pair in the path list.
    #Repeat until 'end' is in path list.
    path = [(t, x, y)]
    while path[-1] != (start_time + delay, sx, sy):
        t,x,y = path[-1]
        options = [(t - 1, x + X, y + Y) for X in [1, 0, -1] for Y in [1, 0, -1]
                      if X*Y == 0 and (t-1, x+X, y+Y) in scores]#Get_Score((t - 1, x + X, y + Y), inf, scores) == scores[(t, x, y)] - 1]
        # random.shuffle(neighbors)
        
        #Find the step with the lowest score
        new_step = min(options, key = lambda Q: Get_Score(Q, inf, scores))
        
        #If that step is no better than just staying in place, do that instead.
        if Get_Score(new_step, inf, scores) == Get_Score((t-1, x, y), inf, scores):
            path.append((t-1, x, y))
        else:
            path.append(new_step)
            

    for time in range(start_time + delay - 1, start_time - 1, -1):
        path.append((time, sx, sy))

    path.reverse()
    
    #Leave a note for debugging purposes
    if prior_radius > 0:
        path[-1] = (*path[-1], "Mergepoint", endpoint)
        
    # print(steps)
    return path, endpoint, len(visited)

def Single_Route_Without_Time(grid_shape, start, end, dp_radius, perm_blocked = [], prior_radius = 0):
    #Similar to the route with time function. Calculates a route from 'start' to 'end' while ignoring transient time-dependent blocks. Only avoids permanent blocks.
    #Uses an A* method with Manhattan-distance as a point selection heuristic to speed up the discovery of a valid route.
    
    endpoint = end
    visit_count = 0
    sx, sy = start
    ex, ey = end
    dp_shape = Shape_from_Radius(dp_radius)
    prior_occ = []
    inf = 2*(grid_shape[0]*grid_shape[1])
    scores = {} #Dictionary to hold the search distance scores of each coordinate center
        
    if prior_radius > 0:
        prior_shape = Shape_from_Radius(prior_radius)
        prior_occ = [(ex + Z[0], ey + Z[1]) for Z in prior_shape if (0 <= ex + Z[0] < grid_shape[0]) and (0 <= ey + Z[1] < grid_shape[1])]
    
    #Assign the destination node a score of 0    
    scores[(sx, sy)] = 0  
    
    #Initialize the unvisited list
    unvisited = [(sx,sy)]
    visited = []
    
    #Repeat until we visit the destination
    while end not in visited:
        
        #Select a point from the unvisited list that has the minimum combined score,
        #calculated from lapsed time and estimated distance from destination heuristic.
        try:
            x,y = min(unvisited, key = lambda Q: Get_Score(Q, inf, scores)  + dist_weight*Dist(Q,end))
            visit_count += 1
        except ValueError:
            return [], None, visit_count
    
        #Will the droplet collide with its priors at this point?
        if prior_radius > 0 and (Dist((x,y), end, cartesian=True) <= (prior_radius + dp_radius) or ((x,y) in prior_occ)):

            #First figure out if the other droplet will be moving.
            #This assumes that (x,y) is the coordinate of the gridpoint closest to the other droplet that has
            #been activated, and we'll estimate that the other droplet will move in the direction of (x,y) if at all.
            prior_shape = Shape_from_Radius(prior_radius)
            delta = np.array((0,0))
            if (x,y) in [(ex + X, ey + Y) for (X,Y) in prior_shape]:
                delta = np.array((x,y)) - end
                delta = delta/np.linalg.norm(delta)
                
            #Now calculate the net center of the new combined droplet
            center = np.average([(x+0.5, y+0.5), (ex+0.5 + delta[0], ey+0.5 + delta[1])], weights = [dp_radius**2, prior_radius**2], axis=0)
            # center = np.average([(x+0.5, y+0.5), (ex+0.5, ey+0.5)], weights = [dp_radius**2, prior_radius**2], axis=0)
            center = tuple(np.floor(center).astype('int'))
            
            #Now check if, with the new shape, any boundaries will be violated.
            new_dp_radius = np.sqrt((prior_radius**2 + dp_radius**2))
            new_dp_shape = Shape_from_Radius(new_dp_radius)
            occupied = [(center[0] + pair[0], center[1] + pair[1]) for pair in new_dp_shape] 
            
            #First check  if it's a perm_block violation or a temporary block violation
            if any((cx, cy) in perm_blocked for (cx, cy) in occupied):
                #If it's a permanent block, remove this site from all possible future exploration
                scores[(x,y)] = inf
                continue

            #Otherwise, record the new endpoint and break the loop.
            endpoint = center
            visited.append((x,y))
            break
        
        #Barring any collisions with priors, are we at the end?
        if (x,y) == end:
            visited.append(end)
            break
        
        #If this isn't the end, get a list of options for the next visit
        options = [(x + X, y + Y) for X in [1, 0, -1] for Y in [1, 0, -1] if (X*Y == 0)]
        
        #Assign scores for all viable options.
        for (cx, cy) in options:
            if (cx,cy) not in visited and (cx,cy) not in unvisited:
                occupied = [(cx + pair[0], cy + pair[1]) for pair in dp_shape] 
                if (cx, cy) == (sx, sy) or all(-1 <= zx < (1 + grid_shape[0]) and -1 <= zy < (1 + grid_shape[1]) and (zx, zy) not in perm_blocked for (zx, zy) in occupied):
                    scores[(cx, cy)] = min(Get_Score((cx, cy), inf, scores), scores[(x, y)] + 1)
                    unvisited.append((cx, cy))
                    
        #Remove this point from the unvisited list, and record it in visited.
        unvisited.remove((x,y))
        visited.append((x,y))
        
    #Generate the path, starting at the destination
    path = [endpoint]
    
    while path[-1] != start:
        x,y = path[-1]
        #Find the lowest-cost neighboring point 
        options = [((x + X), (y + Y)) for X in [-1, 0, 1] for Y in [-1, 0, 1] if X*Y == 0]
        new_step = min(options, key = lambda Q: Get_Score(Q, inf, scores))
        
        #Append that point to the list.
        path.append(new_step)
        
    path.reverse()
    
    return path, endpoint, visit_count

        
def Get_Score(Q, inf, scores):
    #Returns the value stored in scores at key Q, returns inf if Q is not a valid key.
    if Q in scores:
        return scores[Q]
    return inf

def Dist(a,b, cartesian=False):
    #Manhattan or cartesian distance between two coordinate pairs.
    if cartesian:
        return np.linalg.norm([a[0]-b[0], a[1]-b[1]])
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def Shape_from_Radius(rad):
    #Gives a shape list from the radius of a droplet, assuming perfectly round.
    #Used for calculations based on as-of-yet non-instantiated droplets.
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
        elif any(Dist((0.5, 0.5), Z, cartesian=True) <= rad for Z in [(x0,y0), (x0, y1), (x1, y0), (x1, y1)]):
            shapelist.append((x0, y0))
            
    return shapelist