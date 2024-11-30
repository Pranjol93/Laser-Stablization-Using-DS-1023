from cothread.catools import caget, caput, camonitor  # Import cothread tools for interacting with EPICS
import threading  # Import threading module for creating threads
import queue  # Import queue module for creating FIFO queues
import time  # Import time module for time-related functions
import random  # Import random module for generating random numbers
import cothread  # Import cothread for cooperative threading
import spidev  # Import spidev for interfacing with SPI devices
import datetime  # Import datetime for working with date and time
import RPi.GPIO as GPIO  # Import GPIO module to control Raspberry Pi GPIO pins
import math  # Import math module for mathematical functions
import numpy as np  # Import NumPy for numerical operations

# Retrieve the preset EREF value from the EPICS IOC
preset_eref = caget("Laser-Energy-Stablization:EREF")
# Retrieve the Energy1 value from the EPICS IOC
energy = caget("Laser-Energy-Stablization:Energy1")

# Function to create an array of stepped values: Delay matrix creation
def create_stepped_array(initial_value, step_size, num_elements):
    # Calculate the stop value based on the initial value, step size, and number of elements
    stop_value = initial_value + step_size * num_elements

    # Create the array
    array = np.arange(initial_value, stop_value, step_size)
    
    # Ensure the array has the exact number of desired elements
    return array[:num_elements]

# Function to append incremented rows to an initial array: Delay matrix creation
def append_rows(initial_array, num_iterations, increment):
    # Reshape initial_array to be a 2D array with one row
    array = initial_array.reshape(1, -1)
    
    for _ in range(num_iterations):
        # Create the next row by adding 'increment' to the last row
        next_row = array[-1] + increment
        # Append the new row to the array
        array = np.vstack((array, next_row))
    
    return array

# Function to find the closest value in a matrix to a target value: Delay matrix visitor 
def find_closest_value(matrix, target_value):
    # Calculate the absolute differences
    differences = np.abs(matrix - target_value)
    
    # Find the index of the minimum difference
    min_index = np.unravel_index(np.argmin(differences), matrix.shape)
    
    # Get the closest value
    closest_value = matrix[min_index]
    
    return closest_value, min_index

# Function to calculate the offset based on given parameters
# output result: mathematically computed delay  
def calculate_offset(epred, eref, offset):
    # Check if eref is not zero to avoid division by zero
    if eref == 0:
        raise ValueError("eref must not be zero.")
    
    # Calculate the value of the expression
    result = offset - 3.2e-06 * math.log(float(epred) / float(eref))
    return result

# Set the initial delay value: This needs to be parameterized
initial_value = 42.103e-09
# Set the delay step size: This is to be parameterized
step_size = 5e-09  
# Set the total number of steps for one chip: to be parameterized
num_elements = 256
'''The purpose is to create a delay matrix which is 256*256 matrix, that has all the delay values'''
# Create the initial array of stepped values: creating the first row of delay matrix
initial_array = create_stepped_array(initial_value, step_size, num_elements)
# Set the number of times to append the incremented row
num_iterations = 255
# Append rows to the initial delay matrix to create the full matrix
result_array = append_rows(initial_array, num_iterations, step_size)
print("Delay_matrix Created!!!")

# Initialize the SPI interface
spi = spidev.SpiDev()
spi.open(0, 0)  # Open SPI bus 0, device 0
spi.max_speed_hz = 500000  # Set SPI speed to 500 kHz

# Set up GPIO on the Raspberry Pi
GPIO.setwarnings(False)  # Disable GPIO warnings
GPIO.setmode(GPIO.BCM)  # Set GPIO mode to BCM

# Set GPIO 25 as the latch pin output
latch_pin = 25
GPIO.setup(latch_pin, GPIO.OUT)

# Create a FIFO queue with a maximum size of 2
fifo_queue = queue.Queue(maxsize=2)

# Create a mutex lock for thread synchronization
mutex = threading.Lock()

# Callback function to handle incoming energy values from the EPICS IOC
def callback(value):
    # Acquire the mutex lock to ensure thread safety
    with mutex:
        if not fifo_queue.full():
            # Put the data into the FIFO queue if it's not full
            fifo_queue.put(value)
            print(f"Current Energy from Server: {value}")
            now = datetime.datetime.now()
            # Print the current time
            # print(now)

# List to store energy values
energy_list = []

# Consumer function to process the data from the queue
def consumer():
    while True:
        # Acquire the mutex lock to ensure thread safety
        with mutex:
            if not fifo_queue.empty():
                # Get the data from the FIFO queue
                data = fifo_queue.get()
                # Append the data to the energy list
                energy_list.append(data)
                
                global preset_eref
                eref = preset_eref  # Use the preset EREF value
                offset = 2.604691e-06  # Max Offset value

                # Use the previous energy value for prediction
                epred = energy_list[-1]

                # Calculate the result based on the predicted energy, eref and offset 
                result = calculate_offset(epred, 10e-6, 2.604691e-06)
                
                ''' Find the closest delay value in the result array (delay matrix) to the calculated result, which is row-column of the delay matrix. We need to set this row-column number in the chip'''
                closest_value, (row, column) = find_closest_value(result_array, result)
                
                # Print the delay settings for both chips
                print(f"The delay settings for chip1 is {row}, chip2 is {column}.")

                # Set the SPI values for both chips
                values = [row, column]
                for i in values:
                    GPIO.output(latch_pin, GPIO.HIGH)  # Set latch pin high
                    spi.xfer2([int(i)])  # Transfer SPI data
                    GPIO.output(latch_pin, GPIO.LOW)  # Set latch pin low

# Create and start the consumer thread
consumer_thread = threading.Thread(target=consumer)
consumer_thread.start()

# Monitor the 'Laser-Energy-Stablization:Energy1' PV for changes and call the callback function
camonitor('Laser-Energy-Stablization:Energy1', callback)

# Wait for the program to exit gracefully
cothread.WaitForQuit()