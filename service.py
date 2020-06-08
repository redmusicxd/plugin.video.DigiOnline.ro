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
from datetime import datetime
from datetime import timedelta
import time
import resources.lib.common.vars as vars
import resources.lib.common.functions as functions
import resources.lib.schedule as schedule
import re

__SystemBuildVersion__ = xbmc.getInfoLabel('System.BuildVersion')

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
    
    schedule.clear('EPG')
    schedule.every().day.at(vars.__SimplePVRIntegration_EPG_FileRefreshTime__).do(SimplePVRIntegration_update_EPG_file, vars.__ServiceID__, vars.__AddonCookieJar__, vars.__ServiceSession__, MyServiceAddon_DataDir).tag('EPG')

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

    # Get the value (seconds since epoch) of the last modification time.
    _last_update_ = os.path.getmtime(_m3u_file_)
    
    if _last_update_ > time.time() - vars.__SimplePVRIntegration_m3u_FileMaxAge__:
      # File was updated within the last __SimplePVRIntegration_m3u_FileMaxAge__ interval, nothing to do
      logger.debug('\'' + _m3u_file_ + '\' last update: ' + time.strftime("%Y%m%d_%H%M%S", time.localtime(_last_update_)))      

    else:
      logger.debug('\'' + _m3u_file_ + '\' last update: ' + time.strftime("%Y%m%d_%H%M%S", time.localtime(_last_update_)))
      SimplePVRIntegration_update_m3u_file(NAME, COOKIEJAR, SESSION, DATA_DIR)
    
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
  
  # Login to DigiOnline for this session
  login = functions.do_login(NAME, COOKIEJAR, SESSION)

  if login['exit_code'] != 0:
    logger.debug('[Authentication error] => Error message: '+ login['error_message'])

  else:
    _CHNO_ = 1
    _data_file_ = open(_tmp_m3u_file_, 'w')
    _data_file_.write("#EXTM3U tvg-shift=0" + "\n")

    # Get video categories
    categories = functions.get_categories(NAME, COOKIEJAR, SESSION)
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


def SimplePVRIntegration_getEPG_data(NAME, COOKIEJAR, SESSION, DATE, STREAMID):
  logger.debug('Enter function')

  _url_ = "https://digiapis.rcs-rds.ro/digionline/api/v12/epg.php?action=getEPG&date=" + str(DATE) + "&id_stream=" + str(STREAMID)
  logger.debug('URL = ' + str(_url_))

  # Setup headers for the request
  MyHeaders = {
    'Host': 'digiapis.rcs-rds.ro',
    'User-Agent': vars.__userAgent__,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US',
    'Accept-Encoding': 'identity',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
  }

  logger.debug('Cookies: ' + str(list(COOKIEJAR)))
  logger.debug('Headers: ' + str(MyHeaders))
  logger.debug('URL: ' + str(_url_))
  logger.debug('Method: GET')

  # Send the GET request
  _request_ = SESSION.get(_url_, headers=MyHeaders)

  logger.debug('Received status code: ' + str(_request_.status_code))
  logger.debug('Received cookies: ' + str(list(COOKIEJAR)))
  logger.debug('Received headers: ' + str(_request_.headers))
  logger.debug('Received data: ' + str(_request_.content))

  logger.debug('Exit function')
  return str(_request_.content)
  

def SimplePVRIntegration_init_EPG_file(NAME, COOKIEJAR, SESSION, DATA_DIR):
  logger.debug('Enter function')
  
  _ENVHOME_DIR_ = xbmc.translatePath('special://envhome')
  _epg_file_ = os.path.join(_ENVHOME_DIR_, vars.__SimplePVRIntegration_EPG_FileName__)
  logger.debug('epg file: ' + _epg_file_)

  if os.path.exists(_epg_file_) and os.path.getsize(_epg_file_) != 0:
    # The _epg_file_ exists and is not empty.
    logger.debug('\'' + _epg_file_ + '\' exists and is not empty.')

    # Get the value (seconds since epoch) of the last modification time.
    _last_update_ = os.path.getmtime(_epg_file_)
    
    if _last_update_ > time.time() - vars.__SimplePVRIntegration_EPG_FileMaxAge__:
      # File was updated within the last __SimplePVRIntegration_EPG_FileMaxAge__ interval, nothing to do
      logger.debug('\'' + _epg_file_ + '\' last update: ' + time.strftime("%Y%m%d_%H%M%S", time.localtime(_last_update_)))      

    else:
      logger.debug('\'' + _epg_file_ + '\' last update: ' + time.strftime("%Y%m%d_%H%M%S", time.localtime(_last_update_)))
      SimplePVRIntegration_update_EPG_file(NAME, COOKIEJAR, SESSION, DATA_DIR)
    
  else:
    # The _epg_file_ does not exist or is empty.
    logger.debug('\'' + _epg_file_ + '\' does not exist or is empty.')
    SimplePVRIntegration_update_EPG_file(NAME, COOKIEJAR, SESSION, DATA_DIR)
    
  logger.debug('Exit function')


def SimplePVRIntegration_update_EPG_file(NAME, COOKIEJAR, SESSION, DATA_DIR):
  logger.debug('Enter function')

  _today_ = datetime.date(datetime.today())
  _tomorrow_ = datetime.date(datetime.today()) + timedelta(days=1)
  logger.debug('_today_: ' + str(_today_))
  logger.debug('_tomorrow_: ' + str(_tomorrow_))
  
  _ENVHOME_DIR_ = xbmc.translatePath('special://envhome')
  _epg_file_ = os.path.join(_ENVHOME_DIR_, vars.__SimplePVRIntegration_EPG_FileName__)
  _tmp_epg_file_ = os.path.join(_ENVHOME_DIR_, vars.__SimplePVRIntegration_EPG_FileName__ + '.tmp')
  logger.debug('epg file: ' + _epg_file_)
  logger.debug('Temp epg file: ' + _tmp_epg_file_)
  
  # Login to DigiOnline for this session
  login = functions.do_login(NAME, COOKIEJAR, SESSION)

  if login['exit_code'] != 0:
    logger.debug('[Authentication error] => Error message: '+ login['error_message'])

  else:
    _data_file_ = open(_tmp_epg_file_, 'w')
  
    _data_file_.write("<?xml version=\"1.0\" encoding=\"utf-8\" ?>" + "\n")
    _data_file_.write("<tv>" + "\n")

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
       
        _channel_metadata_ = json.loads(channel['metadata'])
        logger.debug('Channel streamId: ' + str(_channel_metadata_['new-info']['meta']['streamId']))
                
        _json_today_ = SimplePVRIntegration_getEPG_data(NAME, COOKIEJAR, SESSION, _today_, _channel_metadata_['new-info']['meta']['streamId'])
        logger.debug('_json_today_: ' + str(_json_today_))
        
        ### Workaround for poorly coded/tested API providing EPG data
        if _json_today_ == "ERR":
          logger.debug('Creating json data structure for \'' + channel['name'] + '\'' )
          _json_today_ = '{"meta":{"version":"6"},"data":{"id_stream":"' + str(_channel_metadata_['new-info']['meta']['streamId']) + '","stream_name":"","stream_desc":"' + channel['name'] + '","ios_button":"","ios_button_on":"","ios_button_size":"","ios_button_url":"","epg":[]}}'
          logger.debug('_json_today_: ' + str(_json_today_))
        
        _json_tomorrow_ = SimplePVRIntegration_getEPG_data(NAME, COOKIEJAR, SESSION, _tomorrow_, _channel_metadata_['new-info']['meta']['streamId'])
        logger.debug('_json_tomorrow_: ' + str(_json_tomorrow_))
        
        ### Workaround for poorly coded/tested API providing EPG data
        if _json_tomorrow_ == "ERR":
          logger.debug('Creating json data structure for \'' + channel['name'] + '\'' )
          _json_tomorrow_ = '{"meta":{"version":"6"},"data":{"id_stream":"' + str(_channel_metadata_['new-info']['meta']['streamId']) + '","stream_name":"","stream_desc":"' + channel['name'] + '","ios_button":"","ios_button_on":"","ios_button_size":"","ios_button_url":"","epg":[]}}'
          logger.debug('_json_tomorrow_: ' + str(_json_tomorrow_))

        _epg_today_ = json.loads(_json_today_)
        _epg_tomorrow_ = json.loads(_json_tomorrow_)
        logger.debug('_epg_today_: ' + str(_epg_today_))
        logger.debug('_epg_tomorrow_: ' + str(_epg_tomorrow_))

        _epg_ = _epg_today_.copy()
        _epg_['data']['epg'] = _epg_today_['data']['epg'] + _epg_tomorrow_['data']['epg']

        _line_ = "  <channel id=\"" + _epg_['data']['id_stream'] + "\">"
        _data_file_.write(_line_ + "\n")
        _line_ = "    <display-name>" + _epg_['data']['stream_desc'] + "</display-name>"
        _data_file_.write(_line_ + "\n")
        _line_ = "  </channel>"
        _data_file_.write(_line_ + "\n")
        
        if _epg_['data']['epg']:
          _len_ = len(_epg_['data']['epg'])
          
          for index, _program_data_ in enumerate(_epg_['data']['epg'], start=1):
            _start_date_time_object_ = datetime.utcfromtimestamp(_program_data_['start_ts'])
            if index < _len_:
              _stop_date_time_object_ = datetime.utcfromtimestamp(_epg_['data']['epg'][index]['start_ts'])
            else:
              _stop_date_time_object_ = datetime.utcfromtimestamp(_program_data_['start_ts'])

            _line_ = "  <programme start=\"" + str(_start_date_time_object_.strftime("%Y%m%d%H%M%S")) + "\" stop=\"" + str(_stop_date_time_object_.strftime("%Y%m%d%H%M%S")) + "\" channel=\"" + _epg_['data']['id_stream'] + "\">"
            _data_file_.write(_line_ + "\n")

            # Replace unwanted characters in the program name
            _program_data_['program_name'] = re.sub('<', '"', _program_data_['program_name'], flags=re.IGNORECASE)
            _program_data_['program_name'] = re.sub('>', '"', _program_data_['program_name'], flags=re.IGNORECASE)
            _line_ = "    <title>" + _program_data_['program_name'] + "</title>"
            _data_file_.write(_line_ + "\n")

             # Replace unwanted characters in the program description
            _program_data_['program_description'] = re.sub('<', '"', _program_data_['program_description'], flags=re.IGNORECASE)
            _program_data_['program_description'] = re.sub('>', '"', _program_data_['program_description'], flags=re.IGNORECASE)
            _program_data_['program_description_l'] = re.sub('<', '"', _program_data_['program_description_l'], flags=re.IGNORECASE)
            _program_data_['program_description_l'] = re.sub('>', '"', _program_data_['program_description_l'], flags=re.IGNORECASE)
            _line_ = "    <desc>" + _program_data_['program_description'] + "\n\n" + _program_data_['program_description_l'] + "</desc>"
            _data_file_.write(_line_ + "\n")

            _line_ = "  </programme>"
            _data_file_.write(_line_ + "\n")

    _data_file_.write("</tv>" + "\n")
    _data_file_.close()
    os.rename(_tmp_epg_file_, _epg_file_)
  
  logger.debug('Exit function')


if __name__ == '__main__':
  logger.debug('Enter __main__ ')
  logger.info('Running on: ' + str(__SystemBuildVersion__))
  
  SimplePVRIntegration_init_m3u_file(vars.__ServiceID__, vars.__AddonCookieJar__, vars.__ServiceSession__, MyServiceAddon_DataDir)
  SimplePVRIntegration_init_EPG_file(vars.__ServiceID__, vars.__AddonCookieJar__, vars.__ServiceSession__, MyServiceAddon_DataDir)
  
  schedule_jobs()
  schedule.every().minute.at(":05").do(schedule_jobs)

  monitor = xbmc.Monitor()  
  while not monitor.abortRequested():
    # Sleep/wait for abort for 300 seconds
    if monitor.waitForAbort(1):
      # Abort was requested while waiting. We should exit
      logger.debug('Abort was requested while waiting.')
      break
    schedule.run_pending()
  logger.debug('Exit __main__ ')

