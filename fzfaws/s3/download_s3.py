"""s3 download operation

Contains the main function to handle the download operation from s3
"""
import fnmatch
import os
import sys
import subprocess
from s3transfer import S3Transfer
from fzfaws.s3.s3 import S3
from fzfaws.utils.pyfzf import Pyfzf
from fzfaws.utils.util import get_confirmation
from fzfaws.s3.helper.sync_s3 import sync_s3
from fzfaws.s3.helper.exclude_file import exclude_file
from fzfaws.s3.helper.s3progress import S3Progress


def download_s3(path=None, local=None, recursive=False, root=False, sync=False, exclude=[], include=[], hidden=False):
    """download files/'directory' from s3

    handles sync, download file and download recursive
    from a s3 bucket

    Args:
        path: string, path of the s3 bucket if specified
        local: string, local path if specified
        recursive: bool, opeate recursivly
        root: bool, search file from root directory
        sync: bool, use sync operation
        exclude: list, list of pattern to exclude file
        include: list, list of pattern to include file after exclude
        hidden: bool, include hidden directory during search
    Returns:
        None
    Exceptions:
        InvalidS3PathPattern: when the specified s3 path is invalid pattern
    """

    s3 = S3()
    if path:
        s3.set_bucket_and_path(path)
        # if only the bucket is specified
        # still need to process the bucket path
        if not s3.bucket_path:
            if recursive or sync:
                s3.set_s3_path()
            else:
                s3.set_s3_object()
    else:
        s3.set_s3_bucket()
        if recursive or sync:
            s3.set_s3_path()
        else:
            s3.set_s3_object()

    fzf = Pyfzf()
    if local:
        local_path = local
    else:
        local_path = fzf.get_local_file(
            root, directory=True, hidden=hidden, empty_allow=True)

    if sync:
        sync_s3(exclude=exclude, include=include, from_path='s3://%s/%s' %
                (s3.bucket_name, s3.bucket_path), to_path=local_path)
    elif recursive:
        download_list = download_dir(s3.client, s3.bucket_name, s3.bucket_path,
                                     local_path, root=s3.bucket_path, download_list=[], exclude=exclude, include=include)
        if get_confirmation('Confirm?'):
            for s3_key, dest_pathname in download_list:
                if not os.path.exists(os.path.dirname(dest_pathname)):
                    os.makedirs(os.path.dirname(dest_pathname))
                print('download: s3://%s/%s to %s' %
                      (s3.bucket_name, s3_key, dest_pathname))
                transfer = S3Transfer(s3.client)
                transfer.download_file(s3.bucket_name, s3_key, dest_pathname, callback=S3Progress(
                    s3_key, s3.bucket_name, s3.client))
                # remove the progress bar
                sys.stdout.write('\033[2K\033[1G')

    else:
        # s3 require a local file name, copy the name of the s3 key
        local_path = os.path.join(local_path, s3.bucket_path.split('/')[-1])
        # due the fact without recursive flag s3.bucket_path is set by s3.set_s3_object
        # the bucket_path is the valid s3 key so we don't need to call s3.get_s3_destination_key
        print('(dryrun) download: s3://%s/%s to %s' %
              (s3.bucket_name, s3.bucket_path, local_path))
        if get_confirmation('Confirm?'):
            print('download: s3://%s/%s to %s' %
                  (s3.bucket_name, s3.bucket_path, local_path))
            transfer = S3Transfer(s3.client)
            transfer.download_file(s3.bucket_name, s3.bucket_path, local_path, callback=S3Progress(
                s3.bucket_path, s3.bucket_name, s3.client))
            # remove the progress bar
            sys.stdout.write('\033[2K\033[1G')


def download_dir(client, bucket, bucket_path, local_path, root='', download_list=[], exclude=[], include=[]):
    """download directory from s3 recursivly

    reference: https://stackoverflow.com/a/33350380
    recursivly call download_dir to reach the bottom level and append the file path
    to the download_list

    process the destination when root is not bucket root

    Args:
        client: boto3.client('s3')
        bucket: string, name of the bucket
        bucket_path: string, which path to download or the current recursive path
        local_path: string, local destination root folder
        root: where the download begin, '' means bucket root
        download_list: list, list of file to download
    Returns:
        download_list: return the list of file to download. The loop contains a tuple
        that coould be iterate over
    """

    paginator = client.get_paginator('list_objects')
    for result in paginator.paginate(Bucket=bucket, Delimiter='/', Prefix=bucket_path):
        if result.get('CommonPrefixes') is not None:
            for subdir in result.get('CommonPrefixes'):
                download_list = download_dir(client, bucket, subdir.get(
                    'Prefix'), local_path, root, download_list, exclude, include)
        for file in result.get('Contents', []):
            if file.get('Key').endswith('/') or not file.get('Key'):
                # user created dir in S3 will appear in the result and is not downloadable
                continue
            if exclude_file(exclude, include, file.get('Key')):
                continue
            if not root:
                dest_pathname = os.path.join(local_path, file.get('Key'))
            else:
                # strip off the root if the root is not root of the bucket
                # with this, downloading sub folders like bucket/aws
                # will not create a folder called /aws in the target directory
                # rather, it will just download all files in bucket/aws to the target directory
                # nested folders within bucket/aws will still be created in the target directory
                # doing this because aws cli does it, do not want to change the behavior
                strip_root_path = '/'.join(file.get('Key').split('/')[1:])
                dest_pathname = os.path.join(local_path, strip_root_path)
            print('(dryrun) download: s3://%s/%s to %s' %
                  (bucket, bucket_path, dest_pathname))
            download_list.append((file.get('Key'), dest_pathname))
    return download_list
