#!/usr/bin/env python
from ants import *
from random import shuffle
import random

# define a class with a do_turn method
# the Ants.run method will parse and update bot input
# it will also run the do_turn method for us
class MyBot:
    def __init__(self):
        self.unseen = [] # unseen locations on the map
        self.hills = [] # enemy ant hills
        self.our_ants = set() #all our ants that aren't assigned to other stuff.  Cutting down list comprehension stuff
        self.food_targets = {} # targets that are food 
        self.hill_targets = {} # targets that are enemy hills
        self.targets = {} # targets that are an empty piece of land
        self.out = open('meow.txt','w')
        self.rev_orders = {}
        self.expansions = {(1,0),(0,1),(-1,0),(0,-1),(3,0),(0,3),(-3,0),(0,-3)}
    
    
    def do_setup(self,ants):
        # Add entire map to unseen locations
        for row in range(ants.rows):
            for col in range(ants.cols):
                if (ants.passable((row,col))):
                    self.unseen.append((row,col))
    
    # Moves an ant in loc in the direction dir. Checks for possible collisions and
    # map blocks before doing so.
    def do_move_direction(self, ants, orders, loc, direction):
        new_loc = ants.destination(loc, direction)
        if (ants.unoccupied(new_loc) and new_loc not in orders and loc in self.our_ants):#not in orders.values()):
            ants.issue_order((loc, direction))
            orders[new_loc] = loc
            self.rev_orders[loc] = new_loc
            if loc in self.our_ants:
                self.our_ants.remove(loc)
            return True
        else:
            return False
              
    # More accurate heuristic for distance
    def betterDist(self, ants, orders, loc1, loc2):
        row1, col1 = loc1
        row2, col2 = loc2
        cDist = min(abs(col1 - col2), ants.cols - abs(col1 - col2))
        rDist = min(abs(row1 - row2), ants.rows - abs(row1 - row2))
    
        man = cDist + rDist
        if man<=1:
            return man
    
        fastest = ants.direction(loc1, loc2)
        dests = map(lambda x : ants.destination(loc1,x),fastest)
        if not reduce(lambda x,y: x or y, map(lambda x : ants.passable(x) and x not in orders, dests)):
            man = man
        return man    
    
    def worstDist(self, loc1, loc2):
        return abs(loc1[0] - loc2[0]) + abs(loc1[1] - loc2[1])
        
     
     
    def trace_path(self, came_from, current_node):    
        if current_node in came_from:
            p = self.trace_path(came_from, came_from[current_node])
            p.append(current_node)
            return p
        else:
            return [current_node]
    #'''   
    # Figures out how to move next to get closer to the destination
    # Returns true if an ant can be assigned a target, false otherwise
    def do_move_location(self, ants, orders, loc, dest, target_type):
        if ants.time_remaining() < 10:
            return False
        
        if (ants.distance(loc, dest) == 1): # then there is no reason to run A*/no blockage possible
            d = ants.direction(loc, dest)[0]
            if self.do_move_direction(ants, orders, loc, d):
                if target_type == 'FOOD':
                    self.food_targets[dest] = loc
                elif target_type == 'HILL':
                    self.hill_targets[dest] = loc
                else:
                    self.targets[dest] = loc
                return True
            else:
                return False
        
        closedset = []
        openset = set([loc])#[loc]
        came_from = {}
    
        g_score = {}
        h_score = {}
        f_score = {}
    
        g_score[loc] = 0
        #h_score[loc] = 5*self.betterDist(ants, orders, loc, dest)
        h_score[loc] = 3*self.worstDist(loc, dest)
        f_score[loc] = g_score[loc] + h_score[loc]
        
        while len(openset) != 0:
            current = min(f_score, key = lambda x: f_score.get(x))
    
            if current == dest:
                path = self.trace_path(came_from, dest)
                if len(path) < 2:
                    return False
                directions = ants.direction(loc,path[1])
                if self.do_move_direction(ants, orders, loc, directions[0]):
                    if target_type == 'FOOD':
                        self.food_targets[dest] = loc
                    elif target_type == 'HILL':
                        self.hill_targets[dest] = loc
                    else:
                        self.targets[dest] = loc
                    return True
                else:
                    return False
    
            
            del f_score[current]
            openset.remove(current) #openset.remove(current)
            closedset.append(current)
    
            # explore possible directions
            aroundMe = [ants.destination(current, d) for d in ['n','s','e','w']]
            neighbors = [nloc for nloc in aroundMe if ants.passable(nloc) and nloc not in closedset]
            
            for neighbor in neighbors:
                if neighbor in closedset:
                    continue
    
                tentative_g_score = g_score[current] + 1
                if neighbor not in openset:
                    openset.add(neighbor)#append(neighbor)
                    h_score[neighbor] = self.betterDist(ants, orders, neighbor, dest)
                    tentative_is_better = True
                elif tentative_g_score < g_score[neighbor]:
                    tentative_is_better = True
                else:
                    tentative_is_better = False
    
                if tentative_is_better:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = g_score[neighbor] + h_score[neighbor]
    
        return False
    
    
    # Updates the targets to reflect when an ant moves
    def update_targets(self, orders, targets):
        for (tar_loc, ant_loc) in targets.items():
            if ant_loc not in self.our_ants: #in orders.values(): # this means the ant it was assigned to has moved
                if ant_loc == tar_loc: # target has been reached!
                    del targets[tar_loc]
                else: # not there yet, but closer!
                    #new_loc = [nloc for nloc in orders if orders[nloc] == ant_loc][0] # get ant's new location
                    new_loc = self.rev_orders[ant_loc]
                    targets[tar_loc] = new_loc
       
    
    
    def hunt_food(self, ants, orders):
        food = [floc for floc in ants.food() if floc not in self.food_targets]
        antz = [aloc for aloc in ants.my_ants() if aloc not in list(self.food_targets.values() + self.hill_targets.values())]
        
        ant_dist = []
        for food_loc in food:
            for ant_loc in antz:
                if ants.time_remaining() < 10:
                    self.out.write('We hit the break in food loc.\n')
                    self.out.flush()
                    break
                dist = ants.distance(ant_loc, food_loc)
                ant_dist.append((dist, ant_loc, food_loc))
        ant_dist.sort()
        for dist, ant_loc, food_loc in ant_dist:
            if food_loc not in self.food_targets and ant_loc not in list(self.targets.values() + self.hill_targets.values() + self.food_targets.values()):
                self.do_move_location(ants, orders, ant_loc, food_loc, 'FOOD')
        
    
    def hunt_hills(self, ants, orders):
        targs = set(self.targets.values() + self.hill_targets.values() + self.food_targets.values())  # changed to set from list...
        antz = [aloc for aloc in ants.my_ants() if aloc not in targs]
        
        for hill_loc, hill_owner in ants.enemy_hills():
            if hill_loc not in self.hills:
                self.hills.append(hill_loc)        
        
        for hill_loc in self.hills:
            self.out.write('WE FOUND A HILLLLLLLlllll\n')
            #self.out.flush()
            for ant_loc in antz:
                if ants.time_remaining() < 10:
                    self.out.write('We hit the break in hunt hills.\n')
                    self.out.flush()
                    break
                
                self.out.write('assigning ants to kill enemy hill!\n')
                #self.out.flush()
                if ant_loc not in targs:
                    self.do_move_location(ants, orders, ant_loc, hill_loc, 'HILL')
    
    
    def explore(self, ants, orders): # make sure we aren't targetting walls?
        for loc in self.unseen[:]:
            if ants.visible(loc):
                self.unseen.remove(loc)
        for ant_loc in ants.my_ants():
            if ants.time_remaining() < 10:
                    self.out.write('We hit the break in explore.\n')
                    self.out.flush()
                    break
            if ant_loc not in list(self.targets.values() + self.hill_targets.values() + self.food_targets.values()):
                unseen_dist = []
                for unseen_loc in self.unseen:
                    if ants.time_remaining() < 10:
                        self.out.write('We hit the 2nd break in explore.\n')
                        self.out.flush()
                        break
                    if ants.passable(unseen_loc):
                        dist = ants.distance(ant_loc, unseen_loc)
                        unseen_dist.append((dist, unseen_loc))
                unseen_dist.sort()
                for dist, unseen_loc in unseen_dist:
                    if self.do_move_location(ants, orders, ant_loc, unseen_loc, 'LAND'):
                        break
    
    
    def bound(self, ants, loc):
        return (loc[0]%ants.rows, loc[1]%ants.cols)

    def time_check(self, ants):
        if ants.time_remaining() < 10000:
            return True
        else:
            return False


    def random_location(self, ants):
        x = (random.randint(0, ants.rows), random.randint(0, ants.cols))
        #while ants.visible(x) and not ants.passable(x):
        #while not ants.passable(x) and not self.time_check(ants):
        #    x = (random.randint(0, ants.rows), random.randint(0, ants.cols))
        return x

    def bread_crumb(self, ants, orders):
        #for ant in ants.my_ants():
        #self.out.write('Started bread_crumb\n')
        #self.out.flush()
        
        for ant in list(self.our_ants):

            #if ant in orders.values():
            #    continue 

            #if ant in self.mission:
            #    if ant == self.mission[ant]:
            #        del self.mission[ant]
            #    else:
            #        do_move_location(ant, self.mission[ant])
            #        break

               
            d = 1
            #directions = ['n', 'e', 's', 'w']
            u = []
            #while len(u) == 0 and d<=3:
            #    d += 2
            #    expansions = [(ant[0] + d , ant[1]), (ant[0] - d, ant[1]), (ant[0], ant[1] + d), (ant[0], ant[1] - d)]
            #    expansions = [self.bound(ants, x) for x in expansions] #map(self.bound, expansions)
            #    for loc in expansions:
            #        if not ants.visible(loc) and ants.passable(loc) and ants.unoccupied(loc) and loc not in orders:
            #            u.append(loc)

            for e in self.expansions:
                loc = self.bound(ants, (ant[0] + e[0], ant[1] + e[1]))
                if not ants.visible(loc) and ants.passable(loc) and ants.unoccupied(loc) and loc not in orders:
                    u.append(loc)
            
            if not len(u) == 0:
                random.shuffle(u)
                self.do_move_location(ants, orders, ant, u[0], 'EXPLORE')
            else:
                #self.mission[ant] = random_location()
                #self.do_move_location(ants, orders, ant, self.mission[ant])
                self.do_move_location(ants, orders, ant, self.random_location(ants), 'EXPLORE')

            if self.time_check(ants):
                return
                
        #self.out.write('Finished bread_crumb\n')
        #self.out.flush()

    
    
    def do_turn(self, ants): 
        orders = {} # tracks what moves have been
        self.our_ants = set(ants.my_ants())
        self.rev_orders = {}
        
        # get off my lawn!
        for hill_loc in ants.my_hills():
            orders[hill_loc] = None
        
        
        # don't forget about the old targets!
        for (tar_loc, ant_loc) in self.food_targets.items():
            if tar_loc in ants.food():
                self.do_move_location(ants, orders, ant_loc, tar_loc, 'FOOD')
            else:
                del self.food_targets[tar_loc]
        
        for (tar_loc, ant_loc) in self.targets.items():
            if tar_loc not in self.unseen: # place has now been seen
                del self.targets[tar_loc]
            else:
                self.do_move_location(ants, orders, ant_loc, tar_loc, 'LAND')
            
        for (tar_loc, ant_loc) in self.hill_targets.items():
            if tar_loc not in ants.my_hills(): # still an enemy hill
                self.do_move_location(ants, orders, ant_loc, tar_loc, 'HILL')
            else: # otherwise it has been taken over 
                del self.hill_targets[tar_loc]
                self.hills.remove(tar_loc)
        
        # attack any hills we see
        self.hunt_hills(ants, orders)

        # hunt for more food
        self.hunt_food(ants, orders)
        
        # explore the map!
        #self.explore(ants, orders)
        self.bread_crumb(ants, orders)
        
        # default move
        
        """
        for ant_loc in ants.my_ants():
            if ants.time_remaining() < 10:
                break
        
            if ant_loc not in list(self.targets.values() + self.hill_targets.values() + self.food_targets.values()):
                directions = ['n','e','s','w']
                shuffle(directions)
                for direction in directions:
                    if self.do_move_direction(ants, orders, ant_loc, direction):
                        break #used to be break but that doesn't make sense...
        """                 
        
        self.update_targets(orders, self.food_targets)
        self.update_targets(orders, self.hill_targets)
        self.update_targets(orders, self.targets)
        
        
    
            
if __name__ == '__main__':
    # psyco will speed up python a little, but is not needed
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    
    try:
        # if run is passed a class with a do_turn method, it will do the work
        # this is not needed, in which case you will need to write your own
        # parsing function and your own game state class
        Ants.run(MyBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')
