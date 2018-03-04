#!/usr/bin/env python3

import os
import sys
import glob
import argparse
import datetime
import urllib.request

# usage: ./mc-put.py my-bucket my-file.zip file2 'fileglob*'

def upload(key, secret, host, bucket, filename):
    """
    call this function when using this file as a library

    date header must be relatively in sync with server or you
    get forbidden error

    returns True on success
    raises on error
    """
    base_name = os.path.basename(filename)

    try:
        hostname, port = host.split(':')
    except ValueError:
        hostname = host

    resource     = f"/{bucket}/{base_name}"
    content_type = "application/octet-stream"
    #date         = filetime(filename).strftime('%a, %d %b %Y %X %z')
    date         = tznow().strftime('%a, %d %b %Y %X %z')
    _signature   = f"PUT\n\n{content_type}\n{date}\n{resource}"
    signature    = sig_hash(secret, _signature)

    url = f"https://{host}{resource}"
    headers = {
        'Host':          hostname,
        'Date':          date,                      # eg. Sat, 03 Mar 2018 10:11:16 -0700
        'Content-Type':  content_type,
        'Authorization': f"AWS {key}:{signature}",
    }
    # import pprint
    # pprint.pprint(headers)

    req = urllib.request.Request(url, data=open(filename), method='PUT', headers=headers)
    resp = urllib.request.urlopen(req)
    return resp.read() or True


def parse_cmdline(args):

    desc = "upload some files to minio/s3"
    epilog = """
    example:
        ./mc-put.py -k key -s secret -u minio.example.com:8081 mybucket myfiles*.zip
    """

    parser = argparse.ArgumentParser(description=desc, epilog=epilog)

    parser.add_argument('-k', '--key', default=os.getenv('S3_KEY', ''), type=str,
                        help="minio/s3 key, default envvar S3_KEY")
    parser.add_argument('-s', '--secret', default=os.getenv('S3_SECRET', ''), type=str,
                        help="minio/s3 secret, default envvar S3_SECRET")
    parser.add_argument('-H', '--host', default=os.getenv('S3_HOST', ''), type=str,
                        help="minio/s3 host, default envvar S3_HOST")
    parser.add_argument('bucket', help="name of bucket")
    parser.add_argument('files', nargs='+', help="file list, wildcards allowed")

    args = parser.parse_args()

    if not all([args.key, args.secret, args.host, args.bucket, args.files]):
        print("must supply a key, secret, server host, and file(s)")
        sys.exit(1)

    if os.path.exists(args.bucket):
        print("it looks like you forgot to give a bucket as given bucket is a file")
        sys.exit(1)

    if args.host.startswith('http'):
        _, args.host = args.host.split('://')

    return args


def filetime(filename):
    t = os.path.getmtime(filename)
    ts = datetime.datetime.fromtimestamp(t)
    return ts.astimezone(tz=None)


def tznow():
    def utc_to_local(utc_dt):
        return utc_dt.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)

    ts = datetime.datetime.utcnow()
    return utc_to_local(ts)

# based on: https://gist.github.com/heskyji/5167567b64cb92a910a3
def sig_hash(secret, sig):
    import hashlib
    import hmac
    import base64

    #signature=`echo -en ${sig} | openssl sha1 -hmac ${secret} -binary | base64`

    secret     = bytes(secret, 'UTF-8')
    sig        = bytes(sig, 'UTF-8')

    digester   = hmac.new(secret, sig, hashlib.sha1)
    signature1 = digester.digest()
    signature2 = base64.standard_b64encode(signature1)
    # signature2 = base64.urlsafe_b64encode(signature1)

    return str(signature2, 'UTF-8')


def mk_filelist(args):
    files = []

    for f in args.files:
        # note: glob filters out non-existant files
        for fname in glob.glob(f):
            files.append(fname)

    seen = set()
    seen_add = seen.add
    return [f for f in files if not (f in seen or seen_add(f))]


def main(args):
    args = parse_cmdline(args)
    #print(args)

    files = mk_filelist(args)

    for filename in files:
        try:
            upload(args.key, args.secret, args.host, args.bucket, filename)
            print(f"uploaded: {filename}")
        except urllib.error.HTTPError as e:
            print("error uploading: {}".format(filename))
            print(e)
            sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])
