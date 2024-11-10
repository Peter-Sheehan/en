import wsn_simpy.wsnsimpy as wsp
import random
from functools import partial

class MyNode(wsp.Node):

    def __init__(self, sim, id, pos):
        super().__init__(sim, id, pos)
        # Transmission range
        self.tx_range = 100
        self.phy = wsp.DefaultPhyLayer(self)
        self.mac = self

    def on_receive_pdu(self, pdu):
        # Log out the source ID and the data contained in the PDU
        self.log(f"Received {pdu.data} from {pdu.source}")

    def run(self):
        # Only node with ID 1 will transmit
        if self.id == 1:
            yield self.sim.timeout(random.random())
            while True:
                # Node 1 transmits every 2 seconds
                yield self.sim.timeout(2)
                pdu = wsp.PDU(None,
                              20,   # PDU size, not important
                              data="Hello from node 1",
                              source=self.id)
                self.phy.send_pdu(pdu)
                self.log(f"Sent PDU from node {self.id}")
        else:
            # Other nodes only receive PDUs, no transmission
            yield self.sim.passivate()

# Create the simulator
sim = wsp.Simulator(until=20, timescale=1)

# Add 11 nodes, with random positions
for i in range(11):
    sim.add_node(MyNode, (random.random() * 50, random.random() * 50))

# Run the simulation
sim.run()
