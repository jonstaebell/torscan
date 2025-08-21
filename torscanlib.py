import requests, sys, re, time, configparser, argparse, os
import xml.etree.ElementTree as ET
from datetime import datetime
from discord_webhook import DiscordWebhook

def get_args():
    # return parameters from CLI arguments
    # Define the argument parser
    param_dict = {}
    parser = argparse.ArgumentParser(description="torscan")
    parser.add_argument("--numdays", "-n", type=str, help="number of days to search", default = 0)
    parser.add_argument("--query", "-q", type=str, help="term to search", default="")
    parser.add_argument("--indexer", "-i", type=str, help="indexer to use", default="")
    parser.add_argument("--config_file", "-c", type=str, help="config file to use", default=sys.argv[0].replace(".py", ".ini"))

    # Parse the arguments
    args = parser.parse_args()
    
    try:
        param_dict["numdays"] = int(args.numdays)
    except:
        param_dict["numdays"] = 0 # default numdays to 0 if non-integer

    param_dict["query"] = args.query
    param_dict["indexer_name"] = args.indexer
    param_dict["config_file"] = args.config_file
    return param_dict

def get_config(config_file): 
    # return paramaters from configuration file
    param_dict = {}
    try:
        Config = configparser.ConfigParser()
        Config.read(config_file)
        param_dict["numdays"] = int(Config.get('optional', 'numdays')) 
        param_dict["api_key"] = Config.get('required', 'api_key')
        param_dict["webhook_url"] = Config.get('optional', 'webhook_url')
        param_dict["indexer_name"] = Config.get('optional', 'indexer_name')
        param_dict["query"] = Config.get('optional', 'query')
        param_dict["savepath"] = Config.get('optional','savepath')
    except:
        print (f"invalid config file {config_file}")
        return {} # return empty list on exceptions
    return param_dict
 
def combine_params(param_dict_args, param_dict_config):
    # combines the command line arguments with the configuration file to set program parameter dictionary
    #
    param_dict = {}
    
    # set parameter that can only come from the CLI arguments
    param_dict["config_file"] = param_dict_args["config_file"]

    # set parameters that can only come from the configuration file
    param_dict["api_key"] = param_dict_config["api_key"]
    param_dict["webhook_url"] = param_dict_config["webhook_url"]
    param_dict["savepath"] = param_dict_config["savepath"]
    
    # combine CLI arguments with config file arguments (CLI arguments take precedence) 
    # sets parameters to the value of the config file values if the argument value is still the default
    # if argument value is not the default, sets the parameter to the config file value
    param_dict["numdays"] = param_dict_config["numdays"] if param_dict_args["numdays"] == 0 else param_dict_args["numdays"]
    param_dict["indexer_name"] = param_dict_config["indexer_name"] if param_dict_args["indexer_name"] == "" else param_dict_args["indexer_name"]
    param_dict["query"] = param_dict_config["query"] if param_dict_args["query"] == "" else param_dict_args["query"]

    return param_dict

def check_errors(param_dict):
    # check if any of the program parameters are in error and if so set to defaults
    #
    # check if indexer blank, if so change to "all"
    param_dict["indexer_name"] = "all" if param_dict["indexer_name"] == "" else param_dict["indexer_name"]

    # check if numdays >= 1, if not set to 1
    param_dict["numdays"] = 1 if param_dict["numdays"] < 1 else param_dict["numdays"]

    # return dictionry, or return {} if missing required Jackett API
    return param_dict if param_dict["api_key"] != "" else {}


def get_param():
    # use get_args to get parameters from CLI arguments 
    # then get parameters from config file
    # set parameters based on 1) arguments, 2) config file
    # if missing any required, print error message and return {}
    # else return dictionary with parameters
    param_dict = {}
    param_dict_args = get_args()
    param_dict_config = get_config(param_dict_args["config_file"])
    
    if param_dict_config != {}:
        param_dict = combine_params(param_dict_args,param_dict_config)
        param_dict = check_errors(param_dict)
        return param_dict
    else:
        return {}

def missing(file,path):
    for root, dirs, files in os.walk(path):  
        if file in files:
            return False
    return True

def isrecent(given_date_str, numdays): 
    # determines if a given date is within a specified number of days of today
    # takes the given date and the number of days to compare
    # returns True if the given date is within those number of days of today
    #
    # Define the format that the given date string is in
    date_format = "%Y-%m-%d"

    # Convert the given date string to a datetime object
    given_date = datetime.strptime(given_date_str[:10], date_format)

    # Get the current date and time
    current_date_str = datetime.now().strftime(date_format)
    current_date = datetime.strptime(current_date_str, date_format)

    # Calculate the difference in days between the given date and the current date
    return (current_date - given_date).days <= numdays


def extract_hash(magnet_link, response):
    # Extracts hash from a given magnet link
    #
    # Check if the magnet link was added successfully
    if response.status_code == 200:
        # Extract the BTIH hash using regex
        hash_match = re.search(r"btih:([a-fA-F0-9]{40})", magnet_link)
        if hash_match:
            return hash_match.group(1).upper()  # Extract and convert the hash to uppercase
        else:
            print("Failed to extract hash from the magnet link.")
            return ""
    else:
        print(f"Failed to add magnet link. Status Code: {response.status_code}")
        print("Response Content:", response.text, magnet_link)
        return ""
     
def download(session,qbittorrent_url, magnet_link, savepath):
    # downloads a single magnet link from qbittorrent
    # takes the url of the qbittorrent client and a magnet link
    # returns the hash of the downloaded torrent if successful, empty string if not successful
    #
    # Start a session
    # session = requests.Session()

    # Add the magnet link with the session using the correct endpoint
    add_magnet_url = f"{qbittorrent_url}/api/v2/torrents/add"
    # add_magnet_data = {'urls': magnet_link, 'savepath': savepath} 
    add_magnet_data = {'urls': magnet_link} 
    
    response = session.post(add_magnet_url, data=add_magnet_data)

    # return hash from magnet if link was added successfully, "" if not
    return extract_hash(magnet_link, response)


def too_old(added,expiry):
    added_on = int(added)
    current_time = time.time()
    minutes_stalled = (current_time - added_on) / 60
    if expiry > 0 and minutes_stalled > expiry:
        return True
    else:
        return False
    
def remove_ifdone(qbittorrent_url, torrent, session):
    # checks if a torrent is done downloading, and if so, removes it from qbittorrent
    #
    # Check if the torrent is finished
    if torrent['state'] == 'pausedUP':  # indicates finished 
        # remove the torrent
        remove_torrent_url = f"{qbittorrent_url}/api/v2/torrents/delete"
        remove_torrent_data = {'hashes': torrent['hash'], 'deleteFiles': 'false'}  # 'false' leaves the downloaded file
        response = session.post(remove_torrent_url, data=remove_torrent_data)
        return response.status_code == 200
    else:
        expiry = 120 # TODO add to config
        if too_old(torrent['added_on'],expiry): # stalled too long, delete torrent and the file
            remove_torrent_url = f"{qbittorrent_url}/api/v2/torrents/delete"
            remove_torrent_data = {'hashes': torrent['hash'], 'deleteFiles': 'true'}  # 'true' deletes the downloaded file
            response = session.post(remove_torrent_url, data=remove_torrent_data)
            return response.status_code == 200 #TODO somehow indicate when torrents stall?
        return False # must still be downloading
                
def remove(qbittorrent_url, torrent_hash):
    # tries to remove single torrent hash from qbittorrent
    # takes the qbittorrent client url and a hash
    # returns True if hash successfully removed, False if not
    # 
    # Start a session, get list of hashes currently in qbittorrent
    session = requests.Session()
    torrents_url = f"{qbittorrent_url}/api/v2/torrents/info"
    response = session.get(torrents_url)

    if response.status_code == 200:
        torrents = response.json()
        found = False

        for torrent in torrents:
            if torrent['hash'] == torrent_hash.lower(): # found the hash in the list
                found = True
                return remove_ifdone(qbittorrent_url, torrent, session)
                
        if not found: # hash not in the list; it must have been deleted by someone else
            return True

def get_dict(result):
    # takes the result of a Jackett API call and returns needed values as a dictionary
    tor_dict = {}
    tor_dict["seeders"] = result.get('Seeders',0)
    tor_dict["pub_date"] = result.get('PublishDate',"2000-01-01")
    tor_dict["tracker"] = result.get('Tracker',"")
    tor_dict["magnet"] = result.get('MagnetUri',"")
    tor_dict["title"] = result.get('Title',"")
    return tor_dict

def get_magnets(jackett_host, params):
    # returns a list of magnet links that Jackett returns for a provided search
    # takes url of the Jackett and the program parameters
    #
    magnets = []

    url = f"{jackett_host}/api/v2.0/indexers/{params["indexer_name"]}/results"

    jackett_params = {
        'apikey': params["api_key"],  # Jackett API key
        'query': params["query"],    # Search term
        #'category': 'all',         # You can specify category like movies, tv, etc.
    }

    try:
        response = requests.get(url, params=jackett_params) 
        response.raise_for_status()  # Check if the request was successful

        # Parse the XML response
        data = response.json()  # Convert the response to JSON

        for result in data['Results']: # for each result from Jackett,
            tor_dict = get_dict(result) # convert response to a dictionary
            # check to see if it's recent, has seeders, has a magnet link, and is missing from the savepath directory
            if isrecent(tor_dict["pub_date"], params["numdays"]) and (tor_dict["seeders"] > 0) and (tor_dict["magnet"] is not None) and missing(tor_dict["title"],params["savepath"]): 
                magnets.append(tor_dict["magnet"]) # if so, add to list of magnets to be downloaded
        return magnets

    #except requests.exceptions.RequestException as e:
    except:
        print("Error occurred in getting magnets from Jackett")
        return []

def request_downloads(magnets, qbittorrent_url,savepath):
    # adds a list of magnet links to qbittorrent client
    # takes a list of magnet links and url of the qbittorrent client
    # returns a list of hashes from qbittorrent
    #
    hash_list = [] 
    if magnets != []:
        for magnet in magnets:
            new_hash = download(qbittorrent_url, magnet, savepath)
            if new_hash != "":
                hash_list.append(new_hash)
        # wait for 30 seconds per download for them to complete
        time.sleep(30*len(hash_list))
    return hash_list

def remove_list(hash_list, qbittorrent_url):
    # removes a list of downloads from qbittorrent
    # takes a list of hashes and url of the qbittorrent client
    # 
    new_hash_list = []
    while len(hash_list) > 0: # try to remove each member of hash_list
        for t in range(0,len(hash_list)):
            if not remove(qbittorrent_url, hash_list[t]):
                new_hash_list.append(hash_list[t]) # if remove fails, add to new_hash_list
        hash_list = new_hash_list
        new_hash_list = []
        if hash_list != []: # if there are entries in the list to be removed,
            time.sleep(60) # let it download some more before trying to remove again 

def call_webhook(webhook_url, output_message): 
    # checks the webhook_url parameter, and if present, uses it to send webhook to Discord
    #
    if webhook_url != "": # if url provided, notify Discord to add alert 
        webhook = DiscordWebhook(url=webhook_url, content=f"{output_message}")
        response = webhook.execute()
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print("Error in trying to use Discord Webhook", err)

def notify (params, num_downloads):
    # prints completion message and invokes discord webhook if one is provided in parameters
    # takes the parameters and the number of torrents that have been downloaded
    #
    program_name, _ = os.path.splitext(os.path.basename(sys.argv[0])) # remove path and extension from current program name
    
    # proper grammer for "downloads" or "1 download"
    output_message = f"{program_name} has downloaded "
    output_message += f"{num_downloads} torrents" if num_downloads > 1 else "1 torrent"
    
    if num_downloads > 0:
        print (output_message)
        call_webhook(params["webhook_url"], output_message)
    else:
        print ("No recent files found")