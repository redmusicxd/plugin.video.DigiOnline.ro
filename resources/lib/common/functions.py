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

import sys
import os
import logging
# The cookielib module has been renamed to http.cookiejar in Python 3
import cookielib
# import http.cookiejar
import re
import time
import json
import vars


def init_AddonCookieJar(NAME, DATA_DIR):
  ####
  #
  # Initialize the vars.__CookieJar__ variable.
  #
  # Parameters:
  #      NAME: Logger name to use for sending the log messages
  #      DATA_DIR: The addon's 'userdata' directory.
  #
  ####

  logger = logging.getLogger(NAME)
  logger.debug('Enter function')

  # File containing the session cookies
  cookies_file = os.path.join(DATA_DIR, vars.__AddonCookiesFilename__)
  logger.debug('[ Addon cookies file ] cookies_file = ' + str(cookies_file))

  ### WARNING: The cookielib module has been renamed to http.cookiejar in Python 3
  #vars.__AddonCookieJar__ = http.cookiejar.MozillaCookieJar(cookies_file)
  vars.__AddonCookieJar__ = cookielib.MozillaCookieJar(cookies_file)

  # If it doesn't exist already, create a new file where the cookies should be saved
  if not os.path.exists(cookies_file):
    vars.__AddonCookieJar__.save()
    logger.debug('[ Addon cookiefile ] Created cookiejar file: ' + str(cookies_file))

  # Load any cookies saved from the last run
  vars.__AddonCookieJar__.load()
  logger.debug('[ Addon cookiejar ] Loaded cookiejar from file: ' + str(cookies_file))


def do_login(NAME, COOKIEJAR, SESSION):
  ####
  #
  # Login to Digionline.ro for the given session.
  #
  # Parameters:
  #      NAME: Logger name to use for sending the log messages
  #      COOKIEJAR: The cookiejar to be used with the given session
  #      SESSION: The session to be used for login
  #
  ####
  logger = logging.getLogger(NAME)
  logger.debug('Enter function')

  # Authentication to DigiOnline is done in two stages:
  # 1 - Send a GET request to https://www.digionline.ro/auth/login ('DOSESSV3PRI' session cookie will be set)
  # 2 - Send a PUT request to https://www.digionline.ro/auth/login with the credentials in the form-encoded data ('deviceId' cookie will be set)

  logger.debug('============== Stage 1: Start ==============')
  # Setup headers for the first request
  MyHeaders = {
    'Host': 'www.digionline.ro',
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
  logger.debug('URL: https://www.digionline.ro/auth/login')
  logger.debug('Method: GET')

  # Send the GET request
  _request_ = SESSION.get('https://www.digionline.ro/auth/login', headers=MyHeaders)

  logger.debug('Received status code: ' + str(_request_.status_code))
  logger.debug('Received cookies: ' + str(list(COOKIEJAR)))
  logger.debug('Received headers: ' + str(_request_.headers))
  logger.debug('Received data: ' + str(_request_.content))
  logger.debug('============== Stage 1: End ==============')

  # Save cookies for later use.
  COOKIEJAR.save(ignore_discard=True)

  logger.debug('============== Stage 2: Start ==============')

  # Setup headers for second request
  MyHeaders = {
    'Host': 'www.digionline.ro',
    'Origin': 'https://www.digionline.ro',
    'Referer': 'https://www.digionline.ro/auth/login',
    'User-Agent': vars.__userAgent__,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US',
    'Accept-Encoding': 'identity',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
  }

  # Setup form data to be sent
  MyFormData = {
    'form-login-email': vars.__config_AccountUser__,
    'form-login-password': vars.__config_AccountPassword__
  }

  logger.debug('Cookies: ' + str(list(COOKIEJAR)))
  logger.debug('Headers: ' + str(MyHeaders))
  logger.debug('MyFormData: ' + str(MyFormData))
  logger.debug('URL: https://www.digionline.ro/auth/login')
  logger.debug('Method: POST')

  # Send the POST request
  _request_ = SESSION.post('https://www.digionline.ro/auth/login', headers=MyHeaders, data=MyFormData)

  logger.debug('Received status code: ' + str(_request_.status_code))
  logger.debug('Received cookies: ' + str(list(COOKIEJAR)))
  logger.debug('Received headers: ' + str(_request_.headers))
  logger.debug('Received data: ' + str(_request_.content))
  logger.debug('============== Stage 2: End ==============')

  # Authentication error.
  if re.search('<div class="form-error(.+?)>', _request_.content, re.IGNORECASE):
    logger.debug('\'form-error\' found.')

    _ERR_SECTION_ = re.findall('<div class="form-error(.+?)>\n(.+?)<\/div>', _request_.content, re.IGNORECASE|re.DOTALL)[0][1].strip()
    _auth_error_message_ = re.sub('&period;', '.', _ERR_SECTION_, flags=re.IGNORECASE)
    _auth_error_message_ = re.sub('&abreve;', 'a', _auth_error_message_, flags=re.IGNORECASE)

    logger.info('[Authentication error] => Error message: '+ _auth_error_message_)

    logger.debug('_ERR_SECTION_ = ' + str(_ERR_SECTION_))
    logger.debug('_auth_error_message_ = ' + _auth_error_message_)
    logger.debug('[Authentication error] => Error message: '+ _auth_error_message_)

    _auth_status_ = {}
    _auth_status_['exit_code'] = 1
    _auth_status_['error_message'] = _auth_error_message_

    logger.debug('_auth_status_ = ' + str(_auth_status_))
    logger.debug('Exit function')

  else:
    logger.debug('\'form-error\' not found.')

    logger.info('Authentication successfull')

    # Save cookies for later use.
    COOKIEJAR.save(ignore_discard=True)

    _auth_status_ = {}
    _auth_status_['exit_code'] = 0
    _auth_status_['error_message'] = ''

    logger.debug('_auth_status_ = ' + str(_auth_status_))
    logger.debug('Exit function')

  return _auth_status_


def get_categories(NAME, COOKIEJAR, SESSION):
  ####
  #
  # Get from DigiOnline.ro the list of video categories
  #
  # Parameters:
  #      NAME: Logger name to use for sending the log messages
  #      COOKIEJAR: The cookiejar to be used with the given session
  #      SESSION: The session to be used for this call
  #
  # Return: The list of video categories
  #
  ####
  logger = logging.getLogger(NAME)
  logger.debug('Enter function')

  MyHeaders = {
    'Host': 'www.digionline.ro',
    'Referer': 'https://www.digionline.ro/',
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
  logger.debug('URL: https://www.digionline.ro')
  logger.debug('Method: GET')

  # Send the GET request
  _request_ = SESSION.get('https://www.digionline.ro', headers=MyHeaders)

  logger.debug('Received status code: ' + str(_request_.status_code))
  logger.debug('Received cookies: ' + str(list(COOKIEJAR)))
  logger.debug('Received headers: ' + str(_request_.headers))
  logger.debug('Received data: ' + str(_request_.content))

  # Get the raw list of categories
  _raw_categories_ = re.findall('<a href=(.+?)class="nav-menu-item-link ">', _request_.content, re.IGNORECASE)
  logger.debug('Found: _raw_categories_ = ' + str(_raw_categories_))

  # Cleanup special characters
  _raw_categories_ = str(_raw_categories_).replace('\\xc8\\x98', 'S')
  _raw_categories_ = str(_raw_categories_).replace('\\xc4\\x83', 'a')
  logger.debug('Cleaned-up _raw_categories_ = ' + str(_raw_categories_))

  # Build the list of categories names and their titles
  _raw_categories_ = re.findall('"/(.+?)" title="(.+?)"',str(_raw_categories_), re.IGNORECASE)
  logger.debug('Found: _raw_categories_ = ' + str(_raw_categories_))

  # Initialize the list of categories
  _categories_list_ = []

  for _cat_ in _raw_categories_:
    logger.info('Found category: ' + _cat_[1])
    logger.debug('Found category: ' + _cat_[1])
    _cat_record_ = {}
    _cat_record_["name"] = _cat_[0]
    _cat_record_["title"] = _cat_[1]

    logger.debug('Created: _cat_record_ = ' + str(_cat_record_))
    _categories_list_.append(_cat_record_)

  logger.debug('_categories_list_ = ' + str(_categories_list_))

  logger.debug('Exit function')

  return _categories_list_


def update_cached_categories(NAME, COOKIEJAR, SESSION, DATA_DIR):
  ####
  #
  # Updates the file with cached video categories.
  #
  # Parameters:
  #      NAME: Logger name to use for sending the log messages.
  #      COOKIEJAR: The cookiejar to be used with the given session.
  #      SESSION: The session to be used for this call
  #      DATA_DIR: The addon's 'userdata' directory.
  #
  ####
  logger = logging.getLogger(NAME)
  logger.debug('Enter function')

  categories = get_categories(NAME, COOKIEJAR, SESSION)
  logger.debug('Received categories = ' + str(categories))

  if not os.path.exists(DATA_DIR + '/' + vars.__cache_dir__ ):
    os.makedirs(DATA_DIR + '/' + vars.__cache_dir__)

  _cache_data_file_ = os.path.join(DATA_DIR, vars.__cache_dir__, vars.__categoriesCachedDataFilename__)
  logger.debug('Cached data file: ' + _cache_data_file_)

  _data_file_ = open(_cache_data_file_, 'w')
  json.dump(categories, _data_file_)
  _data_file_.close()

  logger.debug('Exit function')


def get_cached_categories(NAME, COOKIEJAR, SESSION, DATA_DIR):
  ####
  #
  # Get the list of cached video categories.
  #
  # Parameters:
  #      NAME: Logger name to use for sending the log messages.
  #      COOKIEJAR: The cookiejar to be used with the given session.
  #      SESSION: The session to be used for login this call
  #      DATA_DIR: The addon's 'userdata' directory.
  #
  # Return: The list of cached video categories
  #
  ####
  logger = logging.getLogger(NAME)
  logger.debug('Enter function')

  _return_data_ = {}
  _return_data_['status'] = {'exit_code': 0, 'error_message': ''}
  _return_data_['cached_categories'] = ''

  _cached_data_file_ = os.path.join(DATA_DIR, vars.__cache_dir__, vars.__categoriesCachedDataFilename__)
  logger.debug('Cached data file: ' + _cached_data_file_)

  if os.path.exists(_cached_data_file_) and os.path.getsize(_cached_data_file_) != 0:
    # The data file with cached categories exists and is not empty.
    
    # Get the value (seconds since epoch) of the last modification time for the file containing cached data.
    _last_update_ = os.path.getmtime(_cached_data_file_)
    logger.debug('Cached data file last update: ' + time.strftime("%Y%m%d_%H%M%S", time.gmtime(_last_update_)))
    
    if _last_update_ > time.time() - vars.__categoriesCachedDataRetentionInterval__:
      # Cached data is not yet expired.
      logger.debug('Read cached categories from data file: ' + _cached_data_file_)
      _data_file_ = open(_cached_data_file_, 'r')
      _return_data_['cached_categories'] = json.load(_data_file_)
      _data_file_.close()

    else:
      # Cached data is expired.
      # Call the function to update the cached data
      logger.debug('Cached data requires update.')

      # Login to DigiOnline for this session
      login = do_login(NAME, COOKIEJAR, SESSION)

      if login['exit_code'] != 0:
        logger.debug('[Authentication error] => Error message: '+ login['error_message'])
        _return_data_['status']['exit_code'] = login['exit_code']
        _return_data_['status']['error_message'] = login['error_message']

      else: 
        update_cached_categories(NAME, COOKIEJAR, SESSION, DATA_DIR)

        logger.debug('Read cached categories from data file: ' + _cached_data_file_)
        _data_file_ = open(_cached_data_file_, 'r')
        _return_data_['cached_categories'] = json.load(_data_file_)
        _data_file_.close()

  else:
    # The data file with cached categories does not exist or it is empty.

    # Call the function to update the cached data
    logger.debug('Cached data file does not exist.')

    # Login to DigiOnline for this session
    login = do_login(NAME, COOKIEJAR, SESSION)

    if login['exit_code'] != 0:
      logger.debug('[Authentication error] => Error message: '+ login['error_message'])
      _return_data_['status']['exit_code'] = login['exit_code']
      _return_data_['status']['error_message'] = login['error_message']      

    else:
      update_cached_categories(NAME, COOKIEJAR, SESSION, DATA_DIR)

      logger.debug('Read cached categories from data file: ' + _cached_data_file_)
      _data_file_ = open(_cached_data_file_, 'r')
      _return_data_['cached_categories'] = json.load(_data_file_)
      _data_file_.close()

  
  logger.debug('_return_data_ = ' + str(_return_data_))
  logger.debug('Exit function')

  return _return_data_


def get_channels(category, NAME, COOKIEJAR, SESSION):
  ####
  #
  # Get from DigiOnline.ro the list of channels/streams.
  #
  # Parameters:
  #      category: Category name
  #      NAME: Logger name to use for sending the log messages
  #      COOKIEJAR: The cookiejar to be used with the given session
  #      SESSION: The session to be used for this call
  #
  # Return: The list of channels/streams in the given category
  #
  ####
  logger = logging.getLogger(NAME)
  logger.debug('Enter function')

  logger.debug('Called with parameters:  category = ' + category)

  logger.info('Looking for channels in category: ' + category)
  logger.debug('Looking for channels in category: ' + category)

  # Get the list of channels in this category
  MyHeaders = {
    'Host': 'www.digionline.ro',
    'Referer': 'https://www.digionline.ro/',
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
  logger.debug('URL: https://www.digionline.ro/' + category)
  logger.debug('Method: GET')

  # Send the GET request
  _request_ = SESSION.get('https://www.digionline.ro/' + category, headers=MyHeaders)

  logger.debug('Received status code: ' + str(_request_.status_code))
  logger.debug('Received cookies: ' + str(list(COOKIEJAR)))
  logger.debug('Received headers: ' + str(_request_.headers))
  logger.debug('Received data: ' + str(_request_.content))

  _raw_channel_boxes_ = re.findall('<div class="box-container">(.+?)<figcaption>', _request_.content, re.IGNORECASE|re.DOTALL)
  logger.debug('Found _raw_channel_boxes = ' + str(_raw_channel_boxes_))

  # Initialize the list of channels
  _channels_ = []

  for _raw_channel_box_ in _raw_channel_boxes_:
    logger.debug('_raw_channel_box_ = ' + str(_raw_channel_box_))

    _channel_record_ = {}

    _channel_endpoint_ = re.findall('<a href="(.+?)" class="box-link"></a>', _raw_channel_box_, re.IGNORECASE)
    _channel_endpoint_ = _channel_endpoint_[0]
    logger.debug('Found: _channel_endpoint_ = ' + _channel_endpoint_)

    _channel_logo_ = re.findall('<img src="(.+?)" alt="logo">', _raw_channel_box_, re.IGNORECASE)
    _channel_logo_ = _channel_logo_[0]
    logger.debug('Found: _channel_logo_ = ' + _channel_logo_)

    # Get additional details of the current channel
    MyHeaders = {
      'Host': 'www.digionline.ro',
      'Referer': 'https://www.digionline.ro/' + category,
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
    logger.debug('URL: https://www.digionline.ro' + _channel_endpoint_)
    logger.debug('Method: GET')

    # Send the GET request
    _request_ = SESSION.get('https://www.digionline.ro' + _channel_endpoint_, headers=MyHeaders)

    logger.debug('Received status code: ' + str(_request_.status_code))
    logger.debug('Received cookies: ' + str(list(COOKIEJAR)))
    logger.debug('Received headers: ' + str(_request_.headers))
    logger.debug('Received data: ' + str(_request_.content))

    _raw_channel_details_box_ = re.findall('<div class="entry-video video-player(.+?)</div>', _request_.content, re.IGNORECASE|re.DOTALL)
    logger.debug('_raw_channel_details_box_ = ' + str(_raw_channel_details_box_))

    _channel_details_box_ = _raw_channel_details_box_[0]
    _channel_details_box_ = _channel_details_box_.replace('\n', '')
    _channel_details_box_ = _channel_details_box_.strip()
    logger.debug('_channel_details_box_ = ' + _channel_details_box_)

    _channel_metadata_ = re.findall('<script type="text/template">(.+?)</script>', _channel_details_box_, re.IGNORECASE)
    _channel_metadata_ = _channel_metadata_[0].strip()
    logger.debug('Found: _channel_metadata_ = ' + str(_channel_metadata_))

    _ch_meta_ = json.loads(_channel_metadata_)
    logger.info('Found channel: ' + _ch_meta_['new-info']['meta']['channelName'])
    logger.debug('Found: _channel_name_ = ' + _ch_meta_['new-info']['meta']['channelName'])
    logger.debug('Found: _channel_streamId_ = ' + str(_ch_meta_['new-info']['meta']['streamId']))

    _channel_record_["endpoint"] = _channel_endpoint_
    _channel_record_["name"] = _ch_meta_['new-info']['meta']['channelName']
    _channel_record_["logo"] = _channel_logo_
    _channel_record_["metadata"] = _channel_metadata_

    logger.debug('Created: _channel_record_ = ' + str(_channel_record_))
    _channels_.append(_channel_record_)

  logger.debug('_channels_ = ' + str(_channels_))
  logger.debug('Exit function')

  return _channels_


def update_cached_channels(category, NAME, COOKIEJAR, SESSION, DATA_DIR):
  ####
  #
  # Updates the file with cached video channels for the given category.
  #
  # Parameters:
  #      category: The given category name
  #      NAME: Logger name to use for sending the log messages.
  #      COOKIEJAR: The cookiejar to be used with the given session.
  #      SESSION: The session to be used for this call
  #      DATA_DIR: The addon's 'userdata' directory.
  #
  ####
  logger = logging.getLogger(NAME)
  logger.debug('Enter function')

  channels = get_channels(category, NAME, COOKIEJAR, SESSION)
  logger.debug('Received channels = ' + str(channels))

  if not os.path.exists(DATA_DIR + '/' + vars.__cache_dir__ ):
    os.makedirs(DATA_DIR + '/' + vars.__cache_dir__)

  _cache_data_file_ = os.path.join(DATA_DIR, vars.__cache_dir__, 'channels__' + category + '__.json')
  logger.debug('Cached data file: ' + _cache_data_file_)

  _data_file_ = open(_cache_data_file_, 'w')
  json.dump(channels, _data_file_)
  _data_file_.close()

  logger.debug('Exit function')


def get_cached_channels(category, NAME, COOKIEJAR, SESSION, DATA_DIR):
  ####
  #
  # Get the cached list of channels/streams.
  #
  # Parameters:
  #      category: Category name
  #      NAME: Logger name to use for sending the log messages.
  #      COOKIEJAR: The cookiejar to be used with the given session.
  #      SESSION: The session to be used for this call
  #      DATA_DIR: The addon's 'userdata' directory.
  #
  # Return: The list of cached channels/streams in the given category
  #
  ####
  logger = logging.getLogger(NAME)
  logger.debug('Enter function')

  _return_data_ = {}
  _return_data_['status'] = {'exit_code': 0, 'error_message': ''}
  _return_data_['cached_channels'] = ''

  _cached_data_file_ = os.path.join(DATA_DIR, vars.__cache_dir__, 'channels__' + category + '__.json')
  logger.debug('Cached data file: ' + _cached_data_file_)

  if os.path.exists(_cached_data_file_) and os.path.getsize(_cached_data_file_) != 0:
    # The data file with cached channels exists and is not empty.
    
    # Get the value (seconds since epoch) of the last modification time for the file containing cached data.
    _last_update_ = os.path.getmtime(_cached_data_file_)
    logger.debug('Cached data file last update: ' + time.strftime("%Y%m%d_%H%M%S", time.gmtime(_last_update_)))
    
    if _last_update_ > time.time() - vars.__channelsCachedDataRetentionInterval__:
      # Cached data is not yet expired.
      logger.debug('Read cached channels from data file: ' + _cached_data_file_)
      _data_file_ = open(_cached_data_file_, 'r')
      _return_data_['cached_channels'] = json.load(_data_file_)
      _data_file_.close()

    else:
      # Cached data is expired.
      # Call the function to update the cached data
      logger.debug('Cached data requires update.')

      # Login to DigiOnline for this session
      login = do_login(NAME, COOKIEJAR, SESSION)

      if login['exit_code'] != 0:
        logger.debug('[Authentication error] => Error message: '+ login['error_message'])
        _return_data_['status']['exit_code'] = login['exit_code']
        _return_data_['status']['error_message'] = login['error_message']

      else: 
        update_cached_channels(category, NAME, COOKIEJAR, SESSION, DATA_DIR)

        logger.debug('Read cached channels from data file: ' + _cached_data_file_)
        _data_file_ = open(_cached_data_file_, 'r')
        _return_data_['cached_channels'] = json.load(_data_file_)
        _data_file_.close()

  else:
    # The data file with cached categories does not exist or it is empty.

    # Call the function to update the cached data
    logger.debug('Cached data file does not exist.')

    # Login to DigiOnline for this session
    login = do_login(NAME, COOKIEJAR, SESSION)

    if login['exit_code'] != 0:
      logger.debug('[Authentication error] => Error message: '+ login['error_message'])
      _return_data_['status']['exit_code'] = login['exit_code']
      _return_data_['status']['error_message'] = login['error_message']      

    else:
      update_cached_channels(category, NAME, COOKIEJAR, SESSION, DATA_DIR)

      logger.debug('Read cached channels from data file: ' + _cached_data_file_)
      _data_file_ = open(_cached_data_file_, 'r')
      _return_data_['cached_channels'] = json.load(_data_file_)
      _data_file_.close()

  logger.debug('_return_data_ = ' + str(_return_data_))
  logger.debug('Exit function')

  return _return_data_


def get_epg_data(STREAM_ID, NAME, SESSION):
  ####
  #
  # Get from DigiOnline.ro the EPG data for the given stream ID
  #
  # Parameters:
  #      STREAM_ID: The ID of the stream
  #      NAME: Logger name to use for sending the log messages
  #      SESSION: The session to be used for this call
  #
  # Return: The EPG data for the given stream
  #
  ####
  logger = logging.getLogger(NAME)
  logger.debug('Enter function')

  # Get the EPG details for the current channel
  MyHeaders = {
    'Host': 'www.digionline.ro',
#    'Referer': 'https://www.digionline.ro/' + _channel_endpoint_,
    'User-Agent': vars.__userAgent__,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US',
    'Accept-Encoding': 'identity',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
  }

#  logger.debug('Cookies: ' + str(list(COOKIEJAR)))
  logger.debug('Headers: ' + str(MyHeaders))
  logger.debug('URL: https://www.digionline.ro/epg-xhr?channelId=' + str(STREAM_ID))
  logger.debug('Method: GET')

  # Send the GET request
  _request_ = SESSION.get('https://www.digionline.ro/epg-xhr?channelId=' + str(STREAM_ID), headers=MyHeaders)

  logger.debug('Received status code: ' + str(_request_.status_code))
#  logger.debug('Received cookies: ' + str(list(COOKIEJAR)))
  logger.debug('Received headers: ' + str(_request_.headers))
  logger.debug('Received data: ' + str(_request_.content))

  _epgdata_ = _request_.content
  logger.debug('_epgdata_ = ' + _epgdata_)

  logger.debug('Exit function')

  return _epgdata_


def update_cached_epg_data(STREAM_ID, NAME, SESSION, DATA_DIR):
  ####
  #
  # Updates the file with cached EPG data for the given stream ID.
  #
  # Parameters:
  #      STREAM_ID: ID of the stream
  #      NAME: Logger name to use for sending the log messages.
  #      SESSION: The session to be used for this call
  #      DATA_DIR: The addon's 'userdata' directory.
  #
  ####
  logger = logging.getLogger(NAME)
  logger.debug('Enter function')

  _epg_data_ = get_epg_data(STREAM_ID, NAME, SESSION)
  logger.debug('Received _epg_data_ = ' + str(_epg_data_))

  if not os.path.exists(DATA_DIR + '/' + vars.__cache_dir__ + '/EPG'):
    os.makedirs(DATA_DIR + '/' + vars.__cache_dir__ + '/EPG')

  _cached_data_file_ = os.path.join(DATA_DIR, vars.__cache_dir__, 'EPG', str(STREAM_ID) + '.json')
  logger.debug('Cached data file: ' + _cached_data_file_)

  _data_file_ = open(_cached_data_file_, 'w')
  json.dump(_epg_data_, _data_file_)
  _data_file_.close()

  logger.debug('Exit function')


def get_cached_epg_data(STREAM_ID, NAME, SESSION, DATA_DIR):
  ####
  #
  # Get the cached EPG data for the given streamID.
  #
  # Parameters:
  #      STREAM_ID: ID of the stream
  #      NAME: Logger name to use for sending the log messages.
  #      SESSION: The session to be used for this call
  #      DATA_DIR: The addon's 'userdata' directory.
  #
  # Return: The cached EPG data for the given streamID.
  #
  ####
  logger = logging.getLogger(NAME)
  logger.debug('Enter function')

  _cached_data_file_ = os.path.join(DATA_DIR, vars.__cache_dir__, 'EPG', str(STREAM_ID) + '.json')
  logger.debug('Cached data file: ' + _cached_data_file_)

  if os.path.exists(_cached_data_file_) and os.path.getsize(_cached_data_file_) != 0:
    # The data file with cached channels exists and is not empty.
    
    # Get the value (seconds since epoch) of the last modification time for the file containing cached data.
    _last_update_ = os.path.getmtime(_cached_data_file_)
    logger.debug('Cached data file last update: ' + time.strftime("%Y%m%d_%H%M%S", time.gmtime(_last_update_)))
    
    if _last_update_ > time.time() - vars.__EPGDataCachedDataRetentionInterval__:
      # Cached data is not yet expired.
      logger.debug('Read cached EPG data from data file: ' + _cached_data_file_)
      _data_file_ = open(_cached_data_file_, 'r')
      _return_data_ = json.load(_data_file_)
      _data_file_.close()

    else:
      # Cached data is expired.
      # Call the function to update the cached data
      logger.debug('Cached data requires update.')

      update_cached_epg_data(STREAM_ID, NAME, SESSION, DATA_DIR)

      logger.debug('Read cached EPG data from data file: ' + _cached_data_file_)
      _data_file_ = open(_cached_data_file_, 'r')
      _return_data_ = json.load(_data_file_)
      _data_file_.close()

  else:
    # The data file with cached categories does not exist or it is empty.

    # Call the function to update the cached data
    logger.debug('Cached data file does not exist.')

    update_cached_epg_data(STREAM_ID, NAME, SESSION, DATA_DIR)

    logger.debug('Read cached EPG data from data file: ' + _cached_data_file_)
    _data_file_ = open(_cached_data_file_, 'r')
    _return_data_ = json.load(_data_file_)
    _data_file_.close()

  logger.debug('_return_data_ = ' + str(_return_data_))
  logger.debug('Exit function')

  return _return_data_


