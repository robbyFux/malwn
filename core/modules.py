import os.path
import sys

import core.loader as loader

modules = {}

def add_args(parser):
    parser.add_argument("-M", "--allmodules", default=False, action="store_true", help="run all supported modules")
    parser.add_argument("-m", "--module", action="append", help="module to run")
    return parser

def init_modules(folder):
    global modules
    if os.path.isdir(folder):
        for rulename in os.listdir(folder):
            p = folder + "/" + rulename
            if os.path.isdir(p):
                modules[rulename] = loader.import_all(p)

def get_compatible_modules(rulenames):
    global modules
    compatible_modules = {}
    for r in rulenames:
        if r in modules:
            compatible_modules[r] = modules[r]
    return compatible_modules

def run(fileinfo, compatible_modules, args):
    results = {}
    filename = fileinfo.filename
    for r in compatible_modules.keys():
        if args.allmodules or r in [m.split("/")[0] for m in args.module]:
            for module in modules[r]:
                if args.allmodules or r in args.module or f"{r}/{module.__name__}" in args.module:
                    if r not in results:
                        results[r] = {}
                    results[r][module.__name__] = module.run(filename)
    return results
