'''Make sure raspberry-pi gpio 23 is connected to input of the chip1 (pin1), connect input BNC of prototype box to trigger box at 10 hz with amplitude 3 V'''

from softioc import softioc, builder  # Import softIOC for building EPICS IOCs
import cothread  # Import cothread for cooperative threading in Python
import spidev  # Import spidev for interfacing with SPI devices
import time  # Import time module for time-related functions
import RPi.GPIO as GPIO  # Import GPIO module to control Raspberry Pi GPIO pins
import datetime  # Import datetime for working with date and time
import random  # Import random module to generate random numbers
import numpy as np  # Import NumPy for numerical operations

# Set the record prefix for the IOC
builder.SetDeviceName("Laser-Energy-Stablization")

# Disable GPIO warnings and set the GPIO mode
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Set GPIO 23 as input for detecting rising edges from BNC Input
GPIO.setup(23, GPIO.IN)

# Get the current date and time
now = datetime.datetime.now()

# Function to generate a sequence of energies that form a stairstep pattern
def generate_stairstep(E_ref, t):
    ''' Generates a sequence of energies which will result in a stairstep pattern '''
    
    # Upper state lifetime of Ti:sapphire in seconds
    tau = 3.2e-6
    
    # Generate energy values based on the exponential decay formula
    E = E_ref * np.exp(t / tau)
    
    '''Repeat the energy values to form a stairstep pattern. Here 30 means, E (staircase energy) will be repeated 30 times'''
    E = np.tile(E, 30)
    
    # Save the generated energy values to a CSV file
    with open('StairStepEnergies.csv', 'w') as f:
        for delay, energy in zip(t, E):
            print('%.6g' % energy, file=f)  # Save each energy value to the file
    
    return E  # Return the generated energy values

# Generate the stairstep energy values using the generate_stairstep function
E = generate_stairstep(E_ref=10e-6, t=np.linspace(0, 800e-9, 21))

# Create EPICS records for the IOC
EREF = builder.aOut('EREF', initial_value=10e-06)  # Analog output record for the reference energy, it has been set as 10 micro joul
Energy1 = builder.aOut('Energy1', initial_value=E[0])  # Analog output record for the first energy
Energy2 = builder.aOut('Energy2', initial_value=9e-09)  # Analog output record for the second energy, this is a dummy value
timestamp = builder.stringIn('timestamp', initial_value=str(now))  # String input record for the timestamp

# Load the database and initialize the IOC
builder.LoadDatabase()
softioc.iocInit()

# Initialize a counter for the energy values
kk = 0

# Define the callback function for handling rising edges on GPIO 23
def rising_edge(channel):
    global Energy1  # Access the global Energy1 variable
    global Energy2  # Access the global Energy2 variable
    global kk  # Access the global counter variable

    # Get the current date and time
    now = datetime.datetime.now()
    
    # Set the Energy1 value to the current energy value in the sequence
    Energy1.set(E[kk])
    
    # Update the timestamp with the current time
    timestamp.set(str(now))
    
    # Print the current Energy1 value and timestamp
    print(Energy1.get())
    print(timestamp.get())
    
    # Increment the counter to move to the next energy value
    kk = kk + 1

# Set up an event to detect rising edges on GPIO 23 and call the rising_edge function
GPIO.add_event_detect(23, GPIO.RISING, callback=rising_edge)

# Enter an infinite loop to keep the program running
while 1:
    time.sleep(0.5)  # Sleep for 0.5 seconds in each iteration
