# SS_Tindie
ShipStation and Tindie API Integration based on the work of https://github.com/NuclearManD/TindieAPI and https://github.com/natecox/pyshipstation

## Configuring
You will need your Tindie username and API key, your ShipStation API key and API secret, and your Tindie Store_Id from ShipStation.

Should be pretty self explanatory, but create a config.py file with:
- T_username = 'Tindie username'
- T_api_key = 'Tindie api key'
- SS_api_key = 'ShipStation api key'
- SS_api_secret = 'ShipStation api secret'
- SS_Tindie_StoreID = 'ShipStation Store_Id of Tindie sales channel/store'

SS_Tindie_StoreID can also be set to '' and it will be found automatically for any ShipStation store named Tindie.

## Current Features
- Gets all unshipped orders from Tindie.
- Gets all shipped and awaiting shipment orders from ShipStation for your Tindie sales channel.
- Only submits new orders from Tindie not already in ShipStation.

## Sample Usage
On a Raspberry Pi, to run with crontab:
- sudo nano /etc/crontab
- Run every 30 minutes: */30 *  * * *   root    cd /home/pi/SS_Tindie && python3.8 ss_tindie.py >> /home/pi/SS_Tindie/log.log 2>&1
- Run every 15 minues:  */15 *  * * *   root    cd /home/pi/SS_Tindie && python3.8 ss_tindie.py >> /home/pi/SS_Tindie/log.log 2>&1
