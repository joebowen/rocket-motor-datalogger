#!/bin/bash
############################################################
# Help                                                     #
############################################################
Help()
{
  # Display Help
  echo "Setup environment for different devices."
  echo
  echo "Usage: $(basename "$0") [-hcdlrt] [RemoteID]"
  echo "options:"
  echo "  -c     Camera"
  echo "  -d     DataLogger"
  echo "  -l     Launcher"
  echo "  -r     Remote"
  echo "  -t     Rocket Tracker"
  echo "  -h     Print this Help."
  echo
}

############################################################
# SetupStartUp                                             #
############################################################
SetupStartUp()
{
PythonFile=$1
RemoteID=$2

cat > /home/pi/Desktop/start.sh << EOF
#!/bin/bash
$(cd /home/pi/Desktop/rocket-motor-datalogger/ && ./"${PythonFile}" -r "${RemoteID}")
EOF

chmod +x /home/pi/Desktop/start.sh

cronjob="@reboot /home/pi/Desktop/start.sh >> /home/pi/Desktop/logger.log 2>&1"
(crontab -u pi -l; echo "${cronjob}" ) | crontab -u pi -
}

############################################################
# Camera                                                   #
############################################################
Camera()
{
  RemoteID=$1

  sudo curl https://raw.githubusercontent.com/KonradIT/gopro-linux/master/gopro -o /usr/local/bin/gopro
  sudo chmod +x /usr/local/bin/gopro

  sudo apt install -y mencoder libmagick++-dev

  pip3 install --user --no-input --upgrade -r camera/requirements.txt

  SetupStartUp "ccamera_main.py" "${RemoteID}"
}

############################################################
# DataLogger                                               #
############################################################
DataLogger()
{
  RemoteID=$1

  sudo apt install qt5-default -y
  pip3 install --user --no-input --upgrade setuptools wheel pip
  pip3 install --user --no-input --upgrade -r datalogger/requirements.txt

  SetupStartUp "datalogger_main.py" "${RemoteID}"
}

############################################################
# Launcher                                                 #
############################################################
Launcher()
{
  RemoteID=$1

  pip3 install --user --no-input --upgrade setuptools wheel pip
  pip3 install --user --no-input --upgrade -r launcher/requirements.txt

  SetupStartUp "launcher_main.py" "${RemoteID}"
}

############################################################
# Remote                                                   #
############################################################
Remote()
{
  RemoteID=$1

  pip3 install --user --no-input --upgrade -r remote/requirements.txt

  SetupStartUp "remote_main.py" "${RemoteID}"
}

############################################################
# Gimbal                                                   #
############################################################
Gimbal()
{
  RemoteID=$1

  SetupStartUp "gimbal_main.py" "${RemoteID}"
}

############################################################
# Rocket Tracker                                           #
############################################################
RocketTracker()
{
  pip3 install --user --no-input --upgrade -r rocket_tracker/requirements.txt

  ./rocket_tracker/config_tracker.py
}

############################################################
############################################################
# Main program                                             #
############################################################
############################################################
############################################################
# Process the input options. Add options as needed.        #
############################################################
# Get the options
while getopts ":htc:d:l:r:g:" option; do
  case $option in
    h) # display Help
      Help
      exit;;
    t) # Rocket Tracker
      RocketTracker
      exit;;
    c) # Camera
      Camera "${OPTARG}"
      exit;;
    d) # DataLogger
      DataLogger "${OPTARG}"
      exit;;
    l) # Launcher
      Launcher "${OPTARG}"
      exit;;
    r) # Remote
      Remote "${OPTARG}"
      exit;;
    g) # Gimbal
      Gimbal "${OPTARG}"
      exit;;
    \?) # Invalid option
      echo "Error: Invalid option"
      Help
      exit;;
  esac
done

