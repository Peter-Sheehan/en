import random
import wsn_simpy.wsnsimpy as wsp

class MyNode(wsp.Node):
    def __init__(self, sim, id, pos):
        super().__init__(sim, id, pos)
        # Set the transmission range
        self.tx_range = 100
        # Create a default physical layer
        self.phy = wsp.DefaultPhyLayer(self)
        # No dedicated MAC layer, we are implementing it
        self.mac = self
        # To keep track of the sequence number
        self.seq_num = 0

    def run(self):
        """Main function to control node behavior."""
        if self.id != 0:
            # This is a transmitter node
            self.log(f"Transmitter Node {self.id} is at position {self.pos}")
            while True:
                # Introduce random backoff to avoid collisions
                backoff_time = random.uniform(0, 1)  # Random delay between 0 and 1 second
                yield self.timeout(1 + backoff_time)  # Wait for 1 second plus a random backoff

                # Create a PDU with data and the node's ID
                pdu = wsp.PDU(None, 20, data=f"MyData_from_Node_{self.id}", nodeid=self.id)
                # Send the PDU
                self.phy.send_pdu(pdu)
                # Log the action
                self.log(f"Node {self.id} sent PDU with data {pdu.data}")
                self.seq_num += 1

    # Method called by the PHY layer when receiving a PDU
    def on_receive_pdu(self, pdu):
        """Receiver (node 0) processes and logs received PDUs"""
        if self.id == 0:  # This is the receiver
            # Use pdu.nodeid instead of pdu.source, as source does not exist
            print(f"Receiver (Node {self.id}) received PDU from Node {pdu.nodeid}: {pdu.data}")

# Set up the simulation
sim = wsp.Simulator(until=10, timescale=1)

# Add the receiver node (Node 0) at (10,10)
n1 = sim.add_node(MyNode, (10, 10))  # Receiver node
print(f"Receiver Node 0 is at position {(10, 10)}")

# Add 10 transmitter nodes at random positions
for i in range(1, 11):  # IDs 1 to 10
    position = (random.random() * 50, random.random() * 50)
    sim.add_node(MyNode, position)
    print(f"Transmitter Node {i} is placed at position {position}")

# Run the simulation for 10 seconds
sim.run()

# Print the transmission statistics for the receiver
print(f"Receiver (Node 0) stats: TX={n1.phy.stat.total_tx}, RX={n1.phy.stat.total_rx}, "
      f"Collisions={n1.phy.stat.total_collision}")
