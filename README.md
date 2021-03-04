# legno-compiler

A compiler for the Apollo project that targets the HCDCv2 Analog Device

### Installation

First, make sure all the python requirements are installed. The legno compiler is primarily written in python, so these packages make up the brunt of the system requirements.

	pip3 install -r requirements.txt

Next install any packages listed in `apt-packages.txt` using your operating system's package manager. Here's the command for installing the packages on a debian flavored linux platform:

	sudo apt-get install graphviz

##### Setting up the Analog Chip 

If you're setting this system up on linux, you might need to add yourself to the `dialout` group to access the serial interface of the analog chip:

	sudo usermod -a -G dialout $USER

You may need to log out and log back in after doing this for the changes to take effect.


##### Retrieving the Chip-Specific Characterization Data**

To target the chip, we also need the symbolic models describing the process variations present in the device. Note the model number of your chip -- it should be written on the tag that came with the device. In this tutorial, we will be using the the data associated with chip `c0`. Next we will need to retrieve the characterization data. Download the following file from the characterization data repository:
	
	<model-number>-devstate.zip

To unpack the data, execute the following command:

	python3 scripts/unpack_char_data.py <model-number>

This will unload all of the device characterization data into the `device-state` directory. Refer to the manual for more information on how to analyze this data if you're interested in understanding the process variation data in detail. Generally speaking, the compiler only makes use of the SQL database file included in the characterization archive. In the above example, the database will be located at `device-state/hcdcv2/<model-number>/hcdcv2-<model-number>.db`. 

###### Compiling a benchmark application

Next, we will compile the `cos` benchmark application. You can find the source code for the `cos` benchmark in `progs/quickstart/cos.py`. First, execute the following command to generate one circuit which implements the cosine benchmark:

	python3 legno.py lgraph --adps 1 cos 

This should write exactly one circuit in `outputs/legno/hcdc/unrestricted/cos/lgraph-adp`. You can see a visualization of the circuit in the `lgraph-diag` directory. Next, we need to scale the circuit. Execute the following to scale all the quantities in the circuit:

	python3 legno.py lscale --calib-obj minimize_error --scale-method phys --model-number <model-number> --scale-adps 10 cos

This should write ten scaled circuits to the `outputs/legno/hcdc/unrestricted/lscale-adp` directory. You can see visualizations of the scaled circuits in the `lgraph-diag` directory. 

If the scaling procedure errors out with something along the lines of `no models available...` this means the process variation database is missing a model. To elicit a model from the hardware for all the blocks in the cosine circuit run the following command:

	python3 legno.py lcal --minimize-error --model-number <model-number> cos 

After this command completes, you can try running the above scaling command again. At this point it should execute to completion.


##### Executing the benchmark application

We are now ready to run the benchmark application. To run the `cos` benchmark on the analog hardware, execute the following command:

	python3 legno.py lexec cos

This will run each circuit in the `lscale-adp` subdirectory of the `cos` directory and collect the desired measurements from the hardware. All measurements will be outputted to `outputs/legno/hcdc/unrestricted/cos/out-waveform`. To visualize these waveforms run the following command:

	python3 legno.py lwav --summary-plots --measured cos

The above command will emit a variety of visualizations to `outputs/legno/hcdc/unrestricted/cos/plots/wave`. These visualizations include raw measurement plots, plots comparing the expected and observed behaviors and summary plots which report all trajectories and the best trajectories. You can optionally include the `--emulate` flag if you want to compare the collected waveforms to the waveforms computed by the behavioral hardware simulator.


##### Other features

The legno compiler has many other auxiliary features which are useful for testing programs, packaging collected data, and visualizing low-level hardware behaviors.

**Simulating Dynamical Systems**: The compiler also supports simulating the dynamical system program using an off-the-shelf differential equation simulator. Execute the following command to perform a numerical simulation of the `cos` benchmar:

	python3 legno.py lsim cos

The following command writes all the simulated waveforms to `outputs/legno/hcdc/unrestricted/cos/plots/sim`. These sorts of simulations are useful for testing dynamical system programs before compilation.

**Packaging Data**: The compiler provides a convenience script for packaging up all of the charactization information and program waveforms. Simply run the following command to save all data to an archive:

	python3 scripts/pack_char_data.py <model-number>

The above command will pack up all of the collected waveforms and write them to `<model-number>-bmarks.zip` and pack up all the characterization data and write it to `<model-number>-devstate.zip`. These archives can be later unpacked with the `unpack_char_data.py` command.

**Visualizing Characterization Data**: It may be helpful to visually inspect the characterization data for strange behavior. Execute the following command to produce visualizations of the error characteristics of each of the profiled blocks for a given calibration objective:

	python3 grendel.py vis maximize_fit --histogram --model-number <model-number>

This command will write visualizations to the `device-state/hcdcv2/<model-number>/viz` directory of the project. These visualizations can be visually inspected to get a better idea of the static error characteristics of the various blocks.

**Emulating the Hardware**: It may be helpful to simulate a scaled circuit using the behavioral models elicited during characterization. While many of the behavioral problems discovered by emulating the circuit cannot be fixed in compilation, they can maybe informa the development of a new compiler optimization. Run the following command to emulate a benchmark:

	python3 legno.py lemul cos

This script will emulate the benchmark using all the physical restrictions and behaviors captured in the hardware specification and characterization data. The computed waveforms are written to `outputs/legno/hcdc/unrestricted/cos/plots/sim`.


