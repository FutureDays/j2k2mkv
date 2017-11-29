#!/usr/bin/env/python
import os
import re
import sys
import argparse
import subprocess

class cd:
    '''
    Context manager for changing the current working directory
    '''
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)
    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)
    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


class dotdict(dict):
    '''
    dot.notation access to dictionary attributes
    '''
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def probe_streams(obj):
    '''
    returns dictionary with each stream element
    e.g. {"0.pix_fmt":"yuv420p10le"}
    e.g. streams["0.codec_name"] returns libx264 (or w/e)
    '''
    streams = {}
    ffstr = "ffprobe -show_streams -of flat " + obj
    output = subprocess.Popen(ffstr, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    _out = output.communicate()
    out = _out[0].splitlines()
    for o in out:
        key, value = o.split("=")
        key = key.replace("streams.stream.","")
        streams[str(key)] = value
    if streams:
        count = 0
        numberofstreams = []
        for stream in streams:
            if stream[0] in numberofstreams:
                pass
            else:
                numberofstreams.append(str(count))
                count = count + 1
        streams['numberofstreams'] = numberofstreams
        return streams
    else:
        print _out[1]
        return False

def ffgo(ffstr):
	'''
	runs ffmpeg, returns true if success, error is fail
	'''
	try:
		returncode = subprocess.check_output(ffstr)
		returncode = True
	except subprocess.CalledProcessError, e:
		returncode = e.returncode
		print returncode
	return returncode

def make_paths(kwargs):
    '''
    defines input and output paths for the file
    stores them in kwargs.input and kwargs.output
    '''
    kwargs.input.fname, kwargs.input.ext = os.path.splitext(os.path.basename(kwargs.input.fullpath))
    kwargs.input.dirname = os.path.dirname(kwargs.input.fullpath)
    if kwargs.output is None:
        kwargs.output = dotdict({"fullpath":os.path.join(kwargs.input.dirname, kwargs.input.fname + ".mkv")})
    elif os.path.isdir(kwargs.output):
        dirname = kwargs.output
        kwargs.output = dotdict({"dirname":dirname, "fname":kwargs.input.fname})
        kwargs.output.fullpath = os.path.join(kwargs.output.dirname, kwargs.output.fname + ".mkv")
    else:
        if not kwargs.output.endswith(".mkv"):
            print "Buddy, you specified an output file without the .mkv extension"
            print "We can't process it"
            return False
        if not os.path.dirname(kwargs.output):
            fp = os.path.join(kwargs.input.dirname, kwargs.output)
        else:
            fp = os.path.join(os.getcwd(), kwargs.output)
        kwargs.output = dotdict({"fullpath":fp})
    return kwargs

def process(kwargs):
    '''
    processes a single file
    '''
    print "Processing " + kwargs.input.fullpath
    kwargs = make_paths(kwargs)
    streams = probe_streams(kwargs.input.fullpath)
    for stream in streams["numberofstreams"]:
        print stream
        print streams[stream + ".codec_name"]
    '''for attr in streams:
        print attr
        print streams[attr]
    for stream in streams['numberofstreams']:
        for attr in streams:
            print streams[attr]'''
    print "Outputting to " +kwargs.output.fullpath
    return True

def init_args():
    '''
    initialize arguments from CLI
    '''
    parser = argparse.ArgumentParser(description="transcodes from j2k to ffvi")
    parser.add_argument('-i', '--input', dest='i', help="the input filepath")
    parser.add_argument('-o', '--output', dest='o', default=None, help="the output path")
    args = parser.parse_args()
    args.i = args.i.replace("\\", "/")
    if args.o:
        args.o = args.o.replace("\\", "/")
    return args

def main():
    '''
    NTSC
    ffmpeg -i input_file -map 0 -dn -c:v ffv1 -level 3 -g 1 -slicecrc 1 -slices 24 -field_order bb
    -vf setfield=bff,setdar=4/3 -color_primaries smpte170m -color_trc bt709 -colorspace smpte170m
    -color_range mpeg -c:a copy output_file.mkv
    PAL
    ffmpeg -i input_file -map 0 -dn -c:v ffv1 -level 3 -g 1 -slicecrc 1 -slices 24 -field_order bt
    -vf setfield=tff,setdar=4/3 -color_primaries bt470bg -color_trc bt709 -colorspace bt470bg
    -color_range mpeg -c:a copy output_file.mkv
    '''
    args = init_args()
    if os.path.isdir(args.i):
        for dirs, subdirs, files in os.walk(args.i):
            for f in files:
                itWorked = process(dotdict({"input":dotdict({"fullpath":os.path.join(dirs, f)}), "output":args.o}))
    else:
        match = ''
        match = re.search(r"[aA-zZ]/:", args.i)
        if match or args.i.startswith("/"):
            fp = args.i
        else:
            fp = os.path.join(os.getcwd(), args.i)
        if not os.path.exists(fp):
            print "Buddy, we couldn't find the file"
            print "Please check that it exists at:"
            print fp
            sys.exit()
        itWorked = process(dotdict({"input":dotdict({"fullpath":fp}), "output":args.o}))
    if itWorked is not True:
        print "mkvisr encountered an error"
if __name__ == '__main__':
    main()
