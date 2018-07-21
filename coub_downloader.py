# -*- coding: utf-8 -*-

import requests
import sys
import getopt
import re
import shutil
import os.path
import codecs
from fake_useragent import UserAgent
import time

class CoubDownloader(object):
    def __init__(self, path_to_download='/tmp'):
        self._path_to = path_to_download
        self._coub_id_re = re.compile(r".*\/(\w{4,})$", re.DOTALL|re.UNICODE|re.MULTILINE)
        self.prefix_url = 'http://coub.com/api/v2/coubs/'
        self.video_parts_count =4
        self.cookie = ""

    # setter for set path to resources
    def set_path(self, path_to_resources):
        self._path_to = path_to_resources

    def download(self, url):
        # randomize useragent
        ua = UserAgent()
        headers = {'User-Agent': ua.random}

        # coub url https://coub.com/view/gggggg
        # parse id for coub page
        id_coub_page = self._coub_id_re.findall(url)
        if not id_coub_page:
            print("Error parse coub id page")
            return

        id_coub_page = id_coub_page[0]
        page_str = requests.get(self.prefix_url+id_coub_page, headers=headers)

        # download page as json
        json_obj = page_str.json()

        video_url = None
        audio_url = None

        #chack quality version for video and audio
        # two quality: high or med
        video_size = 0
        if 'high' in json_obj['file_versions']['html5']['video']:
            video_url = json_obj["file_versions"]["html5"]["video"]["high"]["url"]
            video_size = json_obj["file_versions"]["html5"]["video"]["high"]["size"]
        elif 'med' in json_obj['file_versions']['html5']['video']:
            video_url = json_obj["file_versions"]["html5"]["video"]["med"]["url"]
            video_size = json_obj["file_versions"]["html5"]["video"]["med"]["size"]

        if 'high' in json_obj['file_versions']['html5']['audio']:
            audio_url = json_obj["file_versions"]["html5"]["audio"]["high"]["url"]
        elif 'med' in json_obj['file_versions']['html5']['audio']:
            audio_url = json_obj["file_versions"]["html5"]["audio"]["med"]["url"]

        # check urls and exit if is None
        if not (video_url or audio_url):
            print("Error parse resources urls for coub: {}".format(url))
            return

        # download resources
        headers["Referer"] = url
        self.range_download_video(video_url, video_size, url, id_coub_page, headers)

        audio_response = requests.get(audio_url, headers=headers, stream=True)
        audio_blob = audio_response.raw

        # save mp3 file
        if audio_url:
            self.save_mp3_to(audio_blob, id_coub_page)
        else:
            print("Error download file: {}".format(audio_url))

    # fix first bytes in video
    def fix_first_byte_video(self, fragment):
        video_fragment = bytearray(fragment)
        video_fragment[0] = 0
        video_fragment[1] = 0
        return str(video_fragment)

    def range_download_video(self, video_url, video_size, referer, name, headers):
        # get options - simulate requests
        video_options = requests.options(video_url, headers=headers, stream=True)

        # add special headers
        headers['Access-Control-Request-Headers'] = 'range'
        headers['Access-Control-Request-Method'] = 'GET'
        headers['Origin'] = 'https://coub.com'

        # range downloasd
        headers['Range'] = 'bytes=0-'
        video_response = requests.get(video_url, headers=headers, stream=True)
        reset_file_binary = True
        with open(self._path_to+name+".mp4", 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=1024):
                if chunk: # filter out keep-alive new chunks
                    if reset_file_binary:
                        chunk = self.fix_first_byte_video(chunk)
                        reset_file_binary = False
                    f.write(chunk)

    # save files by type to path
    def save_mp3_to(self, blob_file, name):
        with open(self._path_to+name+".mp3", 'wb') as file_handle:
            shutil.copyfileobj(blob_file, file_handle)

help = '''
    coub_downloade.py -i <path_to_input_file> -p <path_to_download> -s <sleep>
'''

if __name__ == "__main__":
    downloader = CoubDownloader()
    inputfile = ''
    path_download = ''
    sleep_sec = 0
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hi:p:s:")
    except getopt.GetoptError:
        print help
        sys.exit()

    for opt, arg in opts:
        if opt == '-h':
            print help
            sys.exit()
        elif opt in ("-i"):
            inputfile = arg
        elif opt in ("-p"):
            path_download = arg
        elif opt in ("-s"):
            sleep_sec = float(arg)

    if not (inputfile or os.path.isfile(inputfile)):
        print(help)
        sys.exit()

    if path_download and os.path.isdir(path_download):
        downloader.set_path(path_download)
    else:
        print(help)
        sys.exit()

    # package download coub video from file
    with codecs.open(inputfile, "r", "utf-8") as file_handle:
        for line in file_handle.readlines():
            url = line.strip()
            if url:
                downloader.download(url)
            if sleep_sec:
                time.sleep(sleep_sec)

    print("Download finished")