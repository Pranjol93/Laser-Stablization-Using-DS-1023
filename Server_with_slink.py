# This code puts energy values acquired from slink channel-1 into epics at 10 hz rate, reads eref file, sets it in epics
# Import necessary modules
from softioc import softioc, builder  # Import SoftIOC for EPICS IOC creation
import cothread  # Import cothread for threading support
import spidev  # Import SPI device module for SPI communication
import time  # Import time module for timing functions
import RPi.GPIO as GPIO  # Import GPIO module for Raspberry Pi GPIO control
import datetime  # Import datetime module for date and time functions
import random  # Import random module for generating random numbers
import numpy as np  # Import NumPy for numerical operations
import serial  # Import serial module for serial communication
import time  # Import time module (redundant import, already imported)
from datetime import datetime  # Import datetime from datetime for more precise timestamping
import csv  # Import CSV module for handling CSV files
 
# Setup serial link (slink) with a device
def setup_slink2():
    # Configure the serial port (USB0) with specific settings (baud rate, etc.)
    s = serial.Serial('/dev/ttyUSB0', baudrate=921600, bytesize=8, parity=serial.PARITY_NONE, stopbits=1, write_timeout=0.01, xonxoff=False)
   
    # Send commands to the device over serial to configure it
    s.write('*TL10010\n'.encode('utf-8'))  # Set trigger level
    s.write('*SS1001\n'.encode('utf-8'))  # Set how many points are needed
    s.write('*PW101064\n'.encode('utf-8'))  # Set wavelength
    s.write('*SC118\n'.encode('utf-8'))  # Set energy scale
    s.write('*VNM\n'.encode('utf-8'))  # Set polling
    s.write('*ET11\n'.encode('utf-8'))  # Set trigger
    s.write('*CA1\n'.encode('utf-8'))  # Set internal acquisition
   
    # Return the serial object to be used later
    return s
 
# Set the record prefix for EPICS database
builder.SetDeviceName("Laser-Energy-Stablization")
 
# Initialize GPIO settings on Raspberry Pi
GPIO.setwarnings(False)  # Disable GPIO warnings
GPIO.setmode(GPIO.BCM)  # Set GPIO numbering mode to BCM
GPIO.setup(23, GPIO.IN)  # Set GPIO pin 23 as input
 
# Function to get the current timestamp
def get_current_timestamp():
    now = datetime.now()  # Get the current date and time
    hours = now.strftime("%H")  # Extract hours
    minutes = now.strftime("%M")  # Extract minutes
    seconds = now.strftime("%S")  # Extract seconds
    nanoseconds = now.microsecond * 1000  # Convert microseconds to nanoseconds
    return f"{hours}:{minutes}:{seconds}.{nanoseconds}"  # Return formatted timestamp
 
# Function to generate a stairstep sequence of energies
def generate_stairstep(E_ref, t):
    '''Generates a sequence of energies which will result in a stairstep'''
    tau = 3.2e-6  # Upper state lifetime of Ti:sapphire
    E = E_ref * np.exp(t / tau)  # Calculate energy based on the exponential decay formula
    E = np.tile(E, 30)  # Repeat the energy array to form a long sequence
    with open('StairStepEnergies.csv', 'w') as f:  # Open a CSV file to write the energies
        for delay, energy in zip(t, E):
            print('%.6g' % energy, file=f)  # Save each energy value in the CSV file
    return E  # Return the generated energy sequence
 
# Function to generate a reference energy (E_ref) from a data file, set the eref file name to format_data.csv
def generate_Eref(filename='format_data.csv', percentile=0.95, ind_col=1):
    data = np.genfromtxt(filename, delimiter=',')  # Load data from a CSV file
    data = data[1:, ind_col]  # Remove the header row and focus on the desired column
   
    m = np.mean(data)  # Calculate the mean of the data
    data = data[np.where(np.logical_and(data > 0.2 * m, data < 2 * m))]  # Filter out obvious outliers
   
    data = np.sort(data)  # Sort the filtered data
    print('EREF is    :..........................')
    print(data[np.floor(percentile * data.size).astype(int)])  # Print the E_ref value
    return data[np.floor(percentile * data.size).astype(int)]  # Return the E_ref value
 
# Generate E_ref and print it
eref = generate_Eref()
print(eref)
 
# Generate a dummy sequence of energies for testing
E_dummy = generate_stairstep(E_ref=10e-06, t=np.linspace(-200e-09, 200e-09, 21))
 
# Create EPICS records for reference energy, energy values, and timestamp
EREF = builder.aOut('EREF', initial_value=eref)  # Set EREF to the generated E_ref
Energy1 = builder.aOut('Energy1', initial_value=E_dummy[0])  # Set Energy1 to the first value in E_dummy
Energy2 = builder.aOut('Energy2', initial_value=9e-09)  # Set Energy2 to a default value
timestamp = builder.stringIn('timestamp', initial_value=str(get_current_timestamp()))  # Set timestamp to the current timestamp
 
# Boilerplate code to initialize the IOC (EPICS Input/Output Controller)
builder.LoadDatabase()
softioc.iocInit()
 
# Callback function to update energy values on a rising edge signal
kk = 0  # Initialize a counter
def get_file_name():
    now = datetime.now()  # Get the current date and time
    return now.strftime("12_Aug_vHill_energy_meter_data_%Y%m%d_%H%M%S.csv")  # Generate a file name based on the current date and time
 
def rising_edge(E, timestamp1):
    global Energy1
    global Energy2
    global timestamp
    global kk
    now = datetime.now()  # Get the current date and time
    Energy1.set(float(E))  # Update Energy1 with the new energy value
    Energy2.set(E_dummy[kk])  # Update Energy2 with the next value in E_dummy
    timestamp.set(str(timestamp1))  # Update the timestamp
    kk = kk + 1  # Increment the counter
 
# Define the parameters for data acquisition
input_frequency = 10  # Frequency of data acquisition (Hz)
number_of_seconds = 60  # Duration of data acquisition (seconds)
number_of_shots = input_frequency * number_of_seconds  # Total number of data points to acquire
count = 0  # Initialize a counter
diff_ts1 = 0  # Initialize a timestamp difference variable
header_start1 = "b'1:"  # Define the start of header for channel 1
header_start2 = "b'2:"  # Define the start of header for channel 2 (commented out)
header_end = "\r\n"  # Define the end of header
s = setup_slink2()  # Setup the serial link with the device
file_name = get_file_name()  # Generate a file name for data logging
 
# Open a CSV file to log the data
with open(file_name, mode='w', newline='') as file:
    writer = csv.writer(file)  # Create a CSV writer object
    writer.writerow(['Timestamp1', 'Channel1_Power', 'Rate'])  # Write the header row
   
    while count < number_of_shots:
        s.write('*CV1\n'.encode('utf-8'))  # Request one data
        val1 = s.read_until()  # Read the response
       
        timestamp1 = get_current_timestamp()  # Get the current timestamp
       
        data1 = val1[len(header_start1)-2:]  # Extract the data from the response
        data1 = data1[:-len(header_end)]
        data1 = data1.decode('utf-8')  # Decode the data to a string
       
        ts1 = time.perf_counter_ns()  # Get the current time in nanoseconds
       
        if count > 0:
            diff_ts1 = ts1 - prev_ts1  # Calculate the difference in time since the last reading
       
        prev_ts1 = ts1  # Store the current time for the next iteration
       
        writer.writerow([timestamp1, data1, diff_ts1 * 1e-09])  # Log the data in the CSV file
        print(f"{timestamp1}: {data1}: {diff_ts1 * 1e-09}")  # Print the logged data
       
        E1 = data1  # Assign the energy value to E1
        rising_edge(E1, timestamp1)  # Trigger the rising edge function
       
        count = count + 1  # Increment the counter
 
    s.close()  # Close the serial connection