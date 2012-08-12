# Imports
import threading, logging, socket, os, select, re
from threading import Timer

# Defines
AODV_HELLO_INTERVAL         =   10
AODV_HELLO_TIMEOUT          =   30
AODV_PATH_DISCOVERY_TIME    =   30
AODV_ACTIVE_ROUTE_TIMEOUT   =   300

# Class Definition
class aodv(threading.Thread):

    # Constructor
    def __init__(self):
        threading.Thread.__init__(self)
        self.node_id = ""
        self.num_nodes = 0
        self.seq_no = 0
        self.rreq_id = 0
        self.listener_port = 0
        self.aodv_port = 0
        self.tester_port = 0
        self.listener_sock = 0
        self.aodv_sock = 0
        self.tester_sock = 0
        self.log_file = ""
        self.command = ""
        self.status = ""
        self.neighbors = dict()
        self.routing_table = dict()
        self.message_box = dict()
        self.rreq_id_list = dict()
        self.pending_msg_q = []
        self.status = "Active"
        self.hello_timer = 0
    
    # Set the Node ID
    def set_node_id(self, nid):
        self.node_id = nid
    
    # Set the number of nodes in the network
    def set_node_count(self, count):
        self.num_nodes = count
    
    # Get the port associated with the listener thread for the given node
    def get_listener_thread_port(self, node):
        port = {'n1':  1000,
                'n2':  1100,
                'n3':  1200,
                'n4':  1300,
                'n5':  1400,
                'n6':  1500,
                'n7':  1600,
                'n8':  1700,
                'n9':  1800,
                'n10': 1900}[node]
                
        return port

    # Get the port used to communicate with the listener thread for this node
    def get_listener_port(self, node):
        port = {'n1':  2000,
                'n2':  2100,
                'n3':  2200,
                'n4':  2300,
                'n5':  2400,
                'n6':  2500,
                'n7':  2600,
                'n8':  2700,
                'n9':  2800,
                'n10': 2900}[node]
                
        return port

    # Get the port associated with sending and receiving AODV messages
    def get_aodv_port(self, node):
        port = {'n1':  3000,
                'n2':  3100,
                'n3':  3200,
                'n4':  3300,
                'n5':  3400,
                'n6':  3500,
                'n7':  3600,
                'n8':  3700,
                'n9':  3800,
                'n10': 3900}[node]
                
        return port

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

    # Create / Restart the lifetime timer for the given route
    def aodv_restart_route_timer(self, route, create):
        if (create == False):
            timer = route['Lifetime']
            timer.cancel()

        timer = Timer(AODV_ACTIVE_ROUTE_TIMEOUT, 
                      self.aodv_process_route_timeout, [route])
        route['Lifetime'] = timer
        route['Status'] = 'Active'
        timer.start()
    
    # Send a message
    def aodv_send(self, destination, destination_port, message):
        try:
            message_bytes = bytes(message, 'utf-8')
            self.aodv_sock.sendto(message_bytes, 0, 
                                  ('localhost', destination_port))
        except:
            pass    
    
    # Send the hello message to all the neighbors
    def aodv_send_hello_message(self):
        try:
            # Send message to each neighbor
            for n in self.neighbors.keys():
                message_type = "HELLO_MESSAGE"
                sender = self.node_id
                message_data = "Hello message from " + str(self.node_id)
                message = message_type + ":" + sender + ":" + message_data
                port = self.get_aodv_port(n)
                self.aodv_send(n, int(port), message)
                logging.debug("['" + message_type + "', '" + sender + "', " + 
                              "Sending hello message to " + str(n) + "']")
        
            # Restart the timer
            self.hello_timer.cancel()
            self.hello_timer = Timer(AODV_HELLO_INTERVAL, self.aodv_send_hello_message, ())
            self.hello_timer.start()
            
        except:
            pass
        
    # Process incoming hello messages
    def aodv_process_hello_message(self, message):
        logging.debug(message)
        sender = message[1]

        # Get the sender's ID and restart its neighbor liveness timer
        try:
            if (sender in self.neighbors.keys()):
                neighbor = self.neighbors[sender]
                timer = neighbor['Timer-Callback']
                timer.cancel()
                timer = Timer(AODV_HELLO_TIMEOUT, 
                              self.aodv_process_neighbor_timeout, [sender])
                self.neighbors[sender] = {'Neighbor': sender, 
                                          'Timer-Callback': timer}
                timer.start()
            
                # Restart the lifetime timer
                route = self.routing_table[sender]
                self.aodv_restart_route_timer(route, False)

            else:
                #
                # We come here when we get a hello message from a node that
                # is not there in our neighbor list. This happens when a 
                # node times out and comes back up again. Add the node to
                # our neighbor table.
                #
                timer = Timer(AODV_HELLO_TIMEOUT, 
                              self.aodv_process_neighbor_timeout, [sender])
                self.neighbors[sender] = {'Neighbor': sender, 
                                          'Timer-Callback': timer}
                timer.start()
            
                # Update the routing table as well
                if (sender in self.routing_table.keys()):
                    route = self.routing_table[sender]
                    self.aodv_restart_route_timer(route, False)
                else:
                    self.routing_table[sender] = {'Destination': sender, 
                                                  'Destination-Port': self.get_aodv_port(sender), 
                                                  'Next-Hop': sender, 
                                                  'Next-Hop-Port': self.get_aodv_port(sender), 
                                                  'Seq-No': '1', 
                                                  'Hop-Count': '1', 
                                                  'Status': 'Active'}
                    self.aodv_restart_route_timer(self.routing_table[sender], True)

        except KeyError:
            # This neighbor has not been added yet. Ignore the message.
            pass

    # Process incoming application message
    def aodv_process_user_message(self, message):
        
        # Get the message contents, sender and receiver
        sender = message[1]
        receiver = message[2]
        msg = message[3]
        
        # Check if the message is for us
        if (receiver == self.node_id):

            # Add the message to the message box
            self.message_box[msg] = {'Sender': sender, 'Message': msg}
        
            # Log the message and notify the user
            logging.debug(message)
            print("New message arrived. Issue 'view_messages' to see the contents")
        
        else:
            # 
            # Forward the message by looking up the next-hop. We should have a 
            # route for the destination.
            #
            # TODO update lifetime for the route
            route = self.routing_table[receiver]
            next_hop = route['Next-Hop']
            next_hop_port = int(route['Next-Hop-Port'])
            self.aodv_restart_route_timer(route, False)
            message = message[0] + ":" + message[1] + ":" + message[2] + ":" + message[3]
            self.aodv_send(next_hop, next_hop_port, message)
            logging.debug("['USER_MESSAGE', '" + sender + " to " + receiver + "', " + msg + "']")

    # Process an incoming RREQ message
    def aodv_process_rreq_message(self, message):
        
        # Extract the relevant parameters from the message
        message_type = message[0]
        sender = message[1]
        hop_count = int(message[2]) + 1
        message[2] = str(hop_count)
        rreq_id = int(message[3])
        dest = message[4]
        dest_seq_no = int(message[5])
        orig = message[6]
        orig_seq_no = int(message[7])
        orig_port = self.get_aodv_port(orig)
        sender_port = self.get_aodv_port(sender)

        # Ignore the message if we are not active
        if (self.status == "Inactive"):
            return

        logging.debug("['" + message[0] + "', 'Received RREQ to " + message[4] + " from " + sender + "']")

        # Discard this RREQ if we have already received this before
        if (orig in self.rreq_id_list.keys()):
            node_list = self.rreq_id_list[orig]
            per_node_rreq_id_list = node_list['RREQ_ID_List']
            if rreq_id in per_node_rreq_id_list.keys():
                logging.debug("['RREQ_MESSAGE', 'Ignoring duplicate RREQ (" + orig + ", " + str(rreq_id) + ") from " + sender + "']")
                return

        # This is a new RREQ message. Buffer it first
        if (orig in self.rreq_id_list.keys()):
            per_node_list = self.rreq_id_list[orig]
        else:
            per_node_list = dict()
        path_discovery_timer = Timer(AODV_PATH_DISCOVERY_TIME, 
                                     self.aodv_process_path_discovery_timeout, 
                                     [orig, rreq_id])
        per_node_list[rreq_id] = {'RREQ_ID': rreq_id, 
                                  'Timer-Callback': path_discovery_timer}
        self.rreq_id_list[orig] = {'Node': self.node_id, 
                                   'RREQ_ID_List': per_node_list}
        path_discovery_timer.start()

        # 
        # Check if we have a route to the source. If we have, see if we need
        # to update it. Specifically, update it only if:
        #
        # 1. The destination sequence number for the route is less than the
        #    originator sequence number in the packet
        # 2. The sequence numbers are equal, but the hop_count in the packet
        #    + 1 is lesser than the one in routing table
        # 3. The sequence number in the routing table is unknown
        #
        # If we don't have a route for the originator, add an entry

        if orig in self.routing_table.keys():
            # TODO update lifetime timer for this route
            route = self.routing_table[orig]
            if (int(route['Seq-No']) < orig_seq_no):
                route['Seq-No'] = orig_seq_no
                self.aodv_restart_route_timer(route, False)
            elif (int(route['Seq-No']) == orig_seq_no):
                if (int(route['Hop-Count']) > hop_count):
                    route['Hop-Count'] = hop_count
                    route['Next-Hop'] = sender
                    route['Next-Hop-Port'] = sender_port
                    self.aodv_restart_route_timer(route, False)
            elif (int(route['Seq-No']) == -1):
                route['Seq-No'] = orig_seq_no
                self.aodv_restart_route_timer(route, False)

        else:
            # TODO update lifetime timer for this route
            self.routing_table[orig] = {'Destination': str(orig), 
                                        'Destination-Port': str(orig_port),
                                        'Next-Hop': str(sender),
                                        'Next-Hop-Port': str(sender_port),
                                        'Seq-No': str(orig_seq_no),
                                        'Hop-Count': str(hop_count),
                                        'Status': 'Active'}
            self.aodv_restart_route_timer(self.routing_table[orig], True)

        # 
        # Check if we are the destination. If we are, generate and send an
        # RREP back.
        #
        if (self.node_id == dest):
            self.aodv_send_rrep(orig, sender, dest, dest, 0, 0)
            return

        # 
        # We are not the destination. Check if we have a valid route
        # to the destination. If we have, generate and send back an
        # RREP.
        #
        if (dest in self.routing_table.keys()):
            # Verify that the route is valid and has a higher seq number
            route = self.routing_table[dest]
            status = route['Status']
            route_dest_seq_no = int(route['Seq-No'])
            if (status == "Active" and route_dest_seq_no >= dest_seq_no):
                self.aodv_send_rrep(orig, sender, self.node_id, dest, route_dest_seq_no, int(route['Hop-Count']))
                return
        else:
            # Rebroadcast the RREQ
            self.aodv_forward_rreq(message)

    # Process an incoming RREP message
    def aodv_process_rrep_message(self, message):
        # Extract the relevant fields from the message
        message_type = message[0]
        sender = message[1]
        hop_count = int(message[2]) + 1
        message[2] = str(hop_count)
        dest = message[3]
        dest_seq_no = int(message[4])
        orig = message[5]

        logging.debug("['" + message_type + "', 'Received RREP for " + dest + " from " + sender + "']")

        # Check if we originated the RREQ. If so, consume the RREP.
        if (self.node_id == orig):
            # 
            # Update the routing table. If we have already got a route for
            # this estination, compare the hop count and update the route
            # if needed.
            #
            if (dest in self.routing_table.keys()):
                route = self.routing_table[dest]
                route_hop_count = int(route['Hop-Count'])
                if (route_hop_count > hop_count):
                    route['Hop-Count'] = str(hop_count)
                    self.aodv_restart_route_timer(self.routing_table[dest], False)
            else:
                self.routing_table[dest] = {'Destination': dest,
                                            'Destination-Port': self.get_aodv_port(dest),
                                            'Next-Hop': sender,
                                            'Next-Hop-Port': self.get_aodv_port(sender),
                                            'Seq-No': str(dest_seq_no),
                                            'Hop-Count': str(hop_count),
                                            'Status': 'Active'}
                self.aodv_restart_route_timer(self.routing_table[dest], True)

            # Check if we have any pending messages to this destination
            for m in self.pending_msg_q:
                msg = re.split(':', m)
                d = msg[2]
                if (d == dest):
                    # Send the pending message and remove it from the buffer
                    next_hop = sender
                    next_hop_port = self.get_aodv_port(next_hop)
                    self.aodv_send(next_hop, int(next_hop_port), m)
                    logging.debug("['USER_MESSAGE', '" + msg[1] + " to " + msg[2] + " via " + next_hop + "', '" + msg[3] + "']")
                    print("Message sent")
           
                    self.pending_msg_q.remove(m)

        else:
            # 
            # We need to forward the RREP. Before forwarding, update
            # information about the destination in our routing table.
            #
            if (dest in self.routing_table.keys()):
                route = self.routing_table[dest]
                route['Status'] = 'Active'
                route['Seq-No'] = str(dest_seq_no)
                self.aodv_restart_route_timer(route, False)
            else:
                self.routing_table[dest] = {'Destination': dest,
                                            'Destination-Port': self.get_aodv_port(dest),
                                            'Next-Hop': sender,
                                            'Next-Hop-Port': self.get_aodv_port(sender),
                                            'Seq-No': str(dest_seq_no),
                                            'Hop-Count': str(hop_count),
                                            'Status': 'Active'}
                self.aodv_restart_route_timer(self.routing_table[dest], True)
                # TODO update/add a lifetime timer for the route

            # Now lookup the next-hop for the source and forward it
            route = self.routing_table[orig]
            next_hop = route['Next-Hop']
            next_hop_port = int(route['Next-Hop-Port'])
            self.aodv_forward_rrep(message, next_hop, next_hop_port)

    # Process an incoming RERR message
    def aodv_process_rerr_message(self, message):
        # Extract the relevant fields from the message
        message_type = message[0]
        sender = message[1]
        dest = message[3]
        dest_seq_no = int(message[4])

        if (self.node_id == dest):
            return

        logging.debug("['" + message_type + "', 'Received RERR for " + dest + " from " + sender + "']")

        # 
        # Take action only if we have an active route to the destination with
        # sender as the next-hop
        #
        if (dest in self.routing_table.keys()):
            route = self.routing_table[dest]
            if (route['Status'] == 'Active' and route['Next-Hop'] == sender):
                # Mark the destination as inactive
                route['Status'] = "Inactive"

                # Forward the RERR to all the neighbors
                self.aodv_forward_rerr(message)
            else:
                logging.debug("['" + message_type + "', 'Ignoring RERR for " + dest + " from " + sender + "']")

    # Broadcast an RREQ message for the given destination
    def aodv_send_rreq(self, destination, destination_seq_no):
        
        # Increment our sequence number
        self.seq_no = self.seq_no + 1
        
        # Increment the RREQ_ID
        self.rreq_id = self.rreq_id + 1
        
        # Construct the RREQ packet
        message_type = "RREQ_MESSAGE"
        sender = self.node_id
        hop_count = 0
        rreq_id = self.rreq_id
        dest = destination
        dest_seq_no = destination_seq_no
        orig = self.node_id
        orig_seq_no = self.seq_no
        message = message_type + ":" + sender + ":" + str(hop_count) + ":" + str(rreq_id) + ":" + str(dest) + ":" + str(dest_seq_no) + ":" + str(orig) + ":" + str(orig_seq_no)
        
        # Broadcast the RREQ packet to all the neighbors
        for n in self.neighbors:
            port = self.get_aodv_port(n)
            self.aodv_send(n, int(port), message)
            logging.debug("['" + message_type + "', 'Broadcasting RREQ to " + dest + "']")
            
        # Buffer the RREQ_ID for PATH_DISCOVERY_TIME. This is used to discard duplicate RREQ messages
        if (self.node_id in self.rreq_id_list.keys()):
            per_node_list = self.rreq_id_list[self.node_id]
        else:
            per_node_list = dict()
        path_discovery_timer = Timer(AODV_PATH_DISCOVERY_TIME, 
                                     self.aodv_process_path_discovery_timeout, 
                                     [self.node_id, rreq_id])
        per_node_list[rreq_id] = {'RREQ_ID': rreq_id, 
                                  'Timer-Callback': path_discovery_timer}
        self.rreq_id_list[self.node_id] = {'Node': self.node_id, 
                                           'RREQ_ID_List': per_node_list}
        path_discovery_timer.start()

    # 
    # Rebroadcast an RREQ request (Called when RREQ is received by an
    # intermediate node)
    #
    def aodv_forward_rreq(self, message):
        msg = message[0] + ":" + self.node_id + ":" + message[2] + ":" + message[3] + ":" + message[4] + ":" + message[5] + ":" + message[6] + ":" + message[7]
        for n in self.neighbors:
            port = self.get_aodv_port(n)
            self.aodv_send(n, int(port), msg)
            logging.debug("['" + message[0] + "', 'Rebroadcasting RREQ to " + message[4] + "']")

    # Send an RREP message back to the RREQ originator
    def aodv_send_rrep(self, rrep_dest, rrep_nh, rrep_src, rrep_int_node, dest_seq_no, hop_count):
        # 
        # Check if we are the destination in the RREP. If not, use the
        # parameters passed.
        #
        if (rrep_src == rrep_int_node):
            # Increment the sequence number and reset the hop count
            self.seq_no = self.seq_no + 1
            dest_seq_no = self.seq_no
            hop_count = 0

        # Construct the RREP message
        message_type = "RREP_MESSAGE"
        sender = self.node_id
        dest = rrep_int_node
        orig = rrep_dest
        message = message_type + ":" + sender + ":" + str(hop_count) + ":" + str(dest) + ":" + str(dest_seq_no) + ":" + str(orig)

        # Now send the RREP to the RREQ originator along the next-hop
        port = self.get_aodv_port(rrep_nh)
        self.aodv_send(rrep_nh, int(port), message)
        logging.debug("['" + message_type + "', 'Sending RREP for " + rrep_int_node + " to " + rrep_dest + " via " + rrep_nh + "']")

    # 
    # Forward an RREP message (Called when RREP is received by an
    # intermediate node)
    #
    def aodv_forward_rrep(self, message, next_hop, next_hop_port):
        msg = message[0] + ":" + self.node_id + ":" + message[2] + ":" + message[3] + ":" + message[4] + ":" + message[5]
        self.aodv_send(next_hop, next_hop_port, msg)
        logging.debug("['" + message[0] + "', 'Forwarding RREP for " + message[5] + " to " + next_hop + "']")

    # Generate and send a Route Error message
    def aodv_send_rerr(self, dest, dest_seq_no):
        # Construct the RERR message
        message_type = "RERR_MESSAGE"
        sender = self.node_id
        dest_count = '1'
        dest_seq_no = dest_seq_no + 1
        message = message_type + ":" + sender + ":" + dest_count + ":" + dest + ":" + str(dest_seq_no)

        # Now broadcast the RREQ message
        for n in self.neighbors.keys():
            port = self.get_aodv_port(n)
            self.aodv_send(n, int(port), message)

        logging.debug("['" + message_type + "', 'Sending RERR for " + dest + "']")

    # Forward a Route Error message
    def aodv_forward_rerr(self, message):
        msg = message[0] + ":" + self.node_id + ":" + message[2] + ":" + message[3] + ":" + message[4]
        for n in self.neighbors.keys():
            port = self.get_aodv_port(n)
            self.aodv_send(n, int(port), msg)

        logging.debug("['" + message[0] + "', 'Forwarding RERR for " + message[3] + "']")

    # Handle neighbor timeouts
    def aodv_process_neighbor_timeout(self, neighbor):
        
        # Update the routing table. Mark the route as inactive.
        route = self.routing_table[neighbor]
        route['Status'] = 'Inactive'

        # Log a message
        logging.debug("aodv_process_neighbor_timeout: " + neighbor + " went down")

        # Send an RERR to all the neighbors
        self.aodv_send_rerr(neighbor, int(route['Seq-No']))

        # Try to repair the route
        dest_seq_no = int(route['Seq-No']) + 1
        self.aodv_send_rreq(neighbor, dest_seq_no)
        
    # Handle Path Discovery timeouts
    def aodv_process_path_discovery_timeout(self, node, rreq_id):
        
        # Remove the buffered RREQ_ID for the given node
        if node in self.rreq_id_list.keys():
            node_list =  self.rreq_id_list[node]
            per_node_rreq_id_list = node_list['RREQ_ID_List']
            if rreq_id in per_node_rreq_id_list.keys():
                per_node_rreq_id_list.pop(rreq_id)
    
    # Handle route timeouts
    def aodv_process_route_timeout(self, route):

        # Remove the route from the routing table
        key = route['Destination']
        self.routing_table.pop(key)

        # 
        # If the destination is a neighbor, remove it from the neighbor table
        # as well
        #
        if (key in self.neighbors):
            self.neighbors.pop(key)

        logging.debug("aodv_process_route_timeout: removing " + key + " from the routing table.")

    # Simulate a link-up event for the current node
    def aodv_simulate_link_up(self, from_tester):
        #
        # Resume sending hello messages. This command is used for debugging 
        # purposes to simulate link failures and RERR messages.
        #

        # Don't proceed if the node is already up
        if (self.status == "Active"):
            print("Node is already active!")
            return

        # Start the hello timer again
        self.hello_timer = Timer(AODV_HELLO_INTERVAL, self.aodv_send_hello_message, ())
        self.hello_timer.start()

        # Restart all the lifetime timers in the routing table
        for r in self.routing_table.keys():
            route = self.routing_table[r]
            timer = Timer(AODV_ACTIVE_ROUTE_TIMEOUT, 
                          self.aodv_process_route_timeout, [route])
            route['Lifetime'] = timer
            timer.start()

        self.status = "Active"

        logging.debug("Activating node " + self.node_id)
        print("Activated node " + self.node_id + ". This node will resume sending hello messages.")
    
    # Take the neighbor set for the current node from the user
    def aodv_add_neighbor(self, from_tester):
        if (from_tester == False):
            neighbors_raw = input("Enter the neighbors for the current node, separated by a space: ")
            neighbors = str.split(neighbors_raw)
        else:
            neighbors = str.split(self.command[2], ' ')

        for n in neighbors:
            timer = Timer(AODV_HELLO_TIMEOUT, 
                          self.aodv_process_neighbor_timeout, [n])
            self.neighbors[n] = {'Neighbor': n, 'Timer-Callback': timer}
            timer.start()

        print("Neighbors added successfully: ", self.neighbors.keys())
        
        # Update the routing table. Setup direct routes for each added neighbor.
        for n in neighbors:
            # TODO: Add lifetime timer
            dest = str(n)
            dest_port = str(self.get_aodv_port(n))
            nh = str(n)
            nh_port = str(self.get_aodv_port(n))
            seq = '1'
            hop_count = '1'
            status = 'Active'
            
            self.routing_table[dest] = {'Destination': dest, 
                                        'Destination-Port': dest_port, 
                                        'Next-Hop': nh, 
                                        'Next-Hop-Port': nh_port, 
                                        'Seq-No': seq, 
                                        'Hop-Count': hop_count, 
                                        'Status': status}
            self.aodv_restart_route_timer(self.routing_table[dest], True)
            
        # Start a timer to start sending hello messages periodically
        self.hello_timer = Timer(AODV_HELLO_INTERVAL, self.aodv_send_hello_message, ())
        self.hello_timer.start()
        
    # Simulate a link-down event for the current node
    def aodv_simulate_link_down(self, from_tester):
        #
        # Stop sending hello messages. Keep the neighbor list as it is.
        # This command is used for debugging purposes to simulate link
        # failures and RERR messages.
        #

        # Don't proceed if the node is already down
        if (self.status == "Inactive"):
            print("Node is already down!")
            return

        # Cancel the hello timer
        self.hello_timer.cancel()

        # Stop all the lifetime timers in the routing table
        for r in self.routing_table.keys():
            route = self.routing_table[r]
            timer = route['Lifetime']
            timer.cancel()

        self.status = "Inactive"

        logging.debug("Deactivating node " + self.node_id)
        print("Deactivated node " + self.node_id + ". This node will stop sending hello messages.")
        
    # Delete the messages buffered for the given node
    def aodv_delete_messages(self, from_tester):
        # Remove all the messages from the message box
        self.message_box.clear()
        print("Message box has been cleared")
                    
    # Send a message to a peer
    def aodv_send_message(self, from_tester):
        
        # Get the command sent by the listener thread / tester process
        command = self.command
        if (from_tester == False):
            source = command[1]
            dest = command[2]
            message_data = command[3]
        else:
            source = command[1]
            dest = command[2]
            message_data = command[3]
        
        # Format the message
        message_type = "USER_MESSAGE"
        message = message_type + ":" + source + ":" + dest + ":" + message_data
        
        # First check if we have a route for the destination
        if dest in self.routing_table.keys():
            # Route already present. Get the next-hop for the destination.
            destination = self.routing_table[dest]
            
            if (destination['Status'] == 'Inactive'):
                # We don't have a valid route. Broadcast an RREQ.
                self.aodv_send_rreq(dest, destination['Seq-No'])
            else:
                next_hop = destination['Next-Hop']
                next_hop_port = destination['Next-Hop-Port']
                self.aodv_send(next_hop, int(next_hop_port), message)
                # TODO: update lifetime here as the route was used
                self.aodv_restart_route_timer(destination, False)
                logging.debug("['USER_MESSAGE', '" + source + " to " + dest + " via " + next_hop + "', '" + message_data + "']")
                print("Message sent")
        else:
            # Initiate a route discovery message to the destination
            self.aodv_send_rreq(dest, -1)

            # Buffer the message and resend it once RREP is received
            self.pending_msg_q.append(message)

    # Display the routing table for the current node
    def aodv_show_routing_table(self, from_tester):
        print("")
        print("There are " + str(len(self.routing_table)) + " active route(s) in the routing-table")
        print("")
        
        print("Destination     Next-Hop     Seq-No     Hop-Count     Status")
        print("------------------------------------------------------------")
        for r in self.routing_table.values():
            print(r['Destination'] + "              " + r['Next-Hop'] + "           " + r['Seq-No'] + "          " + r['Hop-Count'] + "             " + r['Status'])
        print("")
        
        self.status = "Success"

    # Dump the log file to the console
    def aodv_show_log(self, from_tester):
        for line in open(self.log_file, 'r'):
            print(line)
            
    # Return the buffered messages back to the node
    def aodv_show_messages(self, from_tester):
        print("")
        print("There are " + str(len(self.message_box)) + " message(s) in the message-box")
        print("")
        
        print("Sender     Message")
        print("------------------")
        for m in self.message_box.values():
            print(m['Sender'] + "         " + m['Message'])
        print("")
        
        self.status = "Success"
        
    # Default action handler
    def aodv_default(self):
        pass
    
    # Thread start routine
    def run(self):
        
        # Setup logging
        self.log_file = "aodv_log_" + self.node_id
        FORMAT = "%(asctime)s - %(message)s"
        logging.basicConfig(filename=self.log_file, 
                            level=logging.DEBUG, 
                            format=FORMAT)
        
        # Get the listener port
        self.listener_port = self.get_listener_port(self.node_id)
        self.listener_thread_port = self.get_listener_thread_port(self.node_id)
        
        # Get the AODV port
        self.aodv_port = self.get_aodv_port(self.node_id)
        
        # Get the tester port
        self.tester_port = self.get_tester_port(self.node_id)

        # 
        # Create sockets to communicate with the listener thread, tester
        # process and other nodes in the network
        #
        self.listener_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener_sock.bind(('localhost', self.listener_port))
        self.listener_sock.setblocking(0)
        self.listener_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tester_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.tester_sock.bind(('localhost', self.tester_port))
        self.tester_sock.setblocking(0)
        self.tester_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.aodv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.aodv_sock.bind(('localhost', self.aodv_port))
        self.aodv_sock.setblocking(0)
        self.aodv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        logging.debug("node " + self.node_id + " started on port " + str(self.aodv_port) + " with pid " + str(os.getpid()))
        
        # Set the node status
        self.status = "Active"

        # Setup the socket list we expect to read via select()
        inputs = [self.listener_sock, self.tester_sock, self.aodv_sock]
        outputs = []
        
        # Run the main loop
        while inputs:
            readable, _, _ = select.select(inputs, outputs, inputs)
            for r in readable:
                if r is self.listener_sock:
                    # We got a message from the listener thread. Process it.
                    command, _ = self.listener_sock.recvfrom(100)
                    command = command.decode('utf-8')
                    command = re.split(':', command)
                    command_type = command[0]
                    self.command = command

                    if command_type == "NODE_ACTIVATE":
                        self.aodv_simulate_link_up(False)
                    elif command_type == "ADD_NEIGHBOR":
                        self.aodv_add_neighbor(False)
                    elif command_type == "NODE_DEACTIVATE":
                        self.aodv_simulate_link_down(False)
                    elif command_type == "DELETE_MESSAGES":
                        self.aodv_delete_messages(False)
                    elif command_type == "SEND_MESSAGE":
                        self.aodv_send_message(False)
                    elif command_type == "SHOW_ROUTE":
                        self.aodv_show_routing_table(False)
                    elif command_type == "VIEW_LOG":
                        self.aodv_show_log(False)
                    elif command_type == "VIEW_MESSAGES":
                        self.aodv_show_messages(False)
                    else:
                        self.aodv_default()
                     
                    # Send the status back to the listener thread
                    message = bytes(self.status, 'utf-8')
                    self.listener_sock.sendto(message, 0, 
                                              ('localhost', 
                                               self.listener_thread_port))
                    
                elif r is self.tester_sock:
                    # We got a message from the tester process. Process it.
                    command, _ = self.tester_sock.recvfrom(100)
                    command = command.decode('utf-8')
                    command = re.split(':', command)
                    command_type = command[0]
                    self.command = command

                    if command_type == "NODE_ACTIVATE":
                        self.aodv_simulate_link_up(True)
                    elif command_type == "ADD_NEIGHBOR":
                        self.aodv_add_neighbor(True)
                    elif command_type == "NODE_DEACTIVATE":
                        self.aodv_simulate_link_down(True)
                    elif command_type == "DELETE_MESSAGES":
                        self.aodv_delete_messages(True)
                    elif command_type == "SEND_MESSAGE":
                        self.aodv_send_message(True)
                    elif command_type == "SHOW_ROUTE":
                        self.aodv_show_routing_table(True)
                    elif command_type == "VIEW_LOG":
                        self.aodv_show_log(True)
                    elif command_type == "VIEW_MESSAGES":
                        self.aodv_show_messages(True)
                    else:
                        self.aodv_default()

                    self.status = "Success"
                    message = bytes(self.status, 'utf-8')
                    self.tester_sock.sendto(message, 0, 
                                            ('localhost', 5000))

                elif r is self.aodv_sock:
                    # We got a message from the network
                    message, _ = self.aodv_sock.recvfrom(200)
                    message = message.decode('utf-8')
                    message = re.split(':', message)
                    
                    message_type = message[0]
                    if (message_type == "HELLO_MESSAGE"):
                        self.aodv_process_hello_message(message)
                    elif (message_type == "USER_MESSAGE"):
                        self.aodv_process_user_message(message)
                    elif (message_type == "RREQ_MESSAGE"):
                        self.aodv_process_rreq_message(message)
                    elif (message_type == "RREP_MESSAGE"):
                        self.aodv_process_rrep_message(message)
                    elif (message_type == "RERR_MESSAGE"):
                        self.aodv_process_rerr_message(message)
           
# End of File
