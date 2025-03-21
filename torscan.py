# by Jon Staebell, 3/21/2025 
# uses Jackett and qbittorrent to download torrents
# see get_param function for explanation of parameters
# 
import requests, pytz, sys, re, time, configparser, argparse
import xml.etree.ElementTree as ET
from datetime import datetime
from discord_webhook import DiscordWebhook

def get_param(): 
    # function to return application parameters as a dictionary with these keys:
    #   api_key, webhook_url, numdays, indexer_name, query
    #
    # the following MUST be set in the configuration file passed as an argument:
    #   api_key
    #
    # the following can only be set in the configuration file:
    #   webhook_url
    #
    # the following can be set in configuration file or passed as command line arguments:
    #   numdays: -n
    #   query: -q
    #   indexer: -i
    #
    # the following can only be passed as command line arguments:
    #   config_file: -c
    #
    # order of precendence of the optional ways to set parameters:
    #   command line arguments override configuration file settings
    #   if numdays or query are missing gets them from user input
    #   if indexer is missing, defaults to "all"
    #      
    numdays = 0
    api_key = indexer_name = webhook_url = query = ""
    param_dict = {}

    # Defining the argument parser
    parser = argparse.ArgumentParser(description="A sample program")
    parser.add_argument("--numdays", "-n", type=str, help="number of days to search", default = 0)
    parser.add_argument("--query", "-q", type=str, help="term to search", default="")
    parser.add_argument("--indexer", "-i", type=str, help="indexer to use", default="")
    parser.add_argument("--config_file", "-c", type=str, help="config file to use", default=sys.argv[0].replace(".py", ".ini"))

    # Parsing the arguments
    args = parser.parse_args()
    query = args.query
    indexer_name = args.indexer
    config_file = args.config_file
    
    try:
        numdays = int(args.numdays)
    except:
        pass # leave as default if a non-integer was used in command line argument

    try:
        Config = configparser.ConfigParser()
        Config.read(config_file)
        if numdays < 1: # if not a command line argument, read config file
            numdays = int(Config.get('optional', 'numdays')) 
        api_key = Config.get('required', 'api_key')
        webhook_url = Config.get('optional', 'webhook_url')
        if indexer_name == "": # if not passed in command liine, check config file
            indexer_name = Config.get('optional', 'indexer_name')
        if indexer_name == "": # if still not set, default to "all"
            indexer_name = "all"
        if query == "": # if not a command line argument, read config file
            query = Config.get('optional', 'query')
    except:
        print (f"invalid config file {config_file}")
        return {} # return empty list on exceptions
        
    if numdays == 0: # if no command line argument or config file, ask user
        if len(sys.argv) > 1:
            numdays = int(sys.argv[1])
        else:
            while numdays < 1:
                try:
                    numdays = int(input("numdays? "))
                except:
                    pass

    if  query == "": # if no command line argument or config file, ask user
        if len(sys.argv) > 2:
            query = sys.argv[2]
        else:
            query = input("query? ")

    param_dict["api_key"] = api_key
    param_dict["webhook_url"] = webhook_url
    param_dict["numdays"] = numdays
    param_dict["indexer_name"] = indexer_name
    param_dict["query"] = query
        
    return param_dict

def isrecent(given_date_str, numdays):
    # determines if a given date is within a specified number of days of today
    # takes the given date and the number of days to compare
    # returns True if the given date is within those number of days of today
    #
    # Define the format that the given date string is in
    date_format = "%a, %d %b %Y %H:%M:%S %z"

    # Convert the given date string to a datetime object
    given_date = datetime.strptime(given_date_str, date_format)

    # Get the current date and time
    current_date = datetime.now(pytz.utc)

    # Calculate the difference in days between the given date and the current date
    difference_in_days = (current_date - given_date).days
    return difference_in_days <= numdays

def download(qbittorrent_url, magnet_link):
    # downloads a single magnet link from qbittorrent
    # takes the url of the qbittorrent client and a magnet link
    # returns the hash of the downloaded torrent if successful, empty string if not successful
    #
    # Start a session
    session = requests.Session()

    # Add the magnet link with the session using the correct endpoint
    add_magnet_url = f"{qbittorrent_url}/api/v2/torrents/add"
    add_magnet_data = {'urls': magnet_link}
    
    response = session.post(add_magnet_url, data=add_magnet_data)

    # Check if the magnet link was added successfully
    if response.status_code == 200:
        # Extract the BTIH hash using regex
        hash_match = re.search(r"btih:([a-fA-F0-9]{40})", magnet_link)
        if hash_match:
            torrent_hash = hash_match.group(1).upper()  # Extract and convert the hash to uppercase
        else:
            print("Failed to extract hash from the magnet link.")
            return ""
        return torrent_hash
    else:
        print(f"Failed to add magnet link. Status Code: {response.status_code}")
        print("Response Content:", response.text, magnet_link)
        return ""


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
            if torrent['hash'] == torrent_hash.lower():
                found = True
                # Check if the torrent is finished
                if torrent['state'] == 'pausedUP':  # 'stopped' indicates finished
                    print(f"Torrent {torrent['name']} finished downloading.")
                            
                    # Now remove the torrent
                    remove_torrent_url = f"{qbittorrent_url}/api/v2/torrents/delete"
                    remove_torrent_data = {'hashes': torrent['hash'], 'deleteFiles': 'false'}  # 'false' leaves the downloaded file
                    response = session.post(remove_torrent_url, data=remove_torrent_data)
                            
                    if response.status_code == 200:
                        print(f"Successfully removed torrent {torrent['name']}.")
                        return True
                    else:
                        print(f"Failed to remove torrent {torrent['name']}. Status Code: {response.status_code}")
                        return False
                else:
                    return False
                
        if not found: # must have been deleted by someone else
            return True

def get_magnets(jackett_host, params):
    # finds all the magnet links that Jackett finds for the search
    # takes the Jackett url, parameters for the Jackett search, and the number of days to return results
    # returns a list of magnet links from qbittorrent
    #
    api_key = params["api_key"]  
    numdays = params["numdays"]
    indexer_name = params["indexer_name"]
    query = params["query"]

    # Construct the full URL for the Torznab search
    url = f"{jackett_host}/api/v2.0/indexers/{indexer_name}/results/torznab/api"
    jackett_params = {
        "apikey": api_key,
        "t": "search",
        "q": query,
    }

    try:
        response = requests.get(url, params=jackett_params)
        response.raise_for_status()  # Check if the request was successful

        # Parse the XML response
        root = ET.fromstring(response.text)
        
        magnets = []
        # Iterate through the search results and extract the relevant information
        for item in root.findall("channel/item"):
            # title = item.find("title").text # unused fields commented out for potential future use
            link = item.find("link").text
            pub_date = item.find("pubDate").text
            # size = item.find("size").text
            
            # Use .find() and check if the element exists
            # seeders = item.find("torznab:seeders")
            # seeders = seeders.text if seeders is not None else "N/A"  # Fallback if missing
            
            # leechers = item.find("torznab:leechers")
            # leechers = leechers.text if leechers is not None else "N/A"  # Fallback if missing
            
            magnet = item.find("torznab:magneturi")
            magnet = magnet.text if magnet is not None else "N/A"  # Fallback if missing

            # Print the extracted information
            # print(f"Title: {title}")
            # print(f"Link: {link}")
            # print(f"Publication Date: {pub_date}")
            # print(f"Size: {size}")
            # print(f"Seeders: {seeders}")
            # print(f"Leechers: {leechers}")
            # print(f"Magnet: {magnet}")

            if isrecent(pub_date, numdays):
                magnets.append(link)

        return magnets
        
    #except requests.exceptions.RequestException as e:
    except:
        print("Error occurred in getting magnets")
        return []

def request_downloads(magnets, qbittorrent_url):
    # adds a list of magnet links to qbittorrent client
    # takes a list of magnet links and url of the qbittorrent client
    # returns a list of hashes from qbittorrent
    #
    hash_list = [] 
    if magnets != []:
        for magnet in magnets:
            hash_list.append(download(qbittorrent_url, magnet))
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

def notify (params, num_downloads):
    # prints completion message and invokes discord webhook if one is provided in parameters
    # takes the parameters and the number of torrents that have been downloaded
    #
    output_message = "1 torrent"
    if num_downloads > 1:
        output_message = f"{num_downloads} torrents"
    
    if num_downloads > 0:
        print (f"{sys.argv[0]} has downloaded {output_message}")
        webhook_url = params["webhook_url"]
        if webhook_url != "": # if url provided, notify Discord to add alert
            webhook = DiscordWebhook(url=webhook_url, content=f"{sys.argv[0]} has downloaded {output_message}")
            response = webhook.execute()
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as err:
                print(err)
    else:
        print ("No recent files found")

def main():
    jackett_host = "http://localhost:9117"
    qbittorrent_url = "http://localhost:8080"  # Default Web UI 
    print ("-" * 50, "\nStart: ", datetime.now().replace(microsecond=0))
    
    params = get_param() # program parameters
    if params != {}:
        # Get list of magnet links from Jackett
        magnets = get_magnets (jackett_host, params)
        
        # send download requests to qbittorrent
        hash_list = request_downloads(magnets, qbittorrent_url)
        num_downloads = len (hash_list)

        if num_downloads > 0:
            remove_list(hash_list, qbittorrent_url) # remove requests from qbittorrent

        notify (params, num_downloads) # print message and if provided, invoke discord webhook

    print ("End: ", datetime.now().replace(microsecond=0))

if __name__ == "__main__":
    main()