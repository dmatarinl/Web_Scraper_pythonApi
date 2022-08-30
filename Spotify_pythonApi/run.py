from __future__ import unicode_literals

import urllib.request
import string
import time
import json
import traceback
import requests
import shutil
import json, ssl, re, os

from pathlib import Path
from bs4 import BeautifulSoup
from youtube_search import YoutubeSearch
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from pytube import YouTube
from pytube import Playlist
import moviepy.editor as mp
from moviepy.editor import *
import eyed3
from eyed3.id3.frames import ImageFrame




ssl._create_default_https_context = ssl._create_stdlib_context
global BEARER_TOKEN

global MIN_VIEW_COUNT

global MAX_LENGTH

global DEBUG

BEARER_TOKEN = ""

# Some conditions for the downloading process
# The minimum view count of each song should be 5k view, with a maximum of 10 minutes
# The app can stop the downloading process if 5 songs fail before prompting to re-run

MAX_LENGTH = 60 * 10  
MIN_VIEW_COUNT = 5000 

FAIL_THRESHOLD = 5
DEBUG = True

# Definition of the color section in the console

class bcolors:

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    CBLACK  = '\33[30m'
    CGREENBG  = '\33[42m'
    CREDBG    = '\33[41m'
    CVIOLETBG2 = '\33[105m'

class ConfigException(Exception):

    pass

# Function that will get us the token using beautifulsoup library and changing to json type
def getToken():

    req = requests.request("GET", "https://open.spotify.com/")

    req_text = BeautifulSoup(req.content, "html.parser").find("script", {"id": "config"}).get_text()

    return json.loads(req_text)['accessToken']

# Function that will get us the playlist of 100 tracks

def getSongs(id_Playlist, offset, limit, token):

    url = "https://api.spotify.com/v1/playlists/" + str(id_Playlist) + "/tracks?offset=" + str(offset) + "&limit=" + str(limit) + "&market=GB"

    load={}

    headers = {

      'authorization': 'Bearer ' + str(token),
      'Sec-Fetch-Dest': 'empty',

    }

    resp = requests.request("GET", url, headers=headers, data=load)

    return json.loads(resp.text)

# Function getting the list of names corresponding to the entire playlist (setting up a max to 100 songs)

def getNames(id_Playlist):

    success = False
    songs = []

    offset_count = 0

    
    while not success:

        token = getToken()

        data = getSongs(id_Playlist, offset_count, 100, token)

        if(not 'total' in data):

            print(data)
            exit()

        if(data['total'] > 0):
            #checking the limits and printing the data

            limit = data['limit']

            offset = data['offset']

            total = data['total']

            print('\nLoading songs from ' + str(bcolors.OKGREEN) + 'Spotfiy' + str(bcolors.ENDC) +
             ' [ Limit:' + str(limit) + ', offset:' + str(offset) +', total:' + str(total) +  ' ]')
            
            if(offset < total):
                #increase in counter
                offset_count += limit

            else:
                #here will be true when finished loading songs
                success = True

            for song in data['items']:
                ##structure of the lists

                name_of_song = song['track']['name']
                name_of_artist = song['track']['artists'][0]['name']
                image_of_album = song['track']['album']['images'][0]['url']
                songs.append({'name' : name_of_song, 'artist' : name_of_artist, 'song_image' : image_of_album})

        else:
            #In case playlist is empty we print a message of warning
            print('We detect that the Playlist is empty')

            success = True

    return songs


# Main function that makes us be able to download the song and show us enough information
# to the user so they know if their list is downloading without problems
# We will check if the characters introduced by the user are allowed and if they are what we were expecting to be
# We will show the user if a song is already downloaded (song repeated) and a counter of songs that failed
# the downloading process 


def download_playlist(id_Playlist, folder):

    global MIN_VIEW_COUNT
    
    characters_expected = string.ascii_letters + string.digits+ " ()[]"

    folder = ''.join(accessed_character for accessed_character in folder if accessed_character in characters_expected)

    songs = getNames(id_Playlist)

    Path('downloads/' + str(folder)).mkdir(parents=True, exist_ok=True)

    Path('temp/').mkdir(parents=True, exist_ok=True)

    names_of_fail_songs = ""
    total_fail_down = 0 
    
    repeated_songs = 0 

    for index, song in enumerate(songs):

        name_songs = "".join([current_character for current_character in song["name"] if current_character in characters_expected])
        
        artist = "".join([current_character for current_character in song['artist'] if current_character in characters_expected])

        image_of_album_url = song['song_image']

        search_query = name_songs + ' ' + artist

        song_mp3_tmp_loc = "./temp/" + str(search_query) + '.mp3'

        song_image_path = "./temp/" + str(search_query) + '.jpg'

        destinat_song = "downloads/" + str(folder) + "/"+ str(search_query) + '.mp3'

        if os.path.exists(destinat_song):

            print(f"{bcolors.WARNING}Song {search_query} already available at {destinat_song} skipping {bcolors.ENDC}")

            repeated_songs += 1

            continue

        print('\n' * 3)

        print(bcolors.CGREENBG + bcolors.CBLACK + f'Downloading song {index}/ {len(songs)}[ ' + str(name_songs) + ' - ' + str(artist) + ' ]' + bcolors.ENDC + '\n')
        
        location = 'downloads/' + str(id_Playlist) +'/'+   ((search_query + '.mp3').replace('"', '').replace("'", '').replace('\\', '').replace('/', ''))

        if(os.path.isfile(location)):

            print(search_query)

            print('\nThe song already exists, to the next one!\n')

        else:

            try:
                
                #Storing data from youtube to convert it and filtering with min viewcount and duration

                res_yt = YoutubeSearch(search_query, max_results=1).to_json()

                if len(json.loads(res_yt)['videos']) < 1:

                    raise ConfigException('Could not load from YouTube')

                data_yt = json.loads(res_yt)['videos'][0]

                print('View Count: ' + bcolors.UNDERLINE + data_yt['views'] + bcolors.ENDC)

                print('Duration: ' + bcolors.UNDERLINE + data_yt['duration'] + bcolors.ENDC + '\n')

                sd_data = data_yt['duration'].split(':')

                duration = int(sd_data[0]) * 60  + int(sd_data[1])

                viewcount = int(re.sub('[^0-9]','', data_yt['views']))

                songlink = "https://www.youtube.com" + data_yt['url_suffix']
                song_albumc_link = data_yt['thumbnails'][0]

                if(duration >= MAX_LENGTH):
                    
                    # We show the error and demonstrate how to solve it

                    print(bcolors.CREDBG + bcolors.CBLACK + 'Couldnt obtain this song, it has to be under 10 mins.' + bcolors.ENDC)

                    print(bcolors.CVIOLETBG2 + bcolors.CBLACK  + 'Change MAX_LENGTH in the script to prevent skipping' + bcolors.ENDC)

                    raise ConfigException('Skipped song due to MAX_LENGTH value in script')

                if(viewcount <= MIN_VIEW_COUNT):

                    print(bcolors.CREDBG + bcolors.CBLACK + 'Top song has low view count it should be more than 5k views.' + bcolors.ENDC)
                    
                    print(bcolors.CVIOLETBG2 + bcolors.CBLACK  + 'Change MIN_VIEW_COUNT in the script to prevent skipping' + bcolors.ENDC)

                    raise ConfigException('Skipped song due to MIN_VIEW_COUNT value in script')

                ytlink = YouTube(songlink)

                yt_vid_link = ytlink.streams.filter(only_audio=True).first()

                yt_tmp_out = yt_vid_link.download(output_path="./temp/")

                print(bcolors.OKCYAN + ">   Downloaded mp4 without frames to " + yt_tmp_out + bcolors.ENDC + '\n')

                urllib.request.urlretrieve(image_of_album_url, song_image_path)

                print(bcolors.OKCYAN + ">   Downloaded image album cover to " + yt_tmp_out + bcolors.ENDC + '\n')

                print(bcolors.OKCYAN)

                clip = AudioFileClip(yt_tmp_out)

                clip.write_audiofile(song_mp3_tmp_loc)

                print(bcolors.ENDC)

                audiofle = eyed3.load(song_mp3_tmp_loc)

                if (audiofle.tag == None):

                    audiofle.initTag()
                    
                audiofle.tag.images.set(ImageFrame.FRONT_COVER, open(song_image_path, 'rb').read(), 'image/jpeg')

                audiofle.tag.save()

                shutil.copy(song_mp3_tmp_loc, destinat_song)

                print(bcolors.OKGREEN + "Saved final file to " + destinat_song + bcolors.ENDC + '\n')

            except Exception as exempt:

                if(DEBUG):

                    print(bcolors.FAIL + str(exempt) + bcolors.ENDC)

                if(isinstance(exempt, KeyError)):

                    f = open('failed_log.txt', 'a')

                    f.write(search_query + '\n' + str(exempt))
                    f.write('\n' + traceback.format_exc() + '\n')

                    f.close()
                    
                    print(f"{bcolors.WARNING}Failed to convert {search_query} due to error.{bcolors.ENDC}. \nVideo may be age restricted.")
                    
                    total_fail_down += 1

                    names_of_fail_songs = names_of_fail_songs + "\t• " + name_songs + " - " + artist + f" | Fail reason: {exempt}" + "\n"
                
                elif(not isinstance(exempt, ConfigException)):

                    f = open('failed_log.txt', 'a')

                    f.write(search_query + '\n' + str(exempt))

                    f.write('\n' + traceback.format_exc() + '\n')
                    f.close()

                    print(f"{bcolors.WARNING}Failed to convert {search_query} due to error.{bcolors.ENDC}. See failed_log.txt for more information.")

                    total_fail_down += 1

                    names_of_fail_songs = names_of_fail_songs + "\t• " + name_songs + " - " + artist + f" | Fail reason: {exempt}" + "\n"

                    quit()

                else:
                    f = open('failed_log.txt', 'a')

                    f.write(search_query + '\n' + str(exempt))

                    f.write('\n' + traceback.format_exc() + '\n')
                    f.close()

                    print(f"{bcolors.WARNING}Failed to convert {search_query} due to config error.{bcolors.ENDC}. See failed_log.txt for more information.")
                    
                    total_fail_down += 1

                    names_of_fail_songs = names_of_fail_songs + "\t• " + name_songs + " - " + artist + f" | Fail reason: {exempt}" + "\n"
                
                continue
                #Printing message of successfully downloaded songs
    print(f"{bcolors.OKGREEN}Successfully downloaded {len(songs) - total_fail_down - repeated_songs}/{len(songs)} songs ({repeated_songs} skipped) to {folder}{bcolors.ENDC}\n")

    if total_fail_down >= FAIL_THRESHOLD:

        # Give option to the user if the min view count was the problem

        if "y" in input(f"\n\nThere were more than {FAIL_THRESHOLD} failed downloads:\n{names_of_fail_songs} \n\nWould you like to retry with minimum view count halfed ({MIN_VIEW_COUNT//2})? (y/n) "):
           
            MIN_VIEW_COUNT //= 2

            download_playlist(id_Playlist, folder)

            exit()

    if total_fail_down:

        f = open('failed_log.txt', 'a')

        f.write(f"\nFailed downloads for {folder}:\n{names_of_fail_songs}\n")

        f.close()

    shutil.rmtree('./temp')

    print(f"{bcolors.FAIL}Failed downloads:\n{names_of_fail_songs}{bcolors.ENDC}\n")

## Main function where we demand the user to introduce the url link or the playlist name

def main(spoti_url=None):

    Name_Playlist = False

    if spoti_url == None:

        spoti_url = input('\nPlease, enter the spotify URL link: ')

    if('playlist/' in spoti_url):

        spoti_url = spoti_url.split('playlist/')[1]

    if('?' in spoti_url):

        spoti_url = spoti_url.split('?')[0]

    if not Name_Playlist:

        from lxml import html

        site = requests.get(f"https://open.spotify.com/playlist/{spoti_url}")

        if not site: #Checking different cases of warning

            if len(spoti_url) > 8:

                print(bcolors.WARNING + f"\nCould not find a Spotify playlist with the ID '{spoti_url[0:8]}..'" + bcolors.ENDC)

            else:

                print(bcolors.WARNING + f"\nCould not find a Spotify playlist with the ID '{spoti_url}'" + bcolors.ENDC)

            print(bcolors.FAIL + "Please enter a valid Spotify playlist ID or URL" + bcolors.ENDC)

            main()
            exit()

        Name_Playlist = html.fromstring(site.content).xpath('/html/body/div/div/div/div/div[1]/div/div[2]/h1')[0].text_content().strip()
        
        if not Name_Playlist:

            print(bcolors.WARNING + '\nCould not find playlist name please provide a name\n\n'+ bcolors.ENDC)

            main(spoti_url)
            exit()

        print(bcolors.WARNING + f"\nContinuing with: {Name_Playlist=}" + bcolors.ENDC)

    print(bcolors.WARNING + '\nDownloading from: ' + spoti_url + bcolors.ENDC)

    download_playlist(spoti_url, Name_Playlist)


if __name__ == "__main__":
    main()
