#!/usr/bin/env python2.7

import argparse
import threading
import random
import sys
import Tkinter as tk
import itertools
from PIL import ImageTk, Image

import wwagent

DEBUG = 0
try:
    import pdb
except ImportError:
    DEBUG = 0


class Error(Exception):
    """ Base exception for the module.
    """
    def __init__(self, msg):
        self.msg = 'error: %s' % msg


class WumpusSimulatorArgs(object):
    """ Parses the arguments for the Wumpus simulator.
    """
    def __init__(self):
        # Basic info.
        version = 1.0
        name = 'wwsim'
        date = '02/26/15'
        author = 'Igor Janjic'
        organ = '[ECE 5984] Artificial Intelligence and Engineering Fundamentals at Virginia Tech'
        desc = 'A simulator for the Wumpus world.'
        epil = 'Application %s version %s. Created by %s on %s for %s.' % (name, version, author, date, organ)

        # Arguments help.
        help_help = 'Show this help message and exit.'
        gui_help = 'Use this flag to display the simulation in a graphical user interface.'

        # Argparser.
        self.arg_parser = argparse.ArgumentParser(prog=name, description=desc, epilog=epil, add_help=False)
        optional_args = self.arg_parser.add_argument_group('Optional arguments', '')
        optional_args.add_argument('-h', '--help', action='help', help=help_help)
        optional_args.add_argument('-g', '--gui', dest='gui', action='store_true', default=False, help=gui_help)

    def parse(self):
        self.args = self.arg_parser.parse_args()


class Wumpus(object):
    def __init__(self):
        self.known  = False
        self.scream = False
        self.health = True
        self.get_location()
        self.get_stenches()

    def get_location(self):
        self.location = (1, 1)
        while self.location == (1, 1):
            self.location = (random.randint(1, 4), random.randint(1, 4))

    def contains_stench(self, location):
        """ Query whether the stench list contains a stench with a given
            location.
        """
        query = False
        for stench in self.stenches:
            if stench.location == location:
                query = True
        return query

    def get_stenches(self):
        """ Get the stenches.
        """
        self.stenches = []
        (i, j) = self.location
        if i - 1 > 0:
                self.stenches.append(self.Stench((i - 1, j)))
        if j - 1 > 0:
                self.stenches.append(self.Stench((i, j - 1)))
        if j + 1 <= 4:
                self.stenches.append(self.Stench((i, j + 1)))
        if i + 1 <= 4:
                self.stenches.append(self.Stench((i + 1, j)))

    class Stench(object):
        """ Encapsulates a stench.
        """
        def __init__(self, location):
            self.location = location
            self.known = False


class Agent(object):
    def __init__(self):
        # Percepts for the agent at the current time-step.
        self.location = (1, 1)
        self.orientation = 0
        self.in_cave = True      # whether the agent is in the cave (climb)
        self.health  = True      # agent alive or dead
        self.arrow   = True      # Whether the agent has an arrow
        self.bump    = False     # whether the agent has hit a wall


class Gold(object):
    def __init__(self):
        self.grabbed = False
        self.in_pit = False
        self.location = (1, 1)
        while self.location == (1, 1):
            self.location = (random.randint(1, 4), random.randint(1, 4))


class Pits(object):
    """ The current percepts of the agent implemented as a grid of objects.
    """
    def __init__(self):
        self.rows = 4
        self.cols = 4
        self.spawn_chance = 0.2
        self.new()

    def new(self):
        self.get_pits()
        self.get_breezes()

    def contains_pit(self, location):
        """ Query whether the pit list contains a pit with a given location.
        """
        query = False
        for pit in self.pits:
            if pit.location == location:
                query = True
        return query

    def contains_breeze(self, location):
        """ Query whether the breeze list contains a breeze with a given
            location.
        """
        query = False
        for breeze in self.breezes:
            if breeze.location == location:
                query = True
        return query

    def get_pits(self):
        """ Get the pits.
        """
        self.pits = []
        for (i, j) in itertools.product(range(4), range(4)):
            if random.random() < self.spawn_chance and (i, j) != (0, 0):
                self.pits.append(self.Pit((i + 1, j + 1)))

    def get_breezes(self):
        """ Get the breezes.
        """
        self.breezes = []
        for pit in self.pits:
            (i, j) = pit.location
            if i - 1 > 0:
                if not self.contains_pit((i - 1, j)):
                    self.breezes.append(self.Breeze((i - 1, j)))
            if j - 1 > 0:
                if not self.contains_pit((i, j - 1)):
                    self.breezes.append(self.Breeze((i, j - 1)))
            if j + 1 <= 4:
                if not self.contains_pit((i, j + 1)):
                    self.breezes.append(self.Breeze((i, j + 1)))
            if i + 1 <= 4:
                if not self.contains_pit((i + 1, j)):
                    self.breezes.append(self.Breeze((i + 1, j)))

    class Pit(object):
        """ Encapsulates a pit.
        """
        def __init__(self, location):
            self.location = location
            self.known = False

    class Breeze(object):
        """ Encapsulates a breeze.
        """
        def __init__(self, location):
            self.location = location
            self.known    = False


class WumpusSimulator(object):
    """ Simulator for the Wumpus world.

        The Wumpus world is a cave consisting of rooms connected by
        passageways.  Lurking within the world somewhere is the terrible Wumpus
        who will kill anyone who enters its room. The wumpus can be shot by an
        agent, but the agent has only one arrow. Some rooms contain pits that
        will kill agents that enter them, except for the wumpus and somewhere
        in the cave is a room that contains gold.

        PEAS Description:
        - Performance Measure: +1000 for climbing out of the cave with the
          gold, -1000 for falling into the pit or being eaten, -1 for each
          action taken, and -10 for using the arrow. The game ends when either
          the agent dies or climbs out of the cave.
        - Environment: A 4 x 4 grid of rooms. Agent always starts in the square
          labeled [1, 1], facing to the right. The locations of the gold and
          the wumpus are chosen randomly, with a uniform distribution, from the
          squares other than the start square. In addition, each square other
          than the start can be a pit, with probability 0.2.
        - Actuators: The agent can move Forward, TurnLeft by 90 deg, or
          TurnRight by 90 deg. The agent dies a miserable death if it enters a
          square containing a pit or a live wumpus. (It is safe, albeit smelly,
          to enter a square with a dead wumpus.) If an agent tries to move
          forward and bumps into a wall, then the agent does not move. The
          action Grab can be used to pick up the gold if it is in the same
          square as the agent. The action Shoot can be used to fire an arrow in
          a straight line in the direction the agent is facing. The arrow
          continues until it either hits (and hence kills) the wumpus or hits a
          wall. The agent has only one arrow, so only the first Shoot action
          has any effect.  Finally, the action Climb can be used to climb out
          of the cave, but only from square [1,1].
        - Sensors: The agent has five sensors, each of which gives a single bit
          of information:
            - In this square containing the wumpus and in the directly (not
              diagonally) adjacent squares, the agent will perceive a Stench.
            - In the square directly adjacent to a pit, the agent will perceive
              a breeze.
            - In the square where the gold is, the agent will perceive a
              Glitter.
            - When the agent walks into a wall, it will perceive a Bump.
            - When the Wumpus is killed, it emits a woeful Scream that can be
              perceived anywhere in the cave.

        The percepts will be given to the agent program in the form of a list
        of five symbols; for example, if there is a stench and a breeze, but no
        glitter, bump, or scream, the agent program will get [Stench, Breeze,
        None, None, None].
    """
    def __init__(self, gui):
        self.new()
        if gui:
            self.wsg = self.create_gui()
            self.wsg.run()
        else:
            print('Welcome to the wumpus world.')

    def start(self):
        while True:
            pass

    def new(self):
        """ Creates a new simulation.
        """
        self.wumpus = Wumpus()
        self.agent  = Agent()
        self.gold   = Gold()
        self.pits   = Pits()

        self.time = 0
        self.score = 0
        self.last_action = 'Enter'

        if self.pits.contains_pit(self.gold.location):
            self.gold.in_pit = True

    def action(self):
        """ Performs one action time-step.
        """
        # Make sure the agent is alive to perform an action.
        if not self.agent.health:
            return

        # Get the current percepts of the agent.
        breeze  = self.pits.contains_breeze(self.agent.location)
        stench  = self.wumpus.contains_stench(self.agent.location)
        bump    = self.agent.bump
        scream  = self.wumpus.scream
        glitter = self.gold.location == self.agent.location

        # Update the agents percepts.
        percept = [breeze, stench, bump, scream, glitter]
        wwagent.update(percept)

        # Get the next action from the agent.
        self.last_action = wwagent.action()

        self.last_action = random.choice(['MOVE'])
        if self.last_action == 'ROTATE_LEFT':
            self.rotate_left()
        elif self.last_action == 'ROTATE_RIGHT':
            self.rotate_right()
        elif self.last_action == 'MOVE':
            self.action_move()
        elif self.last_action == 'GRAB':
            self.action_grab()
        elif self.last_action == 'SHOOT':
            self.action_shoot()
        elif self.last_action == 'CLIMB':
            self.action_climb()

        # Update the simulator.
        self.time = self.time + 1

    def action_rotate_left(self):
        self.agent.orientation = (self.agent.orientation + 1) % 4

    def action_rotate_right(self):
        self.agent.orientation = (self.agent.orientation - 1) % 4

    def action_move(self):
        # Update the agents location.
        (i, j) = self.agent.location
        self.agent.bump = False
        if self.agent.orientation == 2:
            if i - 1 > 0:
                self.agent.location = (i - 1, j)
            else:
                self.agent.bump = True
        elif self.agent.orientation == 3:
            if j - 1 > 0:
                self.agent.location = (i, j - 1)
            else:
                self.agent.bump = True
        elif self.agent.orientation == 1:
            if j + 1 <= 4:
                self.agent.location = (i, j + 1)
            else:
                self.agent.bump = True
        elif self.agent.orientation == 0:
            if i + 1 <= 4:
                self.agent.location = (i + 1, j)
            else:
                self.agent.bump = True

        # Check to see if the agent has died.
        if self.pits.contains_pit(self.agent.location) or self.wumpus.location == self.agent.location:
            self.agent.health = False
            self.location = (None, None)

    def action_grab(self):
        if self.gold.location == self.agent.location:
                self.gold.grabbed = True

    def action_shoot(self):
        if self.agent.arrow:
            self.agent.arrow = False

            # If the wumpus is in the line of sight of the arrow, then kill it.
            (a, b) = self.agent.location
            (c, d) = self.wumpus.location
            if self.agent.orientation == 0:
                if b == d and c in [a + i for i in range(1, 4) if a + i <= 4]:
                    self.wumpus.health = 0
            elif self.agent.orientation == 1:
                if a == c and d in [b + i for i in range(1, 4) if b + i <= 4]:
                    self.wumpus.health = 0
            elif self.agent.orientation == 2:
                if b == d and c in [a - i for i in range(1, 4) if a - i >= 1]:
                    self.wumpus.health = 0
            elif self.agent.orientation == 3:
                if a == c and d in [b - i for i in range(1, 4) if b - i >= 1]:
                    self.wumpus.health = 0

    def action_climb(self):
        if self.agent.location == (1, 1):
            self.agent.in_cave = False

    def fow(self):
        """ Turns off fog of war.
        """
        pass

    def quit(self):
        sys.exit(0)

    def create_gui(self):
        """ Factory method that builds the wumpus simulator gui and passes the
            wumpus simulator to it.
        """
        return WumpusSimulator.WumpusSimulatorGUI(self)

    class WumpusSimulatorGUI(threading.Thread):
        """ GUI for the wumpus simulator.
        """
        def __init__(self, sim):
            threading.Thread.__init__(self)
            self.sim = sim
            self.root = tk.Tk()
            self.fog = True
            self.new_sim = True
            if self.root:
                self.root.resizable(0, 0)
                self.root.wm_title("Wumpus World Simulator")
                self.sim_frame = tk.Frame(self.root)     # Frame containing sim
                self.info_frame = tk.Frame(self.root)    # Frame for labels
                self.button_frame = tk.Frame(self.root)  # Frame for buttons
                self.create_world()

        def create_world(self):
            """ Creates the Wumpus world.

                Contains a 4 x 4 grid of the Wumpus world along with a few buttons.
                and labels. The button on the bottom left starts a new simulation.
                The bottom middle mutton performs one percept-action time-step. The
                bottom right button toggles the fog of war. Additionally, below
                each button is a label. Bellow the new simulation button, is a
                description of the performance score of the agent. Below the action
                button is the turn number of the game. Below the fog of war
                button is the current thought of the agent.
            """
            # Image of the world.
            self.world = Image.new('RGB', (4*100, 4*100), 'white')

            # Bind the button frame to the keyboard.
            # self.sim_frame.bind("<Key>", self.key_press)

            # Create the layout of the frames.
            self.sim_frame.pack(side=tk.TOP)
            self.info_frame.pack(side=tk.BOTTOM, fill='x')
            self.button_frame.pack(side=tk.BOTTOM, fill='x')

            # Create the layout of the info labels.
            self.health_label = tk.Label(self.info_frame, text='')
            self.time_label = tk.Label(self.info_frame, text='')
            self.action_label = tk.Label(self.info_frame, text='')
            self.score_label = tk.Label(self.info_frame, text='')

            self.health_label.pack(side='left', expand='yes', fill='x')
            self.time_label.pack(side='left', expand='yes', fill='x')
            self.action_label.pack(side='left', expand='yes', fill='x')
            self.score_label.pack(side='left', expand='yes', fill='x')

            # Create the layout of the buttons.
            new_button = tk.Button(self.button_frame, text='New Simulation', command=self.new)
            action_button = tk.Button(self.button_frame, text='Action', command=self.action)
            fog_button = tk.Button(self.button_frame, text='Fog of War', command=self.fow)

            new_button.pack(side='left', expand='yes', fill='x')
            action_button.pack(side='left', expand='yes', fill='x')
            fog_button.pack(side='left', expand='yes', fill='x')

            # Load the images for the world.
            image_grid         = Image.open('./images/grid.png')
            image_agent_right  = Image.open('./images/agent_right.png')
            image_agent_left   = Image.open('./images/agent_left.png')
            image_agent_up     = Image.open('./images/agent_up.png')
            image_agent_down   = Image.open('./images/agent_down.png')
            image_arrow        = Image.open('./images/arrow.png')
            image_wumpus_alive = Image.open('./images/wumpus_alive.png')
            image_wumpus_dead  = Image.open('./images/wumpus_dead.png')
            image_pit          = Image.open('./images/pit.png')
            image_gold         = Image.open('./images/gold.png')
            image_glitter      = Image.open('./images/glitter.png')
            image_stench       = Image.open('./images/stench.png')
            image_scream       = Image.open('./images/stench.png')
            image_wind         = Image.open('./images/wind.png')
            image_bump         = Image.open('./images/bump.png')

            image_new_game     = Image.open('./images/new_game.png')
            image_game_over    = Image.open('./images/game_over.png')
            image_victory      = Image.open('./images/victory.png')

            # Image primitives.
            self.prim_grid         = image_grid.resize((100, 100), Image.NEAREST)
            self.prim_agent_left   = image_agent_left.resize((100, 100), Image.NEAREST)
            self.prim_agent_right  = image_agent_right.resize((100, 100), Image.NEAREST)
            self.prim_agent_up     = image_agent_up.resize((100, 100), Image.NEAREST)
            self.prim_agent_down   = image_agent_down.resize((100, 100), Image.NEAREST)
            self.prim_arrow        = image_arrow.resize((100, 100), Image.NEAREST)
            self.prim_wumpus_alive = image_wumpus_alive.resize((100, 100), Image.NEAREST)
            self.prim_wumpus_dead  = image_wumpus_dead.resize((100, 100), Image.NEAREST)
            self.prim_pit          = image_pit.resize((100, 100), Image.NEAREST)
            self.prim_gold         = image_gold.resize((100, 100), Image.NEAREST)
            self.prim_glitter      = image_glitter.resize((100, 100), Image.NEAREST)
            self.prim_scream       = image_scream.resize((100, 100), Image.NEAREST)
            self.prim_stench       = image_stench.resize((100, 100), Image.NEAREST)
            self.prim_wind         = image_wind.resize((100, 100), Image.NEAREST)
            self.prim_bump         = image_bump.resize((100, 100), Image.NEAREST)
            self.prim_new_game     = image_new_game.resize((400, 400), Image.NEAREST)
            self.prim_game_over    = image_game_over.resize((400, 400), Image.NEAREST)
            self.prim_victory      = image_victory.resize((400, 400), Image.NEAREST)

            photo_world = ImageTk.PhotoImage(self.world)
            self.world_label = tk.Label(self.sim_frame, image=photo_world)
            self.world_label.image = photo_world

            # self.world_label.bind('<Configure>', self.resize)
            self.world_label.pack()
            self.update_world()

        def key_press(self, event):
            print('Pressed: ', event)

        def resize(self, event):
            new_width = event.width
            new_height = event.height
            resized_world = self.world.resize((new_width, new_height))
            photo_resized_world = ImageTk.PhotoImage(resized_world)
            self.world_label.configure(image=photo_resized_world)

        def change_cell(self, location, prim_comb, blend=False):
            """ Changes a given cell to a primitive combination where the
                coordinates refer to the reference (1, 1) at the bottom left
                of the grid.
            """
            try:
                # Map to the python image coordinates.
                (i, j) = location
                y = (400 - j*100)
                x = (i - 1)*100
                box = (x, y, x + 100, y + 100)
            except ValueError:
                raise ValueError
            if not blend:
                self.world.paste(prim_comb, box)
            else:
                temp = self.world.crop(box)
                mask = temp.convert('L')
                mask = mask.point(lambda x: 0 if x < 250 else 255, 'L')
                temp.paste(prim_comb, (0, 0), mask)
                self.world.paste(temp, box)

        def change_world(self, new_world, blend=False):
            """ Changes the entire world at once.
            """
            (x, y) = new_world.size
            if blend:
                self.world = Image.blend(self.world, new_world, 0.5)
            else:
                self.world.paste(new_world, (0, 0, x, y))

        def update_world(self):
            """ Update the world, by blending together the image primitives for
                each cell.
            """
            if self.new_sim:
                self.change_world(self.prim_new_game)
            elif not self.sim.agent.health:
                self.change_world(self.prim_game_over, blend=True)
            elif not self.sim.agent.in_cave and self.sim.agent.health and not self.sim.gold.grabbed:
                self.change_world(self.prim_game_over, blend=True)
            elif not self.sim.agent.in_cave and self.sim.agent.health and self.sim.gold.grabbed:
                self.change_world(self.prim_victory)
            else:
                # The image displayed on the screen.
                self.world = Image.new('RGBA', (4*100, 4*100), 'white')
                self.update_grid()
                self.update_agent()
                self.update_gold()
                self.update_pits()
                self.update_wumpus()
                self.update_percepts()

            # Return the final photo of the updated world.
            photo_world = ImageTk.PhotoImage(self.world)
            self.world_label.config(image=photo_world)
            self.world_label.image = photo_world

        def update_grid(self):
            """ Updates the grey grid of each cell.
            """
            for i in range(1, 5):
                for j in range(1, 5):
                    self.change_cell((i, j), self.prim_grid)

        def update_agent(self):
            """ Updates the agent in the world.
            """
            if self.sim.agent.health:
                if self.sim.agent.orientation == 0:
                    self.change_cell(self.sim.agent.location, self.prim_agent_right, blend=True)
                if self.sim.agent.orientation == 1:
                    self.change_cell(self.sim.agent.location, self.prim_agent_up, blend=True)
                if self.sim.agent.orientation == 2:
                    self.change_cell(self.sim.agent.location, self.prim_agent_left, blend=True)
                if self.sim.agent.orientation == 3:
                    self.change_cell(self.sim.agent.location, self.prim_agent_down, blend=True)

                if self.sim.agent.arrow:
                    self.change_cell(self.sim.agent.location, self.prim_arrow, blend=True)

        def update_wumpus(self):
            """ Updates the wumpus in the world.
            """
            if self.sim.wumpus.health:
                self.change_cell(self.sim.wumpus.location, self.prim_wumpus_alive, blend=True)
            else:
                self.change_cell(self.sim.wumpus.location, self.prim_wumpus_dead, blend=True)

        def update_gold(self):
            """ Updates the gold in the world.
            """
            if not self.sim.gold.in_pit and not self.sim.gold.grabbed:
                self.change_cell(self.sim.gold.location, self.prim_gold, blend=True)

        def update_pits(self):
            """ Updates the pits in the world.
            """
            for pit in self.sim.pits.pits:
                    self.change_cell(pit.location, self.prim_pit, blend=True)

        def update_breezes(self):
            # Update breezes.
            for breeze in self.sim.pits.breezes:
                if breeze.location == self.sim.agent.location or not self.fog:
                    self.change_cell(breeze.location, self.prim_wind, blend=True)
                    breeze.known = True

        def update_stenches(self):
            # Update stenches.
            for stench in self.sim.wumpus.stenches:
                if stench.location == self.sim.agent.location or not self.fog:
                    self.change_cell(stench.location, self.prim_stench, blend=True)

        def update_glitter(self):
            # Update glitter.
            if (self.sim.gold.location == self.sim.agent.location or not self.fog) and not self.sim.gold.in_pit:
                self.change_cell(self.sim.gold.location, self.prim_glitter, blend=True)

        def update_scream(self):
            # Update scream
            if self.sim.wumpus.scream:
                for (i, j) in itertools.product(range(1, 5), range(1, 5)):
                    self.change_cell((i, j), self.prim_scream, blend=True)

        def update_bump(self):
            # Update bump.
            if self.sim.agent.bump:
                self.change_cell(self.sim.agent.location, self.prim_bump, blend=True)

        def update_percepts(self):
            """ Updates the percepts of the agent in the current state.
            """
            self.update_breezes()
            self.update_stenches()
            self.update_glitter()
            self.update_scream()
            self.update_bump()

        def update_info(self):
            if self.new_sim:
                health_text = ''
                time_text   = ''
                action_text = ''
                score_text  = ''
            else:
                health_text = 'Health: %i' % self.sim.agent.health
                time_text = 'Time-step: %i' % self.sim.time
                action_text = 'Last action: %s' % self.sim.last_action
                score_text = 'Score: %s' % self.sim.score

            self.health_label.configure(text=health_text)
            self.time_label.configure(text=time_text)
            self.action_label.configure(text=action_text)
            self.score_label.configure(text=score_text)

        def run(self):
            self.root.mainloop()
            self.sim.quit()

        def new(self):
            self.new_sim = True
            self.sim.new()
            self.update_world()
            self.update_info()

        def action(self):
            if self.new_sim:
                self.new_sim = False
            else:
                self.sim.action()
            self.update_world()
            self.update_info()

        def fow(self):
            self.fog = not self.fog
            self.update_world()


def main():
    try:
        if DEBUG:
            pdb.set_trace()
        wsa = WumpusSimulatorArgs()
        wsa.parse()
        ws = WumpusSimulator(wsa.args.gui)
        pdb.set_trace()
        ws.start()
    except KeyboardInterrupt:
        # Close gui thread!
        print('\nClosing.')
        sys.exit(1)

if __name__ == '__main__':
    main()
