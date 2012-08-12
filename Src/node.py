# Imports
import sys, listener, aodv

# Class Definition
class node():

    # Constructor
    def __init__(self):
        self.node_id = ""

    # Main routine
    def main(self, n, node_id):
        
        # Store the Node ID
        self.node_id = node_id
        
        # Initialize and start the listener thread
        listener_thread = listener.listener()
        listener_thread.set_node_id(node_id)
        listener_thread.set_node_count(n)
        listener_thread.start()
        
        # Initialize and start the protocol handler thread
        aodv_thread = aodv.aodv()
        aodv_thread.set_node_id(node_id)
        aodv_thread.set_node_count(n)
        aodv_thread.start()

# Get the arguments passed by the driver program 
n = int(sys.argv[1])
node_id = sys.argv[2]

# Instantiate the node class and call its main method
node = node()
node.main(n, node_id)

# End of File