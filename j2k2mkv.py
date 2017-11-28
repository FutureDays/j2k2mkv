import os
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
    '''
    streams = {}
    ffstr = "ffprobe -show_streams -of flat " + obj
    output = subprocess.Popen(ffstr, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    _out = output.communicate()
    out = _out[0].splitlines()
    for o in out:
        key, value = o.split("=")
        key = key.replace("streams.stream.","")
        streams[str(key)] = value
    if streams:
        return streams
    else:
        print _out[1]
        return False

def main():
    print "foo"

if __name__ == '__main__':
    main()
