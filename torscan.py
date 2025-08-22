# by Jon Staebell, 3/21/2025 
# uses Jackett and qbittorrent to download torrents
# see get_param function for explanation of parameters
# 

from datetime import datetime

from torscanlib import get_param, get_magnets, request_downloads, remove_list, notify

def main():
    jackett_host = "http://localhost:9117"
    qbittorrent_url = "http://localhost:8080"  # Default Web UI 
    print ("-" * 50, "\nStart: ", datetime.now().replace(microsecond=0))
    
    params = get_param() # gets needed program parameters
    if params != {}:
        # Get list of magnet links from Jackett
        magnets = get_magnets (jackett_host, params)
        
        # log in to qbittorrent
        session = qb_login(params)
        # send download requests to qbittorrent
        hash_list = request_downloads(session,magnets, qbittorrent_url,params["savepath"])
        num_downloads = len (hash_list)

        if num_downloads > 0:
            remove_list(session,hash_list, qbittorrent_url) # remove requests from qbittorrent

        notify (params, num_downloads) # print message and if provided, invoke discord webhook

    print ("End: ", datetime.now().replace(microsecond=0))

if __name__ == "__main__":
    main()