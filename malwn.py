#!/usr/bin/env python3
import os.path
import os
from argparse import ArgumentParser

import threading
import queue

import core.dirwalker as dirwalker
import core.yaramatch as yaramatch
import core.fileinfo as fileinfo
import core.cli as cli
import core.modules as modules

from configparser import ConfigParser

MALWN_PATH = os.path.dirname(os.path.realpath(__file__))
CONFIG =  MALWN_PATH + '/config.ini'
malwn_conf = {}

def init_config(reset=False):
    global malwn_conf
    config = ConfigParser()
    config.read(CONFIG)
    if reset or not 'malwn' in config:
        config['malwn'] = {}
    if not 'yara_path' in config['malwn']:
        default = MALWN_PATH + "/yara-rules/"
        p = input(f'please enter path to yara rules [{default}]: ')
        if p == "":
            p = default
        yara_path = os.path.abspath(os.path.expanduser(p))
        config['malwn']['yara_path'] = yara_path
        reset = True
    if not 'module_path' in config['malwn']:
        default = MALWN_PATH + "/modules/"
        p = input(f'please enter path to malwn modules [{default}]: ')
        if p == "":
            p = default
        module_path = os.path.abspath(os.path.expanduser(p))
        config['malwn']['module_path'] = module_path
        reset = True
    if reset:
        with open(CONFIG, 'w') as configfile:
            config.write(configfile)
    malwn_conf = config['malwn']

def fileworker():
    while True:
        info = filequeue.get()
        if not info:
            break;
        matches = yaramatch.get_yaramatches(info, args)
        cli.debug_print("got matches", args)
        rulenames = [str(item) for e in matches for item in matches[e]]

        r = {}
        r["fileinfo"] = info
        r["yaramatches"] = matches
        r["modules"] = modules.get_compatible_modules(rulenames)
        results.append(r)
        filequeue.task_done()

def add_args(parser):
    parser.add_argument("-s", "--sort", action="store_true", default=False, help="sort results by timestamp")
    parser.add_argument("-t", "--threads", type=int, default=10, help="number of concurrent threads")
    parser.add_argument("--reset", action="store_true", default=False, help="reset config file")
    return parser

if __name__ == '__main__':

    fileinfo.init_formats(MALWN_PATH + "/formats/")
    cli.init_formats(MALWN_PATH + "/output/")

    parser = ArgumentParser()
    parser = dirwalker.add_args(parser)
    parser = fileinfo.add_args(parser)
    parser = yaramatch.add_args(parser)
    parser = cli.add_args(parser)
    parser = modules.add_args(parser)

    parser = add_args(parser)
    args = parser.parse_args()

    init_config(args.reset)

    cli.debug_print("compiling yara rules", args)
    yaramatch.init_rules(malwn_conf["yara_path"], args)
    modules.init_modules(malwn_conf["module_path"])

    filequeue = queue.Queue()

    for file in dirwalker.get_all_files(args):
        if not os.path.isfile(file):
            continue
        cli.debug_print("processing file {}".format(file), args)

        info = fileinfo.get_fileinfo(file, args)
        if info == None:
            continue
        cli.debug_print("got fileformat", args)
        filequeue.put(info)

    threads = []
    results = []
    for i in range(args.threads):
        t = threading.Thread(target=fileworker)
        t.start()
        threads.append(t)

    cli.debug_print("threads started", args)
    filequeue.join()
    cli.debug_print("filequeue finished", args)
    for i in threads:
        filequeue.put(None)
    for t in threads:
        t.join()
    cli.debug_print("threads stopped", args)

    if args.sort:
        results = sorted(results, key=lambda x: x["fileinfo"].time)
    for r in results:
        cli.print_result(r, args)
        modules.run(r["fileinfo"].filename, r["modules"], args)
