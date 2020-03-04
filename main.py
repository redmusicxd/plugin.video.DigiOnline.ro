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
from urllib import urlencode
from urlparse import parse_qsl
import xbmcgui
import xbmcplugin
import os
import re
import json
import xbmcaddon
import requests
import logging
import logging.handlers
import inputstreamhelper
import resources.lib.common.vars as vars
import resources.lib.common.functions as functions

# The cookielib module has been renamed to http.cookiejar in Python 3
import cookielib
# import http.cookiejar

# Kodi uses the following sys.argv arguments:
# [0] - The base URL for this add-on, e.g. 'plugin://plugin.video.demo1/'.
# [1] - The process handle for this add-on, as a numeric string.
# [2] - The query string passed to this add-on, e.g. '?foo=bar&baz=quux'.

# Get the plugin url in plugin:// notation.
_url = sys.argv[0]

# Get the plugin handle as an integer number.
_handle = int(sys.argv[1])

MyAddon = xbmcaddon.Addon(id=vars.__AddonID__)

# Initialize the Addon data directory
MyAddon_DataDir = xbmc.translatePath(MyAddon.getAddonInfo('profile'))
if not os.path.exists(MyAddon_DataDir):
    os.makedirs(MyAddon_DataDir)

# Read the user preferences stored in the addon configuration
vars.__config_AccountUser__ = MyAddon.getSetting('AccountUser')
vars.__config_AccountPassword__ = MyAddon.getSetting('AccountPassword')
vars.__config_DebugEnabled__ = MyAddon.getSetting('DebugEnabled')
vars.__config_ShowTitleInChannelList__ = MyAddon.getSetting('ShowTitleInChannelList')
vars.__categoriesCachedDataRetentionInterval__ = (int(vars.__day__) * int(MyAddon.getSetting('categoriesCachedDataRetentionInterval')))
vars.__channelsCachedDataRetentionInterval__ = (int(vars.__day__) * int(MyAddon.getSetting('channelsCachedDataRetentionInterval')))
vars.__EPGDataCachedDataRetentionInterval__ = (int(vars.__minute__) * int(MyAddon.getSetting('EPGDataCachedDataRetentionInterval')))


#TODO: Extend the settings.xml with options to allow the user to set:
#        - The ammount of time (multiple of days) to keep the cached categories before re-reading them from DigiOnline.ro 
#        - The ammount of time (multiple of days) to keep the cached channels in a category before re-reading them from DigiOnline.ro
#        - The ammount of time (in minutes, no less than __EPGDataCachedDataRetentionInterval__ ) to keep the cached EPG data for each 
#          channel before re-reading it from DigiOnline.ro

# Log file name
addon_logfile_name = os.path.join(MyAddon_DataDir, vars.__AddonLogFilename__)

# Configure logging
if vars.__config_DebugEnabled__ == 'true':
  logging.basicConfig(level=logging.DEBUG)
else:
  logging.basicConfig(level=logging.INFO)

#logger = logging.getLogger('plugin.video.DigiOnline.log')
logger = logging.getLogger(vars.__AddonID__)
logger.propagate = False

# Create a rotating file handler
# TODO: Extend the settings.xml to allow the user to choose the values for maxBytes and backupCount
# TODO: Set the values for maxBytes and backupCount to values defined in the addon settings
handler = logging.handlers.RotatingFileHandler(addon_logfile_name, mode='a', maxBytes=104857600, backupCount=2, encoding=None, delay=False)
if vars.__config_DebugEnabled__ == 'true':
  handler.setLevel(logging.DEBUG)
else:
  handler.setLevel(logging.INFO)

# Create a logging format to be used
formatter = logging.Formatter('%(asctime)s %(funcName)s %(levelname)s: %(message)s', datefmt='%Y%m%d_%H%M%S')
handler.setFormatter(formatter)

# add the file handler to the logger
logger.addHandler(handler)

logger.debug('[ Addon settings ] __config_DebugEnabled__ = ' + str(vars.__config_DebugEnabled__))
logger.debug('[ Addon settings ] __config_ShowTitleInChannelList__ = ' + str(vars.__config_ShowTitleInChannelList__))
logger.debug('[ Addon settings ] __categoriesCachedDataRetentionInterval__ = ' + str(vars.__categoriesCachedDataRetentionInterval__))
logger.debug('[ Addon settings ] __channelsCachedDataRetentionInterval__ = ' + str(vars.__channelsCachedDataRetentionInterval__))
logger.debug('[ Addon settings ] __EPGDataCachedDataRetentionInterval__ = ' + str(vars.__EPGDataCachedDataRetentionInterval__))


# Initialize the __AddonCookieJar__ variable
functions.init_AddonCookieJar(vars.__AddonID__, MyAddon_DataDir)

# Start a new requests session and initialize the cookiejar
vars.__AddonSession__ = requests.Session()

# Put all session cookeis in the cookiejar
vars.__AddonSession__.cookies = vars.__AddonCookieJar__


def check_defaults_DigiOnline_account():
  logger.debug('Enter function')

  vars.__config_AccountUser__ = MyAddon.getSetting('AccountUser')
  while vars.__config_AccountUser__ == '__DEFAULT_USER__':
      logger.debug('Default settings found.', 'Please configure the Authentication User to be used with this addon.')
      xbmcgui.Dialog().ok('Default settings found.', 'Please configure the Authentication User to be used with this addon.')
      MyAddon.openSettings()
      vars.__config_AccountUser__ = MyAddon.getSetting('AccountUser')

  vars.__config_AccountPassword__ = MyAddon.getSetting('AccountPassword')
  while vars.__config_AccountPassword__ == '__DEFAULT_PASSWORD__':
      logger.debug('Default settings found', 'Please configure the Authenticatin Password to be used with this addon.')
      xbmcgui.Dialog().ok('Default settings found', 'Please configure the Authenticatin Password to be used with this addon.')
      MyAddon.openSettings()
      vars.__config_AccountPassword__ = MyAddon.getSetting('AccountPassword')

  logger.debug('Exit function')


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


def list_categories():
  ####
  #
  # Create the list of video categories in the Kodi interface.
  #
  ####
  logger.debug('Enter function')

  # Set plugin category.
  xbmcplugin.setPluginCategory(_handle, 'DigiOnline.ro')

  # Set plugin content.
  xbmcplugin.setContent(_handle, 'videos')

  # Get video categories
  categories = functions.get_cached_categories(vars.__AddonID__, vars.__AddonCookieJar__, vars.__AddonSession__, MyAddon_DataDir)
  logger.debug('Received categories = ' + str(categories))

  if categories['status']['exit_code'] != 0:
    logger.debug('categories[\'status\'][\'exit_code\'] = ' + str(categories['status']['exit_code']))
    xbmcgui.Dialog().ok('[Authentication error]', categories['status']['error_message'])

    logger.debug('Exit function')
    xbmc.executebuiltin("XBMC.Container.Update(path,replace)")

  else:
    for category in categories['cached_categories']:
      logger.debug('category name = ' + category['name'] + '| category title = ' + category['title'])

      # Create a list item with a text label and a thumbnail image.
      list_item = xbmcgui.ListItem(label=category['title'])

      # Set additional info for the list item.
      # For available properties see https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
      # 'mediatype' is needed for a skin to display info for this ListItem correctly.
      list_item.setInfo('video', {'title': category['title'],
                                  'genre': category['title'],
                                  'mediatype': 'video'})

      # Create a URL for a plugin recursive call.
      # Example: plugin://plugin.video.example/?action=listing&category=filme
      url = get_url(action='listing', category=category['name'])
      logger.debug('URL for plugin recursive call: ' + url)

      # This means that this item opens a sub-list of lower level items.
      is_folder = True

      # Add our item to the Kodi virtual folder listing.
      xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    # See: https://romanvm.github.io/Kodistubs/_autosummary/xbmcplugin.html
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)

    logger.debug('Exit function')


def list_channels(category):
  ####
  #
  # Create the list of playable videos in the Kodi interface.
  #
  # Parameters:
  #      category: Category name
  #
  ####

  logger.debug('Enter function')
  logger.debug('Called with parameters:  category = ' + category)

  # Set plugin category.
  xbmcplugin.setPluginCategory(_handle, category)

  # Set plugin content.
  xbmcplugin.setContent(_handle, 'videos')

  # Get the list of videos in the category.
  channels = functions.get_cached_channels(category, vars.__AddonID__, vars.__AddonCookieJar__, vars.__AddonSession__, MyAddon_DataDir)
  logger.debug('Received channels = ' + str(channels))

  if channels['status']['exit_code'] != 0:
    logger.debug('channels[\'status\'][\'exit_code\'] = ' + str(channels['status']['exit_code']))
    xbmcgui.Dialog().ok('[Authentication error]', channels['status']['error_message'])

    logger.debug('Exit function')
    xbmc.executebuiltin("XBMC.Container.Update(path,replace)")

  else:
    for channel in channels['cached_channels']:
      logger.debug('Channel data => ' +str(channel))
      logger.debug('Channel name: ' + channel['name'])
      logger.debug('Channel logo: ' + channel['logo'])
      logger.debug('Channel endpoint: ' + channel['endpoint'])
      logger.debug('Channel metadata: ' + str(channel['metadata']))

      # Create a list item with a text label and a thumbnail image.
      list_item = xbmcgui.ListItem(label=channel['name'])

      _ch_metadata_ = json.loads(channel['metadata'])
      _ch_epg_data_ = json.loads(functions.get_cached_epg_data(_ch_metadata_['new-info']['meta']['streamId'], vars.__AddonID__, vars.__AddonSession__, MyAddon_DataDir))
      logger.debug('_ch_epg_data_ = ' + str(_ch_epg_data_))

      if _ch_epg_data_:
        logger.debug('Channel has EPG data')
        logger.debug('Channel EPG data => [title]: ' + _ch_epg_data_['title'])
        logger.debug('Channel EPG data => [synopsis]: ' + _ch_epg_data_['synopsis'])

        # Set additional info for the list item.
        # For available properties see https://codedocs.xyz/xbmc/xbmc/group__python__xbmcgui__listitem.html#ga0b71166869bda87ad744942888fb5f14
        # 'mediatype' is needed for skin to display info for this ListItem correctly.
        if vars.__config_ShowTitleInChannelList__ == 'false':
          list_item.setInfo('video', {'title': channel['name'],
                                      'genre': category,
                                      'plotoutline': _ch_epg_data_['title'],
                                      'plot': _ch_epg_data_['synopsis'],
                                      'mediatype': 'video'})

        else:
          list_item.setInfo('video', {'title': channel['name'] + '  [ ' + _ch_epg_data_['title'] + ' ]',
                                      'genre': category,
                                      'plotoutline': _ch_epg_data_['title'],
                                      'plot': _ch_epg_data_['synopsis'],
                                      'mediatype': 'video'})

      else:
        logger.debug('Channel does not have EPG data')

        list_item.setInfo('video', {'title': channel['name'],
                                    'genre': category,
                                    'mediatype': 'video'})


      # Set graphics (thumbnail, fanart, banner, poster, landscape etc.) for the list item.
      list_item.setArt({'thumb': channel['logo']})

      # Set 'IsPlayable' property to 'true'.
      # This is mandatory for playable items!
      list_item.setProperty('IsPlayable', 'true')

      # Create a URL for a plugin recursive call.
      # Example: plugin://plugin.video.example/?action=play&channel_endpoint=/filme/tnt&channel_metadata=...
      url = get_url(action='play', channel_endpoint=channel['endpoint'], channel_metadata=channel['metadata'])
      logger.debug('URL for plugin recursive call: ' + url)

      # This means that this item won't open any sub-list.
      is_folder = False

      # Add our item to the Kodi virtual folder listing.
      xbmcplugin.addDirectoryItem(_handle, url, list_item, is_folder)

    # Add a sort method for the virtual folder items (alphabetically, ignore articles)
    xbmcplugin.addSortMethod(_handle, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)

    # Finish creating a virtual folder.
    xbmcplugin.endOfDirectory(_handle)

  logger.debug('Exit function')


def play_video(endpoint, metadata):
  ####
  #
  # Play a video by the provided path.
  #
  # Parameters:
  #      path: Fully-qualified video URL
  #
  ####
  logger.debug('Enter function')

  # Login to DigiOnline for this session
  login = functions.do_login(vars.__AddonID__, vars.__AddonCookieJar__, vars.__AddonSession__)

  if login['exit_code'] != 0:
    xbmcgui.Dialog().ok('[Authentication error]', login['error_message'])
    logger.debug('Exit function')
    xbmc.executebuiltin("XBMC.Container.Update(path,replace)")

  else:
    logger.debug('Called with parameters: endpoint = ' + endpoint)
    logger.debug('Called with parameters: metadata = ' + str(metadata))

    # Set a flag so we know whether to enter in the last "if" clause
    known_video_type = 0

    _channel_metadata_ = json.loads(metadata)

    logger.info('Play channel: ' + _channel_metadata_['new-info']['meta']['channelName'])
    logger.debug('Play channel: ' + _channel_metadata_['new-info']['meta']['channelName'])

    logger.debug('_channel_metadata_[\'shortcode\'] = ' + _channel_metadata_['shortcode'])

    if _channel_metadata_['shortcode'] == 'livestream':
      logger.debug('Playing a \'livestream\' video.')

      # Set the flag so we won't enter in the last "if" clause
      known_video_type = 1

      # Get the stream data (contains the URL for the stream to be played)
      MyHeaders = {
        'Host': 'www.digionline.ro',
        'Referer': 'https://www.digionline.ro' + endpoint,
        'Origin':  'https://www.digionline.ro',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': vars.__userAgent__,
        'Accept': '*/*',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
      }

      MyPostData = {'id_stream': _channel_metadata_['new-info']['meta']['streamId'], 'quality': 'hq'}

      logger.debug('Cookies: ' + str(list(vars.__AddonCookieJar__)))
      logger.debug('Headers: ' + str(MyHeaders))
      logger.debug('MyPostData: ' + str(MyPostData))
      logger.debug('URL: https://www.digionline.ro' + _channel_metadata_['new-info']['meta']['streamUrl'])
      logger.debug('Method: POST')

      # Send the POST request
      _request_ = vars.__AddonSession__.post('https://www.digionline.ro' + _channel_metadata_['new-info']['meta']['streamUrl'], data=MyPostData, headers=MyHeaders)

      logger.debug('Received status code: ' + str(_request_.status_code))
      logger.debug('Received cookies: ' + str(list(vars.__AddonCookieJar__)))
      logger.debug('Received headers: ' + str(_request_.headers))
      logger.debug('Received data: ' + _request_.content)

      _stream_data_ = json.loads(_request_.content)
      logger.debug('_stream_data_ = ' + str(_stream_data_))

      # Get the host needed to be set in the headers
      _headers_host_ = re.findall('//(.+?)/', _stream_data_['stream_url'], re.IGNORECASE)[0]
      logger.debug('Found: _headers_host_ = ' + _headers_host_)

     # If needed, append the "https:" to the stream_url
      if 'https://' not in _stream_data_['stream_url']:
        _stream_url_ = 'https:' + _stream_data_['stream_url']
        logger.debug('Created: _stream_url_ = ' + _stream_url_)
      else:
        _stream_url_ = _stream_data_['stream_url']
        logger.debug('Found: _stream_url_ = ' + _stream_url_)

      # Set the headers to be used with imputstream.adaptive
      _headers_ = ''
      _headers_ = _headers_ + 'Host=' + _headers_host_
      _headers_ = _headers_ + '&User-Agent=' + vars.__userAgent__
      _headers_ = _headers_ + '&Referer=' + 'https://www.digionline.ro' + endpoint
      _headers_ = _headers_ + '&Origin=https://www.digionline.ro'
      _headers_ = _headers_ + '&Connection=keep-alive'
      _headers_ = _headers_ + '&Accept-Language=en-US'
      _headers_ = _headers_ + '&Accept=*/*'
      _headers_ = _headers_ + '&Accept-Encoding=identity'
      logger.debug('Created: _headers_ = ' + _headers_)

      # Create a playable item with a path to play.
      # See:  https://github.com/peak3d/inputstream.adaptive/issues/131#issuecomment-375059796
      play_item = xbmcgui.ListItem(path=_stream_url_)
      play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
      play_item.setProperty('inputstream.adaptive.stream_headers', _headers_)
      play_item.setProperty('inputstream.adaptive.manifest_type', 'hls')
      play_item.setMimeType('application/vnd.apple.mpegurl')
      play_item.setContentLookup(False)

      # Pass the item to the Kodi player.
      xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

    if _channel_metadata_['shortcode'] == 'nagra-livestream':
      logger.debug('Playing a \'nagra-livestream\' video.')

      # Set the flag so we won't enter in the last if clause
      known_video_type = 1

      for cookie in vars.__AddonCookieJar__:
        if cookie.name == "deviceId":
          _deviceId_ = cookie.value
          logger.debug(' _deviceID_ = ' + _deviceId_ )

      # Get the stream data (contains the URL for the stream to be played)
      MyHeaders = {
        'Host': 'www.digionline.ro',
        'Referer': 'https://www.digionline.ro' + endpoint,
        'Origin':  'https://www.digionline.ro',
        'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': vars.__userAgent__,
        'Accept': '*/*',
        'Accept-Language': 'en-US',
        'Accept-Encoding': 'identity',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
      }

      MyPostData = {'id_stream': _channel_metadata_['new-info']['meta']['streamId'], 'quality': 'hq', 'id_device': _deviceId_}

      logger.debug('Cookies: ' + str(list(vars.__AddonCookieJar__)))
      logger.debug('Headers: ' + str(MyHeaders))
      logger.debug('MyPostData: ' + str(MyPostData))
      logger.debug('URL: https://www.digionline.ro' + _channel_metadata_['new-info']['meta']['streamUrl'])
      logger.debug('Method: POST')

      # Send the POST request
      _request_ = vars.__AddonSession__.post('https://www.digionline.ro' + _channel_metadata_['new-info']['meta']['streamUrl'], data=MyPostData, headers=MyHeaders)

      logger.debug('Received status code: ' + str(_request_.status_code))
      logger.debug('Received cookies: ' + str(list(vars.__AddonCookieJar__)))
      logger.debug('Received headers: ' + str(_request_.headers))
      logger.debug('Received data: ' + _request_.content)

      _stream_data_ = json.loads(_request_.content)
      logger.debug('_stream_data_ = ' + str(_stream_data_))

      if _stream_data_['error']['error_code'] == 0:
        logger.debug('_stream_data_[\'error\'][\'error_code\'] = ' + str(_stream_data_['error']['error_code']))

        # Get the host needed to be set in the headers for the manifest file
        _headers_host_ = re.findall('//(.+?)/', _stream_data_['data']['content']['stream.manifest.url'], re.IGNORECASE)[0]
        logger.debug('Found: _headers_host_ = ' + _headers_host_)

       # If needed, append the "https:" to the stream_url
        if 'https://' not in _stream_data_['data']['content']['stream.manifest.url']:
          _stream_manifest_url_ = 'https:' + _stream_data_['data']['content']['stream.manifest.url']
          logger.debug('Created: _stream_manifest_url_ = ' + _stream_manifest_url_)
        else:
          _stream_manifest_url_ = _stream_data_['data']['content']['stream.manifest.url']
          logger.debug('Found: _stream_manifest_url_ = ' + _stream_manifest_url_)

        # Set the headers to be used with imputstream.adaptive
        _headers_ = ''
        _headers_ = _headers_ + 'Host=' + _headers_host_
        _headers_ = _headers_ + '&User-Agent=' + vars.__userAgent__
        _headers_ = _headers_ + '&Referer=' + 'https://www.digionline.ro' + endpoint
        _headers_ = _headers_ + '&Origin=https://www.digionline.ro'
        _headers_ = _headers_ + '&Connection=keep-alive'
        _headers_ = _headers_ + '&Accept-Language=en-US'
        _headers_ = _headers_ + '&Accept=*/*'
        _headers_ = _headers_ + '&Accept-Encoding=identity'
        logger.debug('Created: _headers_ = ' + _headers_)

        # Get the host needed to be set in the headers for the DRM license request
        _lic_headers_host_ = re.findall('//(.+?)/', _stream_data_['data']['content']['widevine.proxy'], re.IGNORECASE)[0]
        logger.debug('Found: _lic_headers_host_ = ' + _lic_headers_host_)

        # Set the headers to be used when requesting license key
        _lic_headers_ = ''
        _lic_headers_ = _lic_headers_ + 'Host=' + _lic_headers_host_
        _lic_headers_ = _lic_headers_ + '&User-Agent=' + vars.__userAgent__
        _lic_headers_ = _lic_headers_ + '&Referer=' + 'https://www.digionline.ro' + endpoint
        _lic_headers_ = _lic_headers_ + '&Origin=https://www.digionline.ro'
        _lic_headers_ = _lic_headers_ + '&Connection=keep-alive'
        _lic_headers_ = _lic_headers_ + '&Accept-Language=en-US'
        _lic_headers_ = _lic_headers_ + '&Accept=*/*'
        _lic_headers_ = _lic_headers_ + '&Accept-Encoding=identity'
        _lic_headers_ = _lic_headers_ + '&verifypeer=false'
        logger.debug('Created: _lic_headers_ = ' + _lic_headers_)

        # Create a playable item with a path to play.
        ### See:
        ###    https://github.com/peak3d/inputstream.adaptive/wiki
        ###    https://github.com/peak3d/inputstream.adaptive/wiki/Integration
        ###    https://github.com/emilsvennesson/script.module.inputstreamhelper

        is_helper = inputstreamhelper.Helper('mpd', drm='com.widevine.alpha')
        if is_helper.check_inputstream():
          play_item = xbmcgui.ListItem(path=_stream_manifest_url_)
          play_item.setProperty('inputstreamaddon', 'inputstream.adaptive')
          play_item.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
          play_item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
          play_item.setProperty('inputstream.adaptive.license_key', _stream_data_['data']['content']['widevine.proxy'] + '|' + _lic_headers_ + '|R{SSM}|')
          play_item.setMimeType('application/dash+xml')

          # Pass the item to the Kodi player.
          xbmcplugin.setResolvedUrl(_handle, True, listitem=play_item)

      else:
        # The DigiOnline.ro account configured in the addon's settings is not entitled to play this stream.
        logger.debug('_stream_data_[\'error\'][\'error_code\'] = ' + str(_stream_data_['error']['error_code']))
        logger.debug('_stream_data_[\'error\'][\'error_message\'] = ' + _stream_data_['error']['error_message'])

        logger.info('[Error code: ' + str(_stream_data_['error']['error_code']) + ']  => ' + _stream_data_['error']['error_message'])
        logger.debug('[Error code: ' + str(_stream_data_['error']['error_code']) + ']  => ' + _stream_data_['error']['error_message'])

        xbmcgui.Dialog().ok('[Error code: ' + str(_stream_data_['error']['error_code']) + ']', str(_stream_data_['error']['error_message']))

    # A 'catch-all'-type condition to cover for the unknown cases
    if known_video_type == 0:
      logger.info('Don\'t know (yet ?) how to play a \'' + _channel_metadata_['shortcode'] + '\' video type.')
      logger.debug('Don\'t know (yet ?) how to play a \'' + _channel_metadata_['shortcode'] + '\' video type.')

  logger.debug('Exit function')


def router(paramstring):
  ####
  #
  # Router function that calls other functions depending on the provided paramster
  #
  # Parameters:
  #      paramstring: URL encoded plugin paramstring
  #
  ####

  logger.debug('Enter function')

  # Parse a URL-encoded paramstring to the dictionary of {<parameter>: <value>} elements
  params = dict(parse_qsl(paramstring))

  # Check the parameters passed to the plugin
  if params:
      if params['action'] == 'listing':
        # Display the list of channels in a provided category.
        list_channels(params['category'])
      elif params['action'] == 'play':
        # Play a video from the provided URL.
        play_video(params['channel_endpoint'], params['channel_metadata'])
      else:
        # Raise an exception if the provided paramstring does not contain a supported action
        # This helps to catch coding errors,
        raise ValueError('Invalid paramstring: {0}!'.format(paramstring))
  else:
    # If the plugin is called from Kodi UI without any parameters:

    # Get the details of the configured DigiOnline.ro account.
    check_defaults_DigiOnline_account()

    # Display the list of available video categories
    list_categories()

  # TODO: Logout from DigiOnline for this session
  # TODO: do_logout()

  logger.debug('Exit function')


if __name__ == '__main__':
  logger.debug('Enter function')

  # Call the router function and pass the plugin call parameters to it.
  router(sys.argv[2][1:])

  logger.debug('Exit function')

