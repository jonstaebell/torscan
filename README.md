# torscan
(c) 2025 Jon Staebell

Program to scan Jackett for torrents and download with qbittorrent

## Description

Conducts a search for torrents using Jackett and downloads any
that are found with qbittorrent.

Example use case: schedule a cron job every morning to download
all torrents that match your search string that have been uploaded
in the previous day (numdays = 1)

### Dependencies

* Requires Jackett and qbittorrent
* qbittorrent must have web gui active with bypass authentification enabled 
* Jackett API Key must be in configuration file

### Executing program

* install in same directory as torscan.ini or use -c command line argument to specify config file path
* python3 torscan.py 
* optional command line arguments listed below

## Help

Required configuration file: torscan.ini
(if renaming the program, must also rename the configuration file. e.g., if renamed
"foobar.py" it will look for "foobar.ini")

The following MUST be set in the configuration file passed as an argument:
   api_key - Jackett key

The following can only be set in the configuration file:
   webhook_url (optional url for discord webhook to notify when downloads happen)

The following can be set in configuration file or passed as command line arguments:
   numdays: -n (number of days back to search; e.g. 1 means yesterday and today only)
   query: -q (string to search for)
   indexer: -i (indexer to use; defaults to "all" if left blank)

The following can only be passed as command line arguments:
   config_file: -c (config file to use instead of torscan.ini)

Order of precendence of the optional ways to set parameters:
   command line arguments override configuration file settings

## Authors

Jon Staebell
jonstaebell@gmail.com

## Version History

* 0.2 bug fixes, code cleanup 3/27/2025
* 0.1
    * Initial Release 3/21/2025

## License

torscan Copyright (C) 2025 Jon Staebell

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

## Acknowledgments



