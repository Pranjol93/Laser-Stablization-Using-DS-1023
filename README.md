# Laser-Stablization-Using-ML
Built a Raspberry Pi prototype to measure flashlamp-pumped laser energy stability and applied ML to reduce noise.

# Objective
The primary goal was to reduce the standard deviation of laser output energy, thereby increasing the number of usable laser shots for HED applications such as laser-plasma interactions, particle accelerators, and extreme material states. A secondary aim was to automate the trigger-based data acquisition process for experimental diagnostics and control system verification.

# Problem
High Energy Density (HED) applications are extremely sensitive to laser parameters. The current Nd:YAG pump laser, which supplies optical energy to the Ti:Sapphire amplifier, exhibits energy fluctuations that degrade stability.

# Skills:
python, Matlab, linux, Circuit Design, Oscilloscope, Signal Generator, Raspberry Pi

# Stabilization Methodology
The stabilization of gain was achieved by implementing a delay stabilization mechanism:

Slightly adjusting the triggering time of pump lasers using a delay circuit to ensure consistent gain decay before each shot.
Utilizing hardware-based delay (40 ns–2.6 µs) with 5 ns step sizes via two serially connected DS1023 ICs, controlled by a Raspberry Pi over the SPI protocol.
Laser energies were communicated using EPICS, and predictions of pump laser energy were calculated based on prior measurements.
Validation and Results
A Python program was developed to automate data collection from the LeCroy oscilloscope, and MATLAB scripts were used to analyze traces:

Successfully demonstrated the ability to control timing delays based on projected shot energies.
Currently, deployment and testing of energy stabilization using ML are ongoing.
