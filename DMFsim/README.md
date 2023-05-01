# Virtual-Lab-On-A-Chip

Python 3.7, developed in Spyder.

This repository runs a virtual lab-on-a-chip for testing DNA assembly on a digital microflulidics grid.

There are four primary components in the hierarchy:
1) The Interpreter, which handles the job of deciding what instructions are necessary to assemble the user-defined gene sequence.
2) The Scheduler, which takes the instructions provided by the Interpreter and turns them into step-by-step commands for the Lab.
3) The AStar routing system, which calculates routes for the droplets when given starting point and destination by the Scheduler.
4) The Lab, which houses all of the Droplet and Gridpoint objects. It handles movement and basic DNA chemistry -- essentially just Watson-Crick pairing during Gibson ops.

The purpose is twofold: First, to provide a test-bed for developing routing control functions for an actual microfluidics lab. Second, to create a system that can quickly produce and record the necessary steps to create any given gene sequence within the symbol-linker constraints of the Gibson assembly.

Check the Tutorial script for a breakdown of how to run the code.
