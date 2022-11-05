import sys
import os
import time
import threading
import argparse
import json
from concurrent.futures import ThreadPoolExecutor

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from lib.scrape.VideoScraper import VideoScraper
from lib.download.Downloader import Downloader
from lib.utils.PrintUtils import PrintUtils


def exec_downloader(args, sources):
    downloader = Downloader(
        tmp_directory = args.tmp_dir,
        chunk_length = int(args.chunk_length),
        chunk_threads = int(args.chunk_threads) # TODO EXCEPTION
    )

    thread = threading.Thread(target=downloader.download, args=(sources, args.output))
    thread.start()
    try:
        while thread.is_alive():
            status = downloader.pretty_status()
            print(status)
            time.sleep(0.5)
            PrintUtils.clear_line(status.count("\n")+1)
    except KeyboardInterrupt:
        downloader.interrupt = True
        print("Download stopped")

def args_manifest_download(args):
    if not args.output:
        print("Please specify the output file path")
        exit(1)

    if args.manifest_download[0] == "[": # it's a json array
        sources = json.loads(args.manifest_download)
    else:
        sources = [args.manifest_download]

    exec_downloader(args, sources)
    
def args_sharepoint_download(args):
    if not args.output or not args.username:
        print("Please specify the output file path")
        exit(1)

    sources = [] # that will be the list of manifest urls
    if args.username and args.password:
        if len(args.username) != len(args.password):
            print("Please specify the same number of usernames and passwords")
            exit(1)
        if args.cookie_file:
            scrapers = [VideoScraper(args.sharepoint_download, username, password, cookies_file=cookie_file) for username, password, cookie_file in zip(args.username, args.password, args.cookie_file)]
        else:
            scrapers = [VideoScraper(args.sharepoint_download, username, password) for username, password in zip(args.username, args.password)]
    elif args.cookie_file:
        scrapers = [VideoScraper(args.sharepoint_download, cookies_file=cookies_file) for cookies_file in args.cookie_file]

    with ThreadPoolExecutor(max_workers=int(args.scrape_threads)) as executor:
        for scraper in scrapers:
            executor.submit(scraper.load, True)

    for scraper in scrapers:
        sources.append(scraper.video_content["manifest"])

        scraper.driver_quit()

    exec_downloader(args, sources)

def main(args):
    if args.manifest_download:
        args_manifest_download(args)
    elif args.sharepoint_download:
        args_sharepoint_download(args)
    else:
        print("Please give me something to do... (use -h param for help)")
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='ler-down.py')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-md', '--manifest-download', help='Download using one ore more manifest URL (sources)')
    parser.add_argument("-out", "--output", help="Output file/directory path")
    parser.add_argument("-tmp", "--tmp-dir", help="Temporary directory for downloading chunks", default="tmp")
    parser.add_argument("-cl", "--chunk-length", help="Chunk length in seconds", default=600)
    parser.add_argument("-ct", "--chunk-threads", help="Number of threads for downloading chunks", default=1)

    group.add_argument("-d", "--sharepoint-download", help="Download using video URL (requires webscraping)")
    parser.add_argument("-u", "--username", help="Username(s) for sharepoint", nargs="*")
    parser.add_argument("-p", "--password", help="Password(s) for sharepoint", nargs="*")
    parser.add_argument("-ckf", "--cookie-file", help="Cookie file(s) for sharepoint. Cookies must be valid if username/password aren't given", nargs="*")
    parser.add_argument("-sth", "--scrape-threads", help="Number of threads for webscraping (n* of webdrivers)", default=1)

    main(parser.parse_args())
else:
    print("This script is not meant to be imported")


