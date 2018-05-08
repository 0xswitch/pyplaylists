#coding:utf-8
from __future__ import unicode_literals
from pytube import *
from moviepy import editor as mp
from sys import stdout
from json import loads, dumps
from string import printable
from os import remove, path
from shutil import copy
from datetime import date
from time import time
import argparse
from getpass import getuser

class PyPlaylist:

    def __init__(self, args):
        self.conf_path = "\\".join(__file__.split("\\")[:-1]) + "\\"
        self.settings, self.playlist_list = self.read_conf_file()
        self.output_path = (self.settings["output_path"] + "\\").replace("\\\\", "\\")
        self.itunes_path = self.settings["itunes_auto_add_path"]
        self.prog = 0
        self.msg = ""
        ##
        if args.add is not None:
            self.add_playlist(args.add)
        if args.import_itunes:
            self.import_in_itunes()
        ##
        new_videos = self.check_new_video_in_playlist()
        self.download_new_vid(new_videos)


    def add_playlist(self, playlist_url):
        t = Playlist(playlist_url)
        try:
            c = t.parse_links()
        except Exception as e:
            print e
            print "[!] Invalid playlist url :: %s" % playlist_url
            exit(-1)
        name = t.playlist_name

        self.playlist_list.append({
            "url" : playlist_url,
            "name" : name,
            "video_list" : []

        })

        self.write_conf(self.playlist_list)
        print "[+] New playlist : %s with %i files !" % (name, len(c))

    def check_new_video_in_playlist(self):
        marked_fur_download = {}
        print "[+] Checking %i playlists" % len(self.playlist_list)
        for playlist in self.playlist_list:
            print "[+] Analyzing %s" % playlist["name"]
            links = Playlist(playlist["url"]).parse_links()
            already_download = [ url["url"] for url in playlist["video_list"] if url["dowloaded"] is  True]
            if  len(links) != len(already_download):
                print "[+] %i files to download" % (len(links) - len(already_download))
                for link in links:
                    if link not in already_download:
                        try:
                            marked_fur_download[playlist["name"]].append(link)
                        except KeyError:
                            marked_fur_download[playlist["name"]] = []
                            marked_fur_download[playlist["name"]].append(link)
            else:
                print "[+] %s is up-to-date with %i files" % (playlist["name"], len(links))
        return marked_fur_download

    def progress(self, stream, chunck, file_handle, bytes_remaining):
        if self.prog == 0:
            self.prog = bytes_remaining
        print "[+] %s [ %.2f / 100 ]\r" % (self.msg, 100.0 * float(self.prog - bytes_remaining) / float(self.prog)),
        stdout.flush()

    def import_in_itunes(self):
        c = 0
        for playlist in self.playlist_list:
             for song in playlist["video_list"]:
                 if not song["imported"]:
                     try:
                        copy(song["path"], unicode(self.itunes_path + song["name"] + ".mp3"))
                        print "[+] Successfully imported %s in iTunes" % song["name"]
                        song["imported"] = True
                        self.write_conf(self.playlist_list)
                        c += 1
                     except Exception as e:
                        print "[!] Error while copying file to iTunes"
                        print "[!] " + str(e)
                        exit(1)
        print "[+] Done with %i songs !" % c


    def download_new_vid(self, list_of_url):
        for playlist in list_of_url:
            for vid in list_of_url[playlist][::-1]:
                y =  YouTube("https://www.youtube.com" + vid)
                self.prog = 0
                titre = "".join([char for char in y.title if char in printable]).replace("?","").replace(".","")
                self.msg = "Dowloading %s" % titre
                y.register_on_progress_callback(self.progress)

                tmp = y.streams.get_by_itag(22)
                if tmp is None:
                    tmp = y.streams.get_by_itag(18)

                tmp.download(self.output_path, filename=titre)
                print
                t = mp.VideoFileClip(self.output_path + titre + ".mp4")
                t.audio.write_audiofile(self.output_path + titre + ".mp3")
                t.close()

                if self.settings["import_itunes"]:
                    copy(self.output_path + titre + ".mp3", unicode(self.itunes_path + titre + ".mp3"))
                    print "[+] Successfully imported in iTunes"
                remove(self.output_path + titre + ".mp4")

                for i in range(0, len(self.playlist_list)):
                    if self.playlist_list[i]["name"] == playlist:
                        self.playlist_list[i]["video_list"].append({
                            "url" : vid,
                            "name" : titre,
                            "dowloaded" : True,
                            "imported" : self.settings["import_itunes"],
                            "path" : self.output_path + titre + ".mp3",
                            "when" : date.fromtimestamp(time()).strftime("%d/%m/%y")
                        })

                self.write_conf(self.playlist_list)

    def write_conf(self, what):
        try:
            open(self.conf_path + "list.json", "w").write(dumps({"playlists": what}, indent=4))
        except Exception as e:
            print "[!] Error reading conf file at %s " % self.conf_path + "list.json"
            print "[!] " + e

    def write_settings(self, what):
        try:
            open(self.conf_path + "settings.json", "w").write(dumps(what, indent=4))
        except Exception as e:
            print "[!] Error reading settings file at %s " % self.conf_path + "setting.json"
            print "[!] " + e

    def create_settings_file(self):
        print "[+] Creating settings file"
        output_path = raw_input("\tAbsolute path to download directory : ")
        if not path.isdir(output_path.replace("/", "\\")):
            print "[!] Error %s is not a directory" % output_path
            exit(1)
        import_itunes = raw_input("\tAutomatically import in iTunes ? (Y/n) : ")
        import_itunes = False if import_itunes == "n" else True
        path_to_itunes = "C:\\Users\\" + getuser() + "\\Music\\iTunes\\iTunes Media\\Ajouter automatiquement \u00e0 iTunes\\"
        print "\tPath to iTunes automatic directory is : %s" % path_to_itunes
        print "\tYou may change it later in the settings file"

        self.write_settings({
            "settings" : {
                "output_path" : (output_path.replace("/", "\\") + "\\").replace("\\\\", "\\"),
                "import_itunes": import_itunes,
                "itunes_auto_add_path":path_to_itunes}})


    def read_settings_file(self):
        print self.conf_path
        try:
            return loads(open(self.conf_path + "settings.json", "r").read())["settings"]
        except:
            print "[!] Settings file not found"
            a = raw_input("[!] Would you create one (Y/n) : ")
            if  a == "n" or a == "N" :
                print "[!] Exiting"
                exit(1)
            else:
                self.create_settings_file()
                return loads(open(self.conf_path + "settings.json", "r").read())["settings"]

    def read_conf(self):
        try:
            return loads(open(self.conf_path + "list.json", "r").read())["playlists"]
        except:
            print "[!] List not found, creating it"
            self.write_conf([])
            return loads(open(self.conf_path + "list.json", "r").read())["playlists"]

    def read_conf_file(self):
        try:
            return (self.read_settings_file(),
                    self.read_conf())

        except Exception as e:
            print "[!] Error while reading conf file : "
            print e
            exit(-1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--add", help="Add new playlist")
    parser.add_argument("--import-itunes",action="store_true", help="Import song in iTunes")
    PyPlaylist(parser.parse_args())


