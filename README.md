# torscan
(c) 2025 Jon Staebell

Program to scan Jackett for torrents and download with qbittorrent

## Description

An in-depth paragraph about your project and overview of use.

## Getting Started

### Dependencies

* Requires Jackett and qbittorrent
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
   if numdays or query are missing gets them from user input

## Authors

Jon Staebell
jonstaebell@gmail.com

## Version History

* 0.1
    * Initial Release 3/21/2025

## License

This project is licensed under the Create Commons Attribution-NonCommercial 4.0 International Deed 
(https://creativecommons.org/licenses/by-nc/4.0/)

## Acknowledgments



