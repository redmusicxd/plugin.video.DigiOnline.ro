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

# Variables for the user preferences stored in the addon configuration
__config_AccountUser__ = ''
__config_AccountPassword__ = ''
__config_DebugEnabled__ = ''
__config_ShowTitleInChannelList__ = ''



# UserAgent exposed by this addon
__userAgent__ = 'Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0'

# The IDs used by addon
__AddonID__ = 'plugin.video.DigiOnline.ro'

# File names for the files where the addon and the service will write the log entries
__AddonLogFilename__ = __AddonID__ + '.log'

# The cookiejar used by addon
__AddonCookiesFilename__ = 'cookies.txt'
__AddonCookieJar__ = ''

# The session used by addon
__AddonSession__ = ''


# Data caching

__minute__ = (1 * 60)
__day__ = (24 * 60 * 60)
# Directory holding the cached data. 
__cache_dir__ = 'cached_data'

# File containing the local copy of the list of categories read from DigiOnline.ro
__categoriesCachedDataFilename__ = 'categories.json'

# Some sane defaults before being overwritten by the user settings
# How much time has to pass before reading again from DigiOnline.ro the list of categories.
__categoriesCachedDataRetentionInterval__ = (30 * __day__)

# How much time has to pass before reading again from DigiOnline.ro the list of channels in a specific category.
__channelsCachedDataRetentionInterval__ = (10 * __day__)

# How much time has to pass before reading again from DigiOnline.ro the EPG data for a channel.
__EPGDataCachedDataRetentionInterval__ = (10 * __minute__)


