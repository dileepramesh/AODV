# Imports
import sys, socket, time

TESTER_PORT = 5000

# Class Definition
class tester():

    # Constructor
    def __init__(self):
        self.num_nodes = 0
        self.sock = 0
        self.port = 0
        self.command = ""

    # Get the tester port associated with this node
    def get_tester_port(self, node):
        port = {'n1':  5100,
                'n2':  5200,
                'n3':  5300,
                'n4':  5400,
                'n5':  5500,
                'n6':  5600,
                'n7':  5700,
                'n8':  5800,
                'n9':  5900,
                'n10': 6000}[node]
                
        return port

    # Wait for the response from protocol handler thread
    def wait_for_response(self):
        # Wait for the status
        (msg, _) = self.sock.recvfrom(10)
        status = msg.decode('utf-8')

    # Default routine called when invalid command is parsed. Do nothing.
    def command_default(self):
        pass

    # Process a command to activate a node
    def process_activate_link(self):
        # Command format: line-number command-name target-node
        target_node = self.command[2]
        message = "NODE_ACTIVATE:" + str(target_node)
        target_port = self.get_tester_port(target_node)
        message_bytes = bytes(message, 'utf-8')
        self.sock.sendto(message_bytes, 0, ('localhost', target_port))
        print("Sending command " + message + " to node " + target_node)
        self.wait_for_response()

    # Process a command to add neighbors
    def process_add_neighbors(self):
        # Command format: line-number command-name neighbor-node 'to' target-node
        target_node = self.command[4]
        neighbor_node = self.command[2]
        message = "ADD_NEIGHBOR:" + str(target_node) + ":" + str(neighbor_node)
        target_port = self.get_tester_port(target_node)
        message_bytes = bytes(message, 'utf-8')
        self.sock.sendto(message_bytes, 0, ('localhost', target_port))
        print("Sending command " + message + " to node " + target_node)
        self.wait_for_response()

    # Process a command to deactivate a node
    def process_deactivate_link(self):
        # Command format: line-number command-name target-node
        target_node = self.command[2]
        message = "NODE_DEACTIVATE:" + str(target_node)
        target_port = self.get_tester_port(target_node)
        message_bytes = bytes(message, 'utf-8')
        self.sock.sendto(message_bytes, 0, ('localhost', target_port))
        print("Sending command " + message + " to node " + target_node)
        self.wait_for_response()

    # Process a command to delete the message box for a node
    def process_delete_messages(self):
        # Command format: line-number command-name target-node
        target_node = self.command[2]
        message = "DELETE_MESSAGES:" + str(target_node)
        target_port = self.get_tester_port(target_node)
        message_bytes = bytes(message, 'utf-8')
        self.sock.sendto(message_bytes, 0, ('localhost', target_port))
        print("Sending command " + message + " to node " + target_node)
        self.wait_for_response()

    # Process a command to send a message from one node to another
    def process_send_message(self):
        # Command format: line-number command-name source-node 'to' dest-node message
        target_node = self.command[2]
        dest_node = self.command[4]
        msg = self.command[5]
        msg_words = str.split(msg, '@')
        msg = ""
        for m in msg_words:
            msg = msg + m + " "
        message = "SEND_MESSAGE:" + str(target_node) + ":" + str(dest_node) + ":" + msg
        target_port = self.get_tester_port(target_node)
        message_bytes = bytes(message, 'utf-8')
        self.sock.sendto(message_bytes, 0, ('localhost', target_port))
        print("Sending command " + message + " to node " + target_node)
        self.wait_for_response()

    # process a command to display a given node's routing table
    def process_show_route(self):
        # Command format: line-number command-name target-node
        target_node = self.command[2]
        message = "SHOW_ROUTE:" + str(target_node)
        target_port = self.get_tester_port(target_node)
        message_bytes = bytes(message, 'utf-8')
        self.sock.sendto(message_bytes, 0, ('localhost', target_port))
        print("Sending command " + message + " to node " + target_node)
        self.wait_for_response()

    # Process a command to display a given node's log file
    def process_show_log(self):
        # Command format: line-number command-name target-node
        target_node = self.command[2]
        message = "VIEW_LOG:" + str(target_node)
        target_port = self.get_tester_port(target_node)
        message_bytes = bytes(message, 'utf-8')
        self.sock.sendto(message_bytes, 0, ('localhost', target_port))
        print("Sending command " + message + " to node " + target_node)
        self.wait_for_response()

    # process a command to display a give node's message box
    def process_show_messages(self):
        # Command format: line-number command-name target-node
        target_node = self.command[2]
        message = "VIEW_MESSAGES:" + str(target_node)
        target_port = self.get_tester_port(target_node)
        message_bytes = bytes(message, 'utf-8')
        self.sock.sendto(message_bytes, 0, ('localhost', target_port))
        print("Sending command " + message + " to node " + target_node)
        self.wait_for_response()

    # Called when user issues help. Dump the list of available commands.
    def help(self):
        print("The following list of commands are available:")
        print("run_test_script : Take a script as input and run the test cases in it")

    # Take the script from the user and run it
    def run_test_script(self):
        fname = input("Enter the name of the script: ")

        try:
            # Open the script and read all the lines upfront
            f = open(fname, 'r')
            lines = f.readlines()

            # Parse each line and process it
            for l in lines:
                # Split the line to individual words
                words = str.split(l)
                self.command = words

                {'activate_link'    : self.process_activate_link,
                 'add_neighbors'    : self.process_add_neighbors,
                 'deactivate_link'  : self.process_deactivate_link,
                 'delete_messages'  : self.process_delete_messages,
                 'send_message'     : self.process_send_message,
                 'show_route'       : self.process_show_route,
                 'show_log'         : self.process_show_log,
                 'show_messages'    : self.process_show_messages}.get(words[1], self.command_default)()

                time.sleep(1)

        except:
            print("File not found. Please try again.")

    # Default routine called when invalid command is issued. Do nothing.
    def default(self):
        if (len(self.command) == 0):
            pass
        else:
            print("Invalid Command")

    # Main routine
    def main(self, n):
        
        # Store the node count
        self.num_nodes = n

        # Setup the port to be used for communication with data nodes
        self.port = TESTER_PORT
        
        # Setup socket to communicate with the AODV protocol handler thread
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('localhost', self.port))
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Set the prompt
        prompt = "TESTER" + "> "
        
        # Listen indefinitely for user inputs
        while (True):
            command = input(prompt)
            
            {'help'             : self.help,
             'run_test_script'  : self.run_test_script}.get(command, self.default)()

# Get the arguments passed by the driver program 
n = int(sys.argv[1])

# Instantiate the tester class and call its main method
tester = tester()
tester.main(n)
              
# End of File
