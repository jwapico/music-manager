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
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("pos_output_path", nargs="?", default=os.getcwd(), help="The output directory in which your files will be downloaded")
    parser.add_argument("--output-path", dest="output_path", help="The output directory in which your files will be downloaded")
    parser.add_argument("--search-query", dest="search_query", help="The output directory in which your files will be downloaded")
    args = parser.parse_args()
    OUTPUT_PATH = os.path.abspath(args.output_path or args.pos_output_path)
    SEARCH_QUERY = args.search_query

    os.makedirs(OUTPUT_PATH, exist_ok=True)

    if SEARCH_QUERY:
        download_track(SEARCH_QUERY, OUTPUT_PATH)
        return 0

def download_track(song: str, output_path: str) -> bool:
    slskd_success = download_track_slskd(song, output_path)

    if not slskd_success:
        download_track_ytdlp(song, output_path)

    return slskd_success

# TODO: make the output path work
def download_track_slskd(song: str, output_path: str) -> bool:
    results = search_slskd(song)

    if results:
        print(f"Downloading {results[0]['files'][0]['filename']} from user {results[0]['username']}")  
        
        download_success = slskd.transfers.enqueue(results[0]["username"], results[0]["files"])

        # TODO: check if the download was actually successful, sometimes it returns True but the file is not downloaded
        if download_success:
            print("Download successful")
            return True
        else:
            print("Download failed")

    return False

def download_track_ytdlp(query: str, output_path: str) -> str :
    if output_path is None:
        output_path = os.path.dirname(os.path.abspath(__file__))

    # TODO: fix empty queries with non english characters ctrl f '大掃除' in sldl_helper.log 
    search_query = f"ytsearch:{query}".encode("utf-8").decode()
    ytdlp_output = ""

    print(f"Downloading from yt-dlp: {query}")

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

def search_slskd(query: str) -> list:
    search = slskd.searches.search_text(query)
    search_id = search["id"]

    print(f"Searching for: '{query}'")
    while slskd.searches.state(search_id)["isComplete"] == False:
        print("Searching...")
        time.sleep(1)

    results = slskd.searches.search_responses(search_id)
    print(f"Found {len(results)} results")

    return results

if __name__ == "__main__":
    main()