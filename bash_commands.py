def install_conda(conda_path):
    """Installs conda if it does not exist"""

    command = f"""
        CONDA_DIR="{conda_path}"

        # add other packages here alongside htop
        apt-get install -y htop

        if [ ! -d $CONDA_DIR ] 
        then
        echo "Conda does not exist. Creating..." 
        # change this for newer conda versions
        wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh;
        bash Miniconda3-latest-Linux-x86_64.sh -b
        # if you extend this to support ymls, change the following command 
        $CONDA_DIR/bin/conda create -y -n dask python=3.9
        $CONDA_DIR/bin/conda install -n dask -y -c conda-forge dask distributed scikit-learn scipy numpy pandas geopandas dask-geopandas
        else
        echo "Conda exists"
        fi
        """
    
    return command

def dask_setup_master(conda_path):
    """Sets up the master node"""
    command = f"""
        echo "Initing Scheduler"
        {conda_path}/envs/dask/bin/dask-scheduler
        """
    return command

def dask_setup_worker(master_ip, conda_path):
    """Sets up the worker node"""
    command = f"""
        echo "Initing Worker"
        {conda_path}/envs/dask/bin/dask-worker {master_ip}
        """
    return command
