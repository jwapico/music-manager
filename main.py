import time
import slskd_api
import subprocess
import re
import os
import argparse
import dotenv

# docker run -d -p 5030:5030 -p 5031:5031 -p 50300:50300 -e SLSKD_REMOTE_CONFIGURATION=true -v '/home/goop/dev/soulseek/app_data':/app --name slskd slskd/slskd:latest
dotenv.load_dotenv()
slskd_api_key = os.getenv("SLSKD_API_KEY")
slskd = slskd_api.SlskdClient("http://localhost:5030", slskd_api_key)

def main():
    # collect commandline arguments
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("pos_output_path", nargs="?", default=os.getcwd(), help="The output directory in which your files will be downloaded")
    parser.add_argument("--output-path", dest="output_path", help="The output directory in which your files will be downloaded")
    parser.add_argument("--search-query", dest="search_query", help="The output directory in which your files will be downloaded")
    args = parser.parse_args()
    OUTPUT_PATH = os.path.abspath(args.output_path or args.pos_output_path)
    SEARCH_QUERY = args.search_query
    os.makedirs(OUTPUT_PATH, exist_ok=True)

    # if a search query is provided, download the track
    if SEARCH_QUERY:
        download_track(SEARCH_QUERY, OUTPUT_PATH)
        return 0

def download_track(search_query: str, output_path: str) -> str:
    """
    Downloads a track from soulseek or youtube, only downloading from youtube if the query is not found on soulseek

    Args:
        search_query (str): the song to download, can be a search query
        output_path (str): the directory to download the song to

    Returns:
        str: the path to the downloaded file
    """
    download_path = download_track_slskd(search_query, output_path)

    if download_path is None:
        download_path = download_track_ytdlp(search_query, output_path)

    return download_path

# TODO: make the output path work
def download_track_slskd(search_query: str, output_path: str) -> str:
    """
    Attempts to download a track from soulseek

    Args:
        search_query (str): the song to download, can be a search query
        output_path (str): the directory to download the song to

    Returns:
        str: the path to the downloaded song
    """
    results = search_slskd(search_query)

    if results:
        print(f"Downloading {results[0]['files'][0]['filename']} from user {results[0]['username']}")  
        
        download_success = slskd.transfers.enqueue(results[0]["username"], results[0]["files"])

        # TODO: check if the download was actually successful, sometimes it returns True but the file is not downloaded
        if download_success:
            print("Download successful")
            return "placeholder slskd download path"
        else:
            print("Download failed")

def download_track_ytdlp(search_query: str, output_path: str) -> str :
    """
    Downloads a track from youtube using yt-dlp
    
    Args:
        search_query (str): the query to search for
        output_path (str): the directory to download the song to

    Returns:
        str: the path to the downloaded song
    """
    if output_path is None:
        output_path = os.path.dirname(os.path.abspath(__file__))

    # TODO: fix empty queries with non english characters ctrl f '大掃除' in sldl_helper.log 
    search_query = f"ytsearch:{search_query}".encode("utf-8").decode()
    ytdlp_output = ""

    print(f"Downloading from yt-dlp: {search_query}")

    # download the file using yt-dlp and necessary flags
    process = subprocess.Popen([
        "yt-dlp",
        search_query,
        # TODO: this should be better
        "--cookies-from-browser", "firefox:~/snap/firefox/common/.mozilla/firefox/fpmcru3a.default",
        "-x", "--audio-format", "mp3",
        "--embed-thumbnail", "--add-metadata",
        "--paths", output_path,
        "-o", "%(title)s.%(ext)s"
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # print and append the output of yt-dlp to the log file
    for line in iter(process.stdout.readline, ''):
        print(line, end='')
        ytdlp_output += line

    process.stdout.close()
    process.wait()

    # this extracts the filepath of the new file from the yt-dlp output, TODO: theres prolly a better way to do this
    file_path_pattern = r'\[EmbedThumbnail\] ffmpeg: Adding thumbnail to "([^"]+)"'
    match = re.search(file_path_pattern, ytdlp_output)
    download_path = match.group(1) if match else ""

    return download_path

def search_slskd(search_query: str) -> list:
    """
    Searches for a track on soulseek

    Args:
        search_query (str): the query to search for

    Returns:
        list: a list of search results
    """
    search = slskd.searches.search_text(search_query)
    search_id = search["id"]

    print(f"Searching for: '{search_query}'")
    while slskd.searches.state(search_id)["isComplete"] == False:
        print("Searching...")
        time.sleep(1)

    results = slskd.searches.search_responses(search_id)
    print(f"Found {len(results)} results")

    return results

if __name__ == "__main__":
    main()