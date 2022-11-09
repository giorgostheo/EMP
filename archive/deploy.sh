# This script moves the script.sh file to the worker machine

if [ $IP == 'LH' ] 
then
    sudo bash script.sh
else
    # if you want to use a .yml file, you should add it to the scp queue
    scp script.sh user@$IP:/home/user/
    ssh -t user@$IP "sudo bash script.sh"
fi