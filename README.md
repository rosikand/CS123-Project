# CS 123 Project - Visual Navigation with Pupper through LLM Path Planning 


## Project description 

For our final project for our robotic dog class (where we build a robotic dog called Pupper and program it using control, ROS 2, and RL), we have decided to work on visual navigation. Our goal is to harness the use of LLM’s to help plan and navigate Pupper. On demo day, we have pre-built environments that Pupper will be tasked with navigating. Essentially, each environment will be a 4x4 grid. Pupper will be placed at a spot on the grid. The user has access to a GUI (see below) where they can specify where pupper starts, its orientation, any obstacles present in the real environment, and the target destination. From here, our program takes in a string representing the state of the environment, as specified by the GUI, and passes it into an LLM. The LLM then maps out a navigation path to get pupper to the intended destination, while avoiding obstacles. Pupper has a high level api called Karel which consists of commands like “move(), turn_left(), turn_right()”. The LLM will output a sequence of commands in Karel for Pupper to use and navigate itself. 

Once the path has been determined, the next challenge is getting Pupper to actually follow the intended path, in the real environment. Pupper locomotion is trained using an RL policy that was given to us. However, it struggles to walk completely straight sometimes. For example, if you give Pupper a sequence of “move(), move(), move()” commands, it will likely veer off path and the errors compound. We are still exploring solutions to solve this problem but the main one is to use April Tags. April Tags are barcode-like images that can be placed in the environment to localize the navigator. The idea is that we will place April tags at each point in the grid, in the real life environment. Then, as pupper moves along, we will use its fisheye camera to get it to the current April tag it needs to get to. We call this process “search()”. Suppose we have a sequence like:

```
move()
move()
turn_left()
move()
move()
```

And suppose pupper starts at (1,1) and needs to get to (3,3) using this path planning. For each step, pupper will run the search function which will translate the first move() command into searching for the April tag at (1,2). Then, we use object detection via the fisheye camera to locate this April tag. Once the desired April tag is located, we use the fisheye camera to help pupper move to the desired target. Once the target is reached, the next target tag is determined. This process repeats until the destination is reached. 

## Progress so far 

We have built a Python-based GUI for our Pupper dog that represents a 4×4 grid environment complete with user-placed obstacles, a defined starting position and orientation for Pupper, and a specified goal block. Using this interface, we capture the entire grid state, obstacle locations, Pupper’s pose, and the target cell, and format it as input for Claude. From there, Claude processes the grid data and returns a sequence of Pupper commands that navigate the dog from its start to its goal. So far, we have verified that the pipeline successfully translates GUI configurations into executable instructions. From here, we now need to integrate this within the rest of the codebase to (1) orchestrate the LLM-outputted string of commands to Pupper’s actual commands in the API to get it to move and (2) to implement the April tag tracking system. We anticipate that some of our goals and objectives might need to change as we progress throughout the project. 

Here is a visual image of the GUI: 

<img width="645" alt="image" src="https://github.com/user-attachments/assets/746d4aae-dcf0-42fa-9b0b-70a7cfc5bb20" />



## Some upcoming questions 

1. I am trying to figure out how to start and properly scaffold the codebase. Before the final project, the class had us do labs where they provide starter code and we simply just fill in a few functions to complete the lab. But this time, we aren’t given any starter code. I am thinking of taking the code from the most relevant lab and go from there. Does this make sense? Or how should I properly scaffold the codebase for our project? 
    1. Note that the codebases for the labs are quite extensive and has tons of ROS 2 code that we absolutely shouldn’t rewrite. 
2. I see the project has having three main coding components: (1) the GUI system which interacts with the user and has the LLM do the path planning in the background; (2) the April tag search and visual tracking system to get pupper to stay on path; (3) mapping the commands generated to actually getting pupper to move with the Karel API and ROS 2 code. 
    1. This isn’t really a question, just mainly a comment. However, the question really is, how to scaffold the codebase given these three components. 
