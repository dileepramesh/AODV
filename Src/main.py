import subprocess, sys, shlex

# Print the banner!
print("This program implements the AODV protocol")

# Get the number of nodes from the user
n = input("Enter the number of nodes: ")
try:
    n = int(n)
except:
    print("Invalid Input")
    sys.exit(0)
    
if (n <= 1):
    print("There should be more than 1 node in the network")
    sys.exit(0)

print("There are " + str(n) + " node(s) in the AODV network")

# Spawn a new console for each node. They will each run the node.py program
for i in range(n):
    node_id = "n" + str(i + 1)
    cmd = "x-terminal-emulator -e 'sudo python3.2 node.py " + str(n) + " " + node_id + "'"
    process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
    #process.wait()

# Spawn a new terminal for the tester process. This will run the tester.py
# program
cmd1 = "x-terminal-emulator -e 'sudo python3.2 tester.py " + str(n) + "'"
process1 = subprocess.Popen(shlex.split(cmd1), stdout=subprocess.PIPE)

print (process.returncode)
