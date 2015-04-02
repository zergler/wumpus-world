#!/usr/bin/env python2

import agents
import logic
import pdb


class Error(Exception):
    """ Base exception for the module.
    """
    def __init__(self, msg):
        self.msg = 'error: %s' % msg


class AgentWW(agents.Agent):
    """ Agent for the wumpus world.
    """
    def __init__(self):
        self.KB = logic.PropKB()
        self.location = (1, 1)
        self.orientation = 0
        self.visited = set()
        self.action = None
        self.path = []

        self.study()

        def program(percept):
            breeze  = percept[0]
            stench  = percept[1]
            bump    = percept[2]
            scream  = percept[3]
            glitter = percept[4]

            # Get the position and orientation of the agent.
            self.update()
            self.visited.add(self.location)
            (x, y) = self.location

            k1 = '%sS%d%d' % (logic.if_(stench, '', '~'), x, y)
            k2 = '%sB%d%d' % (logic.if_(breeze, '', '~'), x, y)

            self.KB.tell(k1)
            self.KB.tell(k2)

            if glitter:
                self.action = 'Grab'
            elif self.path:
                self.action = self.path.pop()
            else:
                safe_moves = set()
                for [i, j] in self.frontier():
                    query = '~P%d%d & ~W_%d%d' % (i, j, i, j)
                    if self.KB.ask(logic.Expr(query)) != False:
                        safe_moves.append((i, j))

                valid_moves = safe_moves.difference(self.visited())
                adj_moves = get_adj(self.location)
                best_move = adj_moves.intersection(valid_moves)

                if best_move is not None:
                    best_move = best_move[0]
                    self.get_path(best_move)
                else:
                    self.action = random.choice(['ROTATE_LEFT', 'ROTATE_RIGHT', 'MOVE'])

                # Add the action to the KB.

            return self.action

        self.program = program

    def get_path(self, best_move):
        """ Gets the path for the best action
        """
        # Make sure the agent is orientated the correct way.
        (i, j) = self.location - self.best_move
        if i == 0:
            if j > 0:
                goal_orientation = 3
            else:
                goal_orientation = 1
        if j == 0:
            if i > 0:
                goal_orientation = 2
            else:
                goal_orientation = 0

        cur_orientation = self.orientation
        while cur_orientation != goal_orientation:
            # Make this work with rotate right too.
            self.path.append('ROTATE_LEFT')

    def get_adj(self, location):
        """ Gets the adjacent cells.
        """
        adj = []
        (i, j) = location
        if i - 1 > 0:
            adj.append((i - 1, j))
        if j - 1 > 0:
            adj.append((i, j - 1))
        if j + 1 <= 4:
            adj.append((i, j + 1))
        if i + 1 <= 4:
            adj.append((i + 1, j))
        return adj

    def study(self):
        """ Creates the initial KB.
        """
        self.study_breezes()
        self.study_stenches()

    def study_breezes(self):
        for i in range(1, 5):
            for j in range(1, 5):
                pit_set = self.get_adj((i, j))
                try:
                    pit_set.remove((1, 1))
                except ValueError:
                    pass

                breeze_sent = 'B%d%d' % (i, j)
                # not_breeze_sent = '~B%d%d' % (i, j)
                pit_sent = ''
                for k in pit_set:
                    pit_sent = pit_sent + 'P%s%s | ' % k
                pit_sent = pit_sent[:-3]
                knowledge = breeze_sent + ' <=> ' + '(' + pit_sent + ')'
                self.KB.tell(knowledge)

    def study_stenches(self):
        for i in range(1, 5):
            for j in range(1, 5):
                if (i, j) == (1, 1):
                    continue
                wumpus_set = self.get_adj((i, j))
                try:
                    wumpus_set.remove((1, 1))
                except ValueError:
                    pass

                stench_sent = 'S%d%d' % (i, j)
                # not_stench_sent = '~S%d%d' % (i, j)
                wumpus_sent = ''
                for k in wumpus_set:
                    wumpus_sent = wumpus_sent + 'W%s%s | ' % k
                wumpus_sent = wumpus_sent[:-3]
                knowledge = stench_sent + ' <=> ' + '(' + wumpus_sent + ')'
                self.KB.tell(knowledge)

    def update(self):
        if self.action == 'ROTATE_LEFT':
            self.orientation = (self.orientation + 1) % 4
        elif self.action == 'ROTATE_RIGHT':
            self.orientation = (orientation - 1) % 4
        elif self.action == 'MOVE':
            if self.orientation == 2 and i - 1 > 0:
                self.location = (i - 1, j)
            elif self.orientation == 3 and j - 1 > 0:
                self.location = (i, j - 1)
            elif self.orientation == 1 and j + 1 <= 4:
                self.location = (i, j + 1)
            elif self.orientation == 0 and i + 1 <= 4:
                self.location = (i + 1, j)

    def frontier(self):
        """ Returns the frontier of the problem. The current node, all
            previously visited nodes, as well as the possible transitions of
            these are in the frontier.
        """
        frontier = set()
        (i, j) = self.location
        if i - 1 > 0:
            frontier.add((i - 1, j))
        if j - 1 > 0:
            frontier.add((i, j - 1))
        if j + 1 <= 4:
            frontier.add((i, j + 1))
        if i + 1 <= 4:
            frontier.add((i + 1, j))

        frontier = frontier.union(self.visited)
        return frontier

    def action(self):
        return self.action


# get percepts from environment (the simulator)
def update(percepts):
    print("Agent: 'Getting the percepts: [breeze, stench, bump, scream, glitter] = '" % (percepts))
    aww.program(percepts)


# pass back action to environment (the simulator)
def action():
    # the_action = aww.action()
    return random.choice(['MOVE', 'ROTATE_LEFT', 'ROTATE_RIGHT'])
    print("Excecuting: %s" % the_action)



aww = AgentWW()
