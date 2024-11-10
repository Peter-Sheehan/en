import random
import wsn_simpy.wsnsimpy as wsp

# Constants
TX_RANGE = 500  # Transmission range
NUM_DEVICES = 50
DISCOVERY_DURATION = 5  # seconds
HELLO_TIMEOUT = 0.1  # Max random delay for HELLO response
RETRY_DISCOVERY_INTERVAL = 5  # Time between retry phases

class CentralNode(wsp.Node):
    def __init__(self, sim, id, pos):
        super().__init__(sim, id, pos)
        self.phy = wsp.DefaultPhyLayer(self)
        self.mac = CustomMacLayer(self)  # Use the custom MAC layer
        self.tx_range = TX_RANGE
        self.discovered_ids = []  # List to store discovered node IDs
        self.missing_ids = list(range(1, NUM_DEVICES + 1))  # Track all nodes initially

    def run(self):
        """Main function for the central node to control behavior."""
        while self.missing_ids:
            yield self.timeout(DISCOVERY_DURATION)
            self.log(f"Central Node {self.id} starts discovery. Missing nodes: {self.missing_ids}")
            
            # Broadcast the DISCOVERY message with the list of missing nodes
            pdu = wsp.PDU(self.phy, 20, src=self.id, dest='broadcast', type='DISCOVERY', data=self.missing_ids)
            self.phy.send_pdu(pdu)
            self.log(f"Central Node {self.id} sent DISCOVERY with missing nodes: {self.missing_ids}")

            # Allow time for devices to respond
            yield self.timeout(RETRY_DISCOVERY_INTERVAL)

            # Update missing nodes after discovery phase
            self.missing_ids = [i for i in range(1, NUM_DEVICES + 1) if i not in self.discovered_ids]

            # Log missing nodes if any remain
            if self.missing_ids:
                self.log(f"Central Node {self.id} still missing responses from nodes: {self.missing_ids}")
            else:
                self.log(f"Central Node {self.id} discovered all nodes: {self.discovered_ids}")

    def on_receive_pdu(self, pdu):
        """Process received PDUs from regular nodes."""
        if pdu.type == 'HELLO' and pdu.src not in self.discovered_ids:
            self.discovered_ids.append(pdu.src)
            self.log(f"Central Node {self.id} received HELLO from Node {pdu.src}")

class RegularNode(wsp.Node):
    def __init__(self, sim, id, pos):
        super().__init__(sim, id, pos)
        self.phy = wsp.DefaultPhyLayer(self)
        self.mac = CustomMacLayer(self)  # Use the custom MAC layer
        self.tx_range = TX_RANGE
        self.received_discovery = False
        self.responded = False  # Track whether this node has responded

    def run(self):
        """Main function for the regular nodes to control behavior."""
        self.log(f"Regular Node {self.id} waiting for DISCOVERY (PHY range: {self.tx_range})")
        
        # Wait for DISCOVERY messages to trigger responses
        while True:
            yield self.timeout(0.1)

    def on_receive_pdu(self, pdu):
        """Process received PDUs from the central node."""
        if pdu.type == 'DISCOVERY':
            self.log(f"Regular Node {self.id} received DISCOVERY from Node {pdu.src}")

            # Check if this node needs to respond (included in the discovery list)
            if not self.responded or self.id in pdu.data:
                self.responded = True
                random_delay = random.uniform(0, HELLO_TIMEOUT)
                self.log(f"Regular Node {self.id} scheduling HELLO in {random_delay} seconds")
                self.sim.delayed_exec(random_delay, self.send_hello)

    def send_hello(self):
        """Send HELLO PDU back to the central node."""
        pdu = wsp.PDU(self.phy, 20, src=self.id, dest=0, type='HELLO', data="HELLO")
        self.phy.send_pdu(pdu)
        self.log(f"Regular Node {self.id} sent HELLO to CentralNode (Node 0)")

# Custom Mac Layer (same as earlier to handle DISCOVERY and HELLO PDUs)
class CustomMacLayer(wsp.DefaultMacLayer):
    def on_receive_pdu(self, pdu):
        """Custom MAC layer to handle DISCOVERY and HELLO PDUs."""
        # Log reception of PDU at MAC layer
        self.node.log(f"Custom MAC Layer received PDU: {pdu.type} at {self.node.id}")
        
        # Forward DISCOVERY and HELLO PDUs to the node's on_receive_pdu
        if pdu.type in ['DISCOVERY', 'HELLO']:
            self.node.on_receive_pdu(pdu)
        else:
            # Call the original MAC behavior for other types of PDUs (like 'data')
            super().on_receive_pdu(pdu)

# Setup the simulation
sim = wsp.Simulator(until=60, timescale=1)

# Add the central node
sim.add_node(CentralNode, pos=(50, 50))

# Add regular nodes at fixed positions within transmission range
for i in range(1, NUM_DEVICES + 1):
    position = (random.uniform(45, 55), random.uniform(45, 55))  # Devices closer to the central node
    sim.add_node(RegularNode, pos=position)

# Run the simulation
sim.run()
