mkdir -p outputs
mkdir -p PAPER
docker run -it --entrypoint /bin/bash \
       	-v $(pwd)/outputs:/root/legno-compiler/outputs \
       	-v $(pwd)/PAPER:/root/legno-compiler/PAPER \
	legno-container
