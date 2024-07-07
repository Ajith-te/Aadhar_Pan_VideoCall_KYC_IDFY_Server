#!/bin/bash

echo "Hello System-user, $USER"


destination_path="/home/bharath/finvesta-K8/Backend-application"

echo "Copying contents of '${Env}' to '.env' file..."
cp "${Env}" "$destination_path/.env"

echo "Waiting for 3 Seconds"
sleep 3


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

# Docker Image Management
IMAGE_NAME="aadhar-verification-api-digilocker-image"
docker build -t "$IMAGE_NAME" .

# Kubernetes Variables
NAMESPACE="finvesta-namespace"
DEPLOYMENT_NAME="aadhar-verification-api-digilocker-deployment"
DEPLOYMENT_FILE_NAME="deployment.yaml"

# Update the image in the deployment
echo "Updating deployment $DEPLOYMENT_NAME in namespace $NAMESPACE with new image $IMAGE_NAME"


kubectl  delete deployment.apps/$DEPLOYMENT_NAME -n $NAMESPACE

kubectl apply -f $DEPLOYMENT_FILE_NAME

if [ $? -eq 0 ]; then
    echo "Deployment $DEPLOYMENT_NAME successfully updated to$IMAGE_NAME"
else
    echo "Failed to update the deployment $DEPLOYMENT_NAME"
    exit 1
fi

