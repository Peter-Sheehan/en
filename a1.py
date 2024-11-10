import random
import wsn_simpy.wsnsimpy as wsp

# Constants
TX_RANGE = 150  # Transmission range for all devices
NUM_DEVICES = 10
DISCOVERY_DURATION = 5  # Discovery period in seconds
HELLO_TIMEOUT = 0.01  # Max random delay for HELLO response in seconds
SLOT_DURATION = 0.1  # Slot duration in seconds (10 ms)
SCHED_START_DELAY = 0.5  # Delay before communication can start
SIM_DURATION = 50  # Total simulation time in seconds (changed from 10 to 50)

# Custom Mac Layer to handle specific PDU types
class CustomMacLayer(wsp.DefaultMacLayer):
    def on_receive_pdu(self, pdu):
        """Custom MAC layer to handle DISCOVERY, HELLO, SCHED, and DATA PDUs."""
        # Log reception of PDU at MAC layer
        self.node.log(f"Received PDU from {pdu.src}: {pdu.type}")
        
        if pdu.type == 'BS-HELLO' and pdu.dest == 'broadcast':
            self.node.on_receive_pdu(pdu)
        elif pdu.type == 'DEV-HELLO' and self.node.id == 0:  # Base Station ID is 0
            self.node.on_receive_pdu(pdu)
        elif pdu.type == 'SCHED' and pdu.dest == 'broadcast':
            self.node.on_receive_pdu(pdu)
        elif pdu.type == 'DATA':
            if self.node.id == 0 and pdu.dest == 0:  # Base Station processes data
                self.node.on_receive_pdu(pdu)
            else:
                super().on_receive_pdu(pdu)


class BaseStation(wsp.Node):
    def __init__(self, sim, id, pos):
        super().__init__(sim, id, pos)
        self.phy = wsp.DefaultPhyLayer(self)
        self.mac = CustomMacLayer(self)
        self.tx_range = TX_RANGE
        self.discovered_devices = []  # List of device IDs discovered during discovery period
        self.schedule = []  # Schedule with device ID and slot numbers

    def run(self):
        """Main method to control the base station's behavior."""
        yield self.timeout(5.0)  # Wait 5 seconds before starting discovery
        self.log(f"Discovery starts")
        
        # Broadcast the BS-HELLO message
        hello_pdu = wsp.PDU(self.phy, 20, src=self.id, dest='broadcast', type='BS-HELLO')
        self.phy.send_pdu(hello_pdu)
        self.log(f"Base Station {self.id} broadcasted BS-HELLO.")
        
        # Wait for devices to respond with DEV-HELLO messages
        yield self.timeout(DISCOVERY_DURATION)
        self.log(f"Base Station {self.id} discovery period ended. Devices discovered: {self.discovered_devices}")

        # Create the schedule for the devices
        self.create_schedule()

        # Broadcast the schedule to all devices
        sched_pdu = wsp.PDU(self.phy, 20, src=self.id, dest='broadcast', type='SCHED', data={
            'num_devices': len(self.schedule),
            'dev_slots': self.schedule,
            'start_delay': SCHED_START_DELAY
        })
        self.phy.send_pdu(sched_pdu)
        self.log(f"Base Station {self.id} sent schedule: {self.schedule}")

        # Wait for data transmissions from devices
        yield self.timeout(SIM_DURATION - self.now)

    def create_schedule(self):
        """Create the schedule based on discovered devices."""
        for idx, device_id in enumerate(self.discovered_devices):
            self.schedule.append((device_id, idx))  # Assign each device a unique slot

    def on_receive_pdu(self, pdu):
        """Process received PDUs from devices."""
        if pdu.type == 'DEV-HELLO' and pdu.src not in self.discovered_devices:
            self.discovered_devices.append(pdu.src)
            self.log(f"Base Station {self.id} received DEV-HELLO from Device {pdu.src}")
        elif pdu.type == 'DATA':
            self.log(f"Base Station {self.id} received DATA from Device {pdu.src}")


class Device(wsp.Node):
    def __init__(self, sim, id, pos):
        super().__init__(sim, id, pos)
        self.phy = wsp.DefaultPhyLayer(self)
        self.mac = CustomMacLayer(self)
        self.tx_range = TX_RANGE
        self.slot_number = None  # Slot number assigned to the device
        self.schedule_frame_length = None  # Total time frame for one schedule round
        self.start_delay = None  # Delay before the schedule starts

    def run(self):
        """Main method to control device behavior."""
        self.log(f"Waiting for HELLO")
        
        # Wait for the HELLO message from the base station
        while True:
            yield self.timeout(0.1)

    def on_receive_pdu(self, pdu):
        """Process received PDUs from the base station."""
        if pdu.type == 'BS-HELLO':
            self.log(f"Received PDU from {pdu.src}: {pdu.type}")
            delay = random.uniform(0, HELLO_TIMEOUT)
            self.sim.delayed_exec(delay, self.send_hello)

        elif pdu.type == 'SCHED':
            self.process_schedule(pdu)

    def send_hello(self):
        """Send DEV-HELLO PDU back to the base station."""
        pdu = wsp.PDU(self.phy, 20, src=self.id, dest=0, type='DEV-HELLO', data=self.id)
        self.phy.send_pdu(pdu)
        self.log(f"Device {self.id} sent DEV-HELLO to Base Station.")

    def process_schedule(self, pdu):
        """Process the schedule PDU and retrieve the slot information."""
        self.start_delay = pdu.data['start_delay']
        num_devices = pdu.data['num_devices']
        self.schedule_frame_length = num_devices * SLOT_DURATION

        # Find the slot assigned to this device
        for dev_id, slot_num in pdu.data['dev_slots']:
            if dev_id == self.id:
                self.slot_number = slot_num
                self.log(f"Device {self.id} received schedule. Slot number: {self.slot_number}")
                # Start transmitting at the assigned slot time
                self.sim.delayed_exec(self.start_delay + self.slot_number * SLOT_DURATION, self.send_data)
                return

        # If no slot is assigned, log that the device didn't get a slot
        self.log(f"Device {self.id} didn't get a slot :(")

    def send_data(self):
        """Send DATA PDU to the base station."""
        if self.now < SIM_DURATION:  # Check if still within simulation time
            pdu = wsp.PDU(self.phy, 20, src=self.id, dest=0, type='DATA', data=f"Data from {self.id}")
            self.phy.send_pdu(pdu)
            self.log(f"Device {self.id} sent DATA to Base Station.")
            
            # Schedule next transmission
            if self.now + self.schedule_frame_length < SIM_DURATION:
                self.sim.delayed_exec(self.schedule_frame_length, self.send_data)


# Setup the simulation
sim = wsp.Simulator(until=SIM_DURATION, timescale=1)

# Add the base station at the center (50,50)
sim.add_node(BaseStation, pos=(50, 50))

# Add 10 devices randomly within a 100x100 area
for i in range(1, NUM_DEVICES + 1):
    position = (random.uniform(0, 100), random.uniform(0, 100))
    sim.add_node(Device, pos=position)

# Run the simulation
sim.run()

# After the simulation, retrieve the base station and print TX, RX, and Collision statistics
for node in sim.nodes:
    if isinstance(node, BaseStation):
        tx_count = node.phy.stat.total_tx  # Number of transmissions (TX)
        rx_count = node.phy.stat.total_rx  # Number of receptions (RX)
        collisions = node.phy.stat.total_collision  # Number of collisions
        print(f"n1 stats: TX={tx_count} RX={rx_count} Collisions={collisions}")
        break
