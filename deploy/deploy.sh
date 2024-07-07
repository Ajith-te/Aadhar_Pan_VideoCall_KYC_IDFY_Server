#!/bin/bash

echo "Hello System-user, $USER"

ls -l CI_SERVER_TLS_CA_FILE





service="$Service-aadhar-idfy.service"

if sudo systemctl is-active --quiet "$service"; then
    sudo systemctl stop "$service"
    echo "$service stopped."
else
    echo "$service is not running."
fi


destination_path="/var/www/$DeploymentType/finvestaapiuat/aadhar-verification-idfy"

echo "Copying contents of '${Env}' to '.env' file..."
cp "${Env}" "$destination_path/.env"

echo "Waiting for 3 Seconds"
sleep 3


# Activate virtual environment
source "$destination_path/aadhar_dfy-venv/bin/activate"


# Folders Copy

folderlist=$(ls -d */)
for row in $folderlist; do
    i=0
    while IFS= read -r compare; do

        if [ "$row" == "$compare" ]; then
            ((i=i+1))
        fi
    done < "deploy/IgnoreDirectory.txt"

    if [ $i -eq 0 ]; then
        destination_dir="$destination_path/$(basename "$row")"
        if [ -e "$destination_dir" ]; then
            rm -r "$destination_dir"
        fi
        cp -r "$row" "$destination_path"
    fi
done

# Files Copy

filelist=$(ls -p | grep -v /)

for row in $filelist; do
    i=0
    while IFS= read -r compare; do
        if [ "$row" == "$compare" ]; then
            ((i=i+1))
        fi
    done < "deploy/IgnoreFiles.txt"

    if [ $i -eq 0 ]; then
        destination_file="$destination_path/$row"
        if [ -e "$destination_file" ]; then
            rm "$destination_file"  # Use 'rm' for files
        fi
        cp "$row" "$destination_path"
    fi
done

# Install Python dependencies
pip install -r "$destination_path/requirements.txt"

echo "Waiting for 3 Seconds"
sleep 3


# Starting Gunicorn app.service
if sudo systemctl is-active --quiet "$service"; then
    echo "$service is already running."
else
    sudo systemctl start "$service"
    echo "$service started."
fi

echo "Waiting for 5 Seconds"
sleep 5

# Displaying status of the service
sudo systemctl status "$service" 


echo "Waiting for 5 Seconds"
sleep 5

echo "Displaying the log | tail 10 lines from IDfy.logs "
tail -n 10 "$destination_path/FIN_IDfy.logs"


# Check if deployment was successful

if [ $? -eq 0 ]; then
    echo "Deployment completed successfully."
else
    echo "Deployment failed."
fi
