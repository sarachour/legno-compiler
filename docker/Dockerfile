FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -y python3-pip libatlas-base-dev git graphviz
RUN echo yes yes | git clone https://github.com/sendyne/legno-compiler.git /root/legno-compiler
WORKDIR /root/legno-compiler
RUN git checkout asplos20-artifact
RUN pip3 install -r packages-legno.list
RUN pip3 install -r packages-grendel.list
ADD state.db device-state/state.db
ADD oscilloscope_data.zip oscilloscope_data.zip
ADD oscilloscope_data_standard.zip oscilloscope_data_standard.zip
# add relevant scripts and tables
ADD setup_exp_data.py .
ADD latex_gen.py .
ADD generate_tables.sh .
ADD generate_quality_plots.sh .
ADD generate_standard_quality_plots.sh .
ADD run_all.py .
# setup compiler
RUN cp util/config_local.py util/config.py
RUN make models-maxfit
RUN make models-minerr
RUN apt-get install -y vim zip
