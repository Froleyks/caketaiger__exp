module purge
module load Clang/17.0.0_20230515-GCCcore-12.3.0-CUDA-12.1.1
module load Boost/1.83.0-GCC-12.3.0
module load CMake/3.26.3-GCCcore-12.3.0
module load Python/3.11.3-GCCcore-12.3.0
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
