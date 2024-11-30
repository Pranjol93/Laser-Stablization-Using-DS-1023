# This code gets energy values from epics sent by server, predicst next energy using average of previous 2 shots, sets delay chip, saves energy that has been sent by server in csv,
#with timestamp, also it uses another thread to get the values from queue, save it along with predicted shot and delay value. It creates 2 csv file in total.
# Import necessary libraries for EPICS channel access tools
from cothread.catools import caget, caput, camonitor
# Import threading and queue libraries for handling concurrency
import threading
import queue
# Import time and random libraries for timing and randomization
import time
import random
# Import cothread library for cooperative threading
import cothread
# Import SPI communication library
import spidev
# Import datetime library for handling date and time
import datetime
# Import RPi.GPIO for Raspberry Pi GPIO control
import RPi.GPIO as GPIO
# Import math and numpy libraries for mathematical operations and array handling
import math
import numpy as np
# Import datetime for timestamp generation
from datetime import datetime
# Import CSV library for writing data to CSV files
import csv
 
# Retrieve initial preset energy reference value from EPICS PV
preset_eref = caget("Laser-Energy-Stablization:EREF")
print(preset_eref)  # Print the retrieved reference value
 
# # Retrieve initial energy value from EPICS PV
# energy = caget("Laser-Energy-Stablization:Energy1")
# print(energy)  # Uncomment to print the initial energy value
 
# Function to create a stepped array for delays
def create_stepped_array(initial_value, step_size, num_elements):
    # Calculate the stop value based on the initial value, step size, and number of elements
    stop_value = initial_value + step_size * num_elements
    # Create the array with the specified range and step size
    array = np.arange(initial_value, stop_value, step_size)
    # Ensure the array has the exact number of desired elements
    return array[:num_elements]
 
# Function to append rows to the initial array for delay settings
def append_rows(initial_array, num_iterations, increment):
    # Reshape initial_array to be a 2D array with one row
    array = initial_array.reshape(1, -1)
   
    for _ in range(num_iterations):
        # Create the next row by adding 'increment' to the last row
        next_row = array[-1] + increment
        # Append the new row to the array
        array = np.vstack((array, next_row))
   
    return array
 
# Function to find the closest value in a matrix to the target value
def find_closest_value(matrix, target_value):
    # Calculate the absolute differences between matrix elements and the target value
    differences = np.abs(matrix - target_value)
   
    # Find the index of the minimum difference
    min_index = np.unravel_index(np.argmin(differences), matrix.shape)
   
    # Get the closest value based on the index
    closest_value = matrix[min_index]
   
    return closest_value, min_index
 
# Function to calculate the offset based on predicted energy, reference energy, and a given offset
def calculate_offset(epred, eref, offset):
    # Check if eref is not zero to avoid division by zero
    if eref == 0:
        raise ValueError("eref must not be zero.")
   
    # Calculate the value of the expression for the offset
    result = offset - 3.2e-06 * math.log(float(epred) / float(eref))
    return result
 
# Function to generate a file name for client-received energy data
def get1_file_name():
    now = datetime.now()  # Get the current date and time
    return now.strftime("Client_Received_Hill_energy_meter_data_%Y%m%d_%H%M%S.csv")
 
# Function to generate a file name for client-predicted energy data
def get2_file_name():
    now = datetime.now()  # Get the current date and time
    return now.strftime("Client_Predicted_Hill_energy_meter_data_%Y%m%d_%H%M%S.csv")
 
# Function to get the current timestamp in a specific format
def get_current_timestamp():
    now = datetime.now()  # Get the current date and time
    hours = now.strftime("%H")  # Extract hours
    minutes = now.strftime("%M")  # Extract minutes
    seconds = now.strftime("%S")  # Extract seconds
    nanoseconds = now.microsecond * 1000  # Convert microseconds to nanoseconds
    return f"{hours}:{minutes}:{seconds}.{nanoseconds}"  # Return formatted timestamp
 
# Idle delay settings
initial_value = 45.525e-09  # Initial delay value (in seconds) - Change as needed
# Delay step size
step_size = 5e-09  # Step size for delay increments (in seconds)
# Total steps for one chip
num_elements = 256  # Number of delay steps for the chip
# Create initial stepped array for delay settings
initial_array = create_stepped_array(initial_value, step_size, num_elements)
# Number of times to append the incremented row
num_iterations = 255  # Number of iterations for delay rows
# Append rows to the delay array
result_array = append_rows(initial_array, num_iterations, step_size)
print("Delay_matrix Created!!!")  # Print confirmation that the delay matrix is created
 
# Initialize SPI communication with the Raspberry Pi
spi = spidev.SpiDev()
spi.open(0, 0)  # Open SPI bus 0, device 0
spi.max_speed_hz = 500000  # Set SPI communication speed
 
# Set up GPIO pins for Raspberry Pi
GPIO.setwarnings(False)  # Disable GPIO warnings
GPIO.setmode(GPIO.BCM)  # Use BCM GPIO numbering
# Set latch pin as output
latch_pin = 25
GPIO.setup(latch_pin, GPIO.OUT)
 
# Create a FIFO queue with a maximum size of 2
fifo_queue = queue.Queue(maxsize=2)
# Create a mutex lock for thread synchronization
mutex = threading.Lock()
 
# Generate file names for client-received and predicted energy data
file_name1 = get1_file_name()
file_name2 = get2_file_name()
 
# Open CSV file to write client-received energy data
file1 = open(file_name1, mode='a', newline='')
 
# Initialize CSV writer for the received data file
writer1 = csv.writer(file1)
# Write the header row in the received data file
writer1.writerow(['Timestamp1', 'Channel1_Power'])
 
# Open CSV file to write client-predicted energy data
file2 = open(file_name2, mode='a', newline='')
 
# Initialize CSV writer for the predicted data file
writer2 = csv.writer(file2)
# Write the header row in the predicted data file
writer2.writerow(['Timestamp1', 'Channel1_Power', 'Prediction', 'Delay'])
 
# Callback function to process received energy data
def callback(value):
    with mutex:  # Acquire the mutex lock
        if not fifo_queue.full():
            # Put the data into the FIFO queue
            fifo_queue.put(value)
 
# List to store energy values
energy_list = []
 
# Consumer function to process the energy data from the queue
def consumer():
    while True:
        # Acquire the mutex lock
        with mutex:
            if not fifo_queue.empty():
                # Get the data from the FIFO queue
                data = fifo_queue.get()
                # Append received energy data to the energy list
                energy_list.append(data)
                global preset_eref  # Use the global preset energy reference
                eref = preset_eref  # Retrieve reference energy
                offset = 2.604691e-06  # Offset value - Change as needed
               
                # If not enough energy data, use reference energy as predicted energy
                if len(energy_list) < 2:
                    epred = eref
                else:
                    # Average of the last two energy values as the prediction
                    epred = (energy_list[-1] + energy_list[-2]) / 2
               
                # Calculate the delay offset based on predicted energy and reference energy
                result = calculate_offset(epred, eref, 2.604691e-06)
                # Write the timestamp, received energy, predicted energy, and calculated delay to the predicted data file
                writer2.writerow([get_current_timestamp(), data, epred, result])
                # Find the closest delay values for chip 1 and chip 2
                closest_value, (row, column) = find_closest_value(result_array, result)
                print(f"The delay settings for chip1 is {row}, chip2 is {column}.")
  
                values = [row, column]  # Values to send via SPI
                for i in values:
                    # Set latch pin high before sending SPI data
                    GPIO.output(latch_pin, GPIO.HIGH)
                    # Send the value via SPI
                    spi.xfer2([int(i)])
                    # Set latch pin low after sending SPI data
                    GPIO.output(latch_pin, GPIO.LOW)
 
# Start the consumer thread to process energy data
consumer_thread = threading.Thread(target=consumer)
consumer_thread.start()
 
# Monitor the EPICS PV for energy changes and use the callback function to handle them
camonitor('Laser-Energy-Stablization:Energy1', callback)
 
# Wait indefinitely for the cothread to finish
cothread.WaitForQuit()