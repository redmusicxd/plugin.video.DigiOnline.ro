#
#
#    Copyright (C) 2020  Alin Cretu
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#

import os
import xbmcaddon
import xbmc
from urllib import urlencode
import requests
import json
import logging
import logging.handlers
import time
import resources.lib.common.vars as vars
import resources.lib.common.functions as functions
import resources.lib.schedule as schedule

# Kodi uses the following sys.argv arguments:
# [0] - The base URL for this add-on, e.g. 'plugin://plugin.video.demo1/'.
# [1] - The process handle for this add-on, as a numeric string.
# [2] - The query string passed to this add-on, e.g. '?foo=bar&baz=quux'.

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]

# Get the plugin handle as an integer number.
#_handle = int(sys.argv[1])

MyServiceAddon = xbmcaddon.Addon(id=vars.__AddonID__)

# Initialize the Addon data directory
MyServiceAddon_DataDir = xbmc.translatePath(MyServiceAddon.getAddonInfo('profile'))
if not os.path.exists(MyServiceAddon_DataDir):
    os.makedirs(MyServiceAddon_DataDir)

# Read the user preferences stored in the addon configuration
functions.read_AddonSettings(MyServiceAddon)

# Log file name
service_logfile_name = os.path.join(MyServiceAddon_DataDir, vars.__ServiceLogFilename__)

# Configure logging
if vars.__config_DebugEnabled__ == 'true':
  logging.basicConfig(level=logging.DEBUG)
else:
  logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(vars.__ServiceID__)
logger.propagate = False

# Create a rotating file handler
# TODO: Extend the settings.xml to allow the user to choose the values for maxBytes and backupCount
# TODO: Set the values for maxBytes and backupCount to values defined in the addon settings
handler = logging.handlers.RotatingFileHandler(service_logfile_name, mode='a', maxBytes=104857600, backupCount=2, encoding=None, delay=False)
if vars.__config_DebugEnabled__ == 'true':
  handler.setLevel(logging.DEBUG)
else:
  handler.setLevel(logging.INFO)

# Create a logging format to be used
formatter = logging.Formatter('%(asctime)s %(funcName)s %(levelname)s: %(message)s', datefmt='%Y%m%d_%H%M%S')
handler.setFormatter(formatter)

# add the file handler to the logger
logger.addHandler(handler)


logger.info('[ Addon settings ] MyServiceAddon = ' + str(MyServiceAddon))
logger.info('[ Addon settings ] MyServiceAddon_DataDir = ' + str(MyServiceAddon_DataDir))
logger.info('[ Addon settings ] __config_DebugEnabled__ = ' + str(vars.__config_DebugEnabled__))

# Initialize the __AddonCookieJar__ variable
functions.init_AddonCookieJar(vars.__ServiceID__, MyServiceAddon_DataDir)

# Start a new requests session and initialize the cookiejar
vars.__ServiceSession__ = requests.Session()

# Put all session cookeis in the cookiejar
vars.__ServiceSession__.cookies = vars.__AddonCookieJar__


def get_url(**kwargs):
  ####
  #
  # Create a URL for calling the plugin recursively from the given set of keyword arguments.
  #
  ####

  logger.debug('Enter function')
  logger.debug('Called with parameters: ' + str(kwargs))

  _call_url_ = '{0}?{1}'.format(_url, urlencode(kwargs))

  logger.debug('_call_url_: ' + str(_call_url_))
  logger.debug('Exit function')

  return _call_url_


def schedule_jobs():
  logger.debug('Enter function')
  functions.read_AddonSettings(MyServiceAddon)
  
  if vars.__SimplePVRIntegration_m3u_FileRefreshTime__ != vars.__SimplePVRIntegration_m3u_FileOldRefreshTime__ or vars.__SimplePVRIntegration_EPG_FileRefreshTime__ != vars.__SimplePVRIntegration_EPG_FileOldRefreshTime__:
    logger.debug('__SimplePVRIntegration_m3u_FileRefreshTime__ = ' + vars.__SimplePVRIntegration_m3u_FileRefreshTime__)
    logger.debug('__SimplePVRIntegration_EPG_FileRefreshTime__ = ' + vars.__SimplePVRIntegration_EPG_FileRefreshTime__)

    schedule.clear('m3u')
    schedule.every().day.at(vars.__SimplePVRIntegration_m3u_FileRefreshTime__).do(SimplePVRIntegration_update_m3u_file, vars.__ServiceID__, vars.__AddonCookieJar__, vars.__ServiceSession__, MyServiceAddon_DataDir).tag('m3u')
    
#    schedule.clear('EPG')
#    schedule.every().day.at(vars.__SimplePVRIntegration_EPG_FileRefreshTime__).do(SimplePVRIntegration_update_EPG_file, vars.__ServiceID__, vars.__AddonCookieJar__, vars.__ServiceSession__, MyServiceAddon_DataDir).tag('EPG')

    # Record the new values
    vars.__SimplePVRIntegration_m3u_FileOldRefreshTime__ = vars.__SimplePVRIntegration_m3u_FileRefreshTime__
    vars.__SimplePVRIntegration_EPG_FileOldRefreshTime__ = vars.__SimplePVRIntegration_EPG_FileRefreshTime__
    
  else:
    logger.debug('Nothing to do !')
      
  logger.debug('Exit function')



def SimplePVRIntegration_init_m3u_file(NAME, COOKIEJAR, SESSION, DATA_DIR):
  logger.debug('Enter function')
  
  _ENVHOME_DIR_ = xbmc.translatePath('special://envhome')
  _m3u_file_ = os.path.join(_ENVHOME_DIR_, vars.__SimplePVRIntegration_m3u_FileName__)
  logger.debug('m3u file: ' + _m3u_file_)

  if os.path.exists(_m3u_file_) and os.path.getsize(_m3u_file_) != 0:
    # The _m3u_file_ exists and is not empty.
    logger.debug('\'' + _m3u_file_ + '\' exists and is not empty.')
  else:
    # The _m3u_file_ does not exist or is empty.
    logger.debug('\'' + _m3u_file_ + '\' does not exist or is empty.')
    SimplePVRIntegration_update_m3u_file(NAME, COOKIEJAR, SESSION, DATA_DIR)
    
  logger.debug('Exit function')



def SimplePVRIntegration_update_m3u_file(NAME, COOKIEJAR, SESSION, DATA_DIR):
  logger.debug('Enter function')
  
  _ENVHOME_DIR_ = xbmc.translatePath('special://envhome')
  _m3u_file_ = os.path.join(_ENVHOME_DIR_, vars.__SimplePVRIntegration_m3u_FileName__)
  _tmp_m3u_file_ = os.path.join(_ENVHOME_DIR_, vars.__SimplePVRIntegration_m3u_FileName__ + '.tmp')
  logger.debug('m3u file: ' + _m3u_file_)
  logger.debug('Temp m3u file: ' + _tmp_m3u_file_)
  
  _CHNO_ = 1
  _data_file_ = open(_tmp_m3u_file_, 'w')
  _data_file_.write("#EXTM3U tvg-shift=0" + "\n")
  
  # Login to DigiOnline for this session
  login = functions.do_login(NAME, COOKIEJAR, SESSION)

  if login['exit_code'] != 0:
    logger.debug('[Authentication error] => Error message: '+ login['error_message'])

  else:
    # Get video categories
    categories = functions.get_categories(NAME, COOKIEJAR, SESSION)
    #logger.debug('Received categories = ' + str(categories))
    logger.debug('Received categories = ' + str(categories))
    
    for category in categories:
      logger.debug('category name = ' + category['name'])
      
      # Get the list of channels in the category.
      channels = functions.get_channels(category['name'], NAME, COOKIEJAR, SESSION)
      logger.debug('Received channels = ' + str(channels))
      
      for channel in channels:
        logger.debug('Channel data => ' +str(channel))
        logger.debug('Channel name: ' + channel['name'])
        logger.debug('Channel logo: ' + channel['logo'])
        logger.debug('Channel endpoint: ' + channel['endpoint'])
        logger.debug('Channel metadata: ' + str(channel['metadata']))
        
        _channel_metadata_ = json.loads(channel['metadata'])
        logger.debug('Channel streamId: ' + str(_channel_metadata_['new-info']['meta']['streamId']))
        
        _line_ = "#EXTINF:0 tvg-id=\"" + str(_channel_metadata_['new-info']['meta']['streamId']) + "\" tvg-name=\"" + channel['name'] + "\" tvg-logo=\"" + channel['logo'] + "\" tvg-chno=\"" + str(_CHNO_) + "\" group-title=\"" + category['title'] + "\"," + channel['name']

        _url_ = get_url(action='play', channel_endpoint=channel['endpoint'], channel_metadata=channel['metadata'])
        _play_url_ = "plugin://" + vars.__AddonID__ + "/" + _url_

        _data_file_.write(_line_ + "\n")
        _data_file_.write(_play_url_ + "\n")
        
        _CHNO_ = _CHNO_ + 1
      
    
  _data_file_.close()
  os.rename(_tmp_m3u_file_, _m3u_file_)
  
  logger.debug('Exit function')


if __name__ == '__main__':
  logger.debug('Enter __main__ ')

  SimplePVRIntegration_init_m3u_file(vars.__ServiceID__, vars.__AddonCookieJar__, vars.__ServiceSession__, MyServiceAddon_DataDir)
  
  schedule_jobs()
  #schedule.every(10).minutes.do(schedule_jobs)
  schedule.every().minute.at(":05").do(schedule_jobs)

  #schedule.every().minute.at(":05").do(SimplePVRIntegration_init_m3u_file, NAME=vars.__ServiceID__, COOKIEJAR=vars.__AddonCookieJar__, SESSION=vars.__ServiceSession__, DATA_DIR=MyServiceAddon_DataDir)

  monitor = xbmc.Monitor()  
  while not monitor.abortRequested():
    # Sleep/wait for abort for 300 seconds
    if monitor.waitForAbort(1):
      # Abort was requested while waiting. We should exit
      logger.debug('Abort was requested while waiting.')
      break
    schedule.run_pending()
  logger.debug('Exit __main__ ')


