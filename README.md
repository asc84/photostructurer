# Phtostructurer for iOS

## Purpuse of the script
This script should help if your photos are organized into a deep directory structure and you want a somwhat similar album structure on iOS.  
This is a workaround for the iOS album problem, that there are no "subalbums". When you sync with iTunes, then your folders under your Photos folder will be your albums.

## Usage

### Installation
1. Install Python 3.7 (preferably with Pyenv)
2. Install Pipenv, preferably with your system Python.
3. Copy the config file from config_template/structphoto.ini location to any of the following:
./config/structphoto.ini or ~/.structphoto/structphoto.ini
4. Before you run the script, please ensure, that the PATHS are set up correctly!
The TARGET_DIR will be handled by the script and its content may get deleted, so you should use a new folder for this.
Also please remove the remarks from the config file.

[CONSTANTS]  
SEPARATOR: " = " This will separate the concatenated directory names.  
MESSAGE_HIGHLIGHT: " --- " This will be around the messages.  

[PATHS]  
SOURCE_DIR: c:/my_photos This is where your photos are  
TARGET_DIR: c:/my_ios_photos This is where the new structure will be created. Do not set here your photos folder!  
EXCLUDE_DIRS = ["iPod Photo Cache"] These folders shouldn't be hardlinked in the temporarly iOS friendly structure.


### Running the script
1. $ pipenv shell or $ pipenv run ...
2. usage:

```
$ python structphoto.py -h
usage: structphoto.py [-h] (-c | -u | -g) [-s SOURCE] [-t TARGET]

Organize photos for iOS

optional arguments:
  -h, --help            show this help message and exit
  -c, --clean           Clean the target folder only.
  -u, --update          Clean the target folder only and update the hardlinks.
  -g, --gui             Run the application with GUI
  -s SOURCE, --source SOURCE
                        Source directory
  -t TARGET, --target TARGET
                        Target directory
```