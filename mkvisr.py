#!/usr/bin/env/python
'''
turns your crap files into ffv1 mkv
'''

import os
import re
import sys
import argparse
import subprocess

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
		returncode = subprocess.check_output(ffstr, shell=True)
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
            dirname = kwargs.output
            while not os.path.dirname(dirname):
                dirname = os.path.dirname(dirname)
                if not dirname:
                    break
            if dirname == '/' or not dirname:
                print "Buddy, you specified an output file without the .mkv extension"
                print "Or you specified an invalid output path"
                print "mkvisr is quitting"
                sys.exit()
            else:
                os.makedirs(os.path.join(kwargs.input.dirname, kwargs.output, kwargs.input.fname + ".mkv"))
        if not os.path.dirname(kwargs.output):
            fp = os.path.join(kwargs.input.dirname, kwargs.output)
        else:
            fp = os.path.join(os.getcwd(), kwargs.output)
        kwargs.output = dotdict({"fullpath":fp})
    return kwargs

def detect_pal(streams):
    '''
    returns true if PAL, false if NTSC
    '''
    h = ''
    for stream in streams["numberofstreams"]:
        if streams[stream + ".codec_type"] == '"video"':
            h = streams[stream + ".height"]
    if not h:
        print "Buddy, we couldn't detect the height of that video"
        sys.exit()
    else:
        if h == "486" or h == "480" or h == "243" or h == "240":
            return False
        elif h == "576":
            return True
        else:
            print "Buddy, we can't determine the broadcast standard for this file"
            print "We can only handle NTSC and PAL"
            sys.exit()

def detect_j2k(streams):
    '''
    detect j2k files
    generally these are half-height files
    i.e. frames are actually fields, 59.94, but we ~want~ 29.97 full-height
    '''
    for stream in streams["numberofstreams"]:
        if streams[stream + ".codec_type"] == '"video"':
            if streams[stream + ".codec_name"] == '"jpeg2000"':
                return True
    return False

def make_ffstr(kwargs, streams):
    '''
    generates the ffmpeg string for transcoding the file
    '''
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
    ffstr = "ffmpeg"
    _ff = ["-i","-map","-dn","-c:v","-level","-g","-slicecrc","-slices","-field_order","-vf","-color_primaries",
            "-color_trc", "-colorspace", "-color_range", "-c:a"]
    ff = dotdict({"i":kwargs.input.fullpath, "map":"0", "c:v":"ffv1", "level":"3", "g":"1",
            "slicecrc":"1", "slices":"24", "color_trc":"bt709", "color_range":"mpeg", "c:a":"copy"})
    pal = detect_pal(streams)
    if pal is True:
        ff.field_order = "bt"
        ff.vf = "setfield=tff,setdar=4/3"
        ff.color_primaries = "bt470bg"
        ff.colorspace = "bt470bg"
    else:
        ff.field_order = "bb"
        ff.vf = "setfield=bff,setdar=4/3"
        ff.color_primaries = "smpte170m"
        ff.colorspace = "smpte170m"
    j2k = detect_j2k(streams)
    if j2k is True:
        ff.vf = "weave," + ff.vf
    for f in _ff:
        key = f.replace('-','')
        if key in ff:
            ffstr = ffstr + ' ' + f + ' ' + ff[key]
        else:
            ffstr = ffstr + ' ' + f
    ffstr = ffstr + ' ' + kwargs.output.fullpath
    return ffstr

def process(kwargs):
    '''
    processes a single file
    '''
    kwargs = make_paths(kwargs)
    print "Processing " + kwargs.input.fullpath
    streams = probe_streams(kwargs.input.fullpath)
    '''for stream in streams["numberofstreams"]:
        print stream
        print streams[stream + ".codec_name"]
    for attr in streams:
        print attr
        print streams[attr]
    for stream in streams['numberofstreams']:
        for attr in streams:
            print streams[attr]'''
    ffstr = make_ffstr(kwargs, streams)
    print ffstr
    print "Outputting to " + kwargs.output.fullpath
    ffWorked = ffgo(ffstr)
    #if ffWorked is not True:
    #   ERROR
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
    do the thing
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
