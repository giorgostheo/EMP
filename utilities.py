"""
Utilities module for EMP command-line tool.

This module provides functions and classes to support the main application,
including argument parsing, file processing, and version control.
"""

import json
from pathlib import Path
import hashlib
from stat import S_ISDIR
from termcolor import colored
from numpy import unique
from datetime import datetime
import os

# Import logging configuration
import log_utils
import logging

logger = logging.getLogger(__name__)

def time_str():
    """
    Returns the current timestamp formatted as hh:mm:ss.ms
    """
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]

def scribe(msg, hostname=None, color=None):
    """
    Returns the current timestamp formatted as hh:mm:ss.ms
    """
    vl = int(os.getenv('V', '0'))

    if hostname is None:
        if color is None:
            if vl>0:
                print(f"[{time_str()}] | {msg}")
        else:
            print(colored(f"[{time_str()}] | {msg}", color))
    else:
        if color is None:
            if vl>0:
                print(f"[{time_str()}] | [{hostname}] {msg}")
        else:
            print(colored(f"[{time_str()}] | [{hostname}] {msg}", color))



def parse_args(target: list) -> list:
    """
    Parses the arguments and returns a dict of commands and args
    """
    commands = []
    processes = target.split(";")
    for process in processes:
        command_args = process.strip().split(" ", 1)
        command = command_args.pop(0)
        args = "" if not command_args else command_args[0].strip()
        commands.append([command, args])
    return commands


def parse_file(path: str) -> list:
    """
    Parses commands from file
    """
    with open(Path(path)) as f:
        lines = [line.rstrip() for line in f]
    commands = ";".join(lines)
    return parse_args(commands)


class VersionControl:
    """
    Responsible for finding file changes between local and deployed module
    """

    def __init__(self, sftp, source_dir, verbose):
        self.sftp = sftp
        self.source_dir = source_dir
        self.target_dir = self.sftp.getcwd()
        self.module_name = self.source_dir.rpartition('/')[-1]
        self.verbose = verbose
        self.should_rebuild = False
        self.commit_image_json_dir = self._commit_json_dir()
        self.commits_image = {}
        self.NEW = []
        self.UPDATED = []
        self.MOVED = []
        self.RENAMED = []
        self.DELETED = []

    def _commit_json_dir(self):
        '''
        Returns the directory of the commit_image.json for given module
        '''
        # folder will be assigned using a config file later on
        # Currently we will just with the module folder
        commit_image_dir = self.source_dir
        module = self.module_name
        commit_image_json_dir = f'{commit_image_dir}/.{module}_commit_image.json'
        return commit_image_json_dir

    def _hash_file(self, fname, remote=False):
        """
        Open file and perform md5 hashing
        """
        """TODO: reading in ssh is slow, check speeds of prefetch and
        getting the whole file locally
        """

        """
        We can perform chunk.strip() in order to eliminate whitespaces as a file change
        """

        hash_md5 = hashlib.md5()
        try:
            if remote:
                file = self.sftp.open(fname)
                file.prefetch()
                # file = self.sftp.open(fname, bufsize=32768)
                for chunk in iter(lambda: file.read(4096), b""):
                    hash_md5.update(chunk.strip())
            else:
                with open(fname, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk.strip())
        except:
            #print(f'File {fname} not found.')
            return ''

        return hash_md5.hexdigest()

    def _listdir(self, dir, remote):
        listdir = self.sftp.listdir_attr(dir) if remote else os.listdir(dir)
        return listdir

    def _isdir(self, dir, file, remote):
        isdir = (
            S_ISDIR(file.st_mode)
            if remote
            else os.path.isdir(self._join(dir, file, remote))
        )
        return isdir

    def _join(self, dir, file, remote):
        return f"{dir}/{file.filename}" if remote else f"{dir}/{file}"

    def _get_files(self, directory, ignore=[], remote=False):
        """
        Returns the dir of every file in a local or remote enviroment
        Ignore is for files, NOT for folders
        """
        # Keep only filename from ignore
        ignore = [f.rpartition('/')[-1] for f in ignore]
        files = []
        available_folders = [directory]
        while available_folders:
            current_folder = available_folders.pop(0)
            for file in self._listdir(current_folder, remote):
                if file not in ignore:
                    file_path = self._join(current_folder, file, remote)
                    if self._isdir(current_folder, file, remote):
                        available_folders.append(file_path)
                    else:
                        if file not in ignore:
                            files.append(file_path)
        return files
    
    def _folder_checksum(self, directory, ignore=[], remote=False):
        """
        Returns a dictionary with every file and its hash value
        """
        hash_dict = {}
        try:
            files = []
            last_commit = list(self.commits_image.values())[-1]
            last_commit_files = last_commit['files_in_commit']
            # In remote we will only check for files contained in last commit
            if remote:
                for file in last_commit_files:
                    full_dir = f"{directory}/{file}"
                    files.append(full_dir)
            # If locally, we will check every file contained in module
            else:
                files = self._get_files(directory, ignore=ignore, remote=remote)

            for file in files:
                file_hash = self._hash_file(file, remote)
                fname = self._strip_dir(file, directory)
                hash_dict.update({fname: file_hash})
        except Exception as e:
            raise e
        return hash_dict

    def _print_changes(self):
        """
        Prints the changes found in the source versus the target module
        """
        if any([self.NEW, self.UPDATED, self.MOVED, self.RENAMED, self.DELETED]):
            logger.info("Changes deployed in module:")

            new_updated = self.NEW + self.UPDATED
            if new_updated:
                logger.info("NEW/UPDATED FILES:")
            for file in self.NEW + self.UPDATED:
                logger.info(f"\t- {file}")  # Using colored for user output

            moved_renamed = self.MOVED + self.RENAMED
            if moved_renamed:
                logger.info("MOVED/RENAMED FILES:")
            for file in moved_renamed:
                change_str = "{} -> {}".format(file["target"], file["source"])
                logger.info(f"\t- {change_str}")  # Using colored for user output

            if self.DELETED:
                logger.info("DELETED FILES:")
            for file in self.DELETED:
                logger.info(f"\t- {file}")  # Using colored for user output
        else:
            logger.info("No changes detected")

    def _mkdir(self, dir):
        '''
        Creates folders of a directory remotely recursively
        '''
        subfolders = dir.split("/")
        current_dir = ""
        for folder in subfolders:
            current_dir = f"{current_dir}/{folder}".strip("/")
            try:
                self.sftp.mkdir(current_dir)
            except IOError:
                pass

    def _strip_dir(self, input, strip_on):
        """
        Strips file(s) directory
        """
        if isinstance(input, list):
            for i, file in enumerate(input):
                stripped = file.split(strip_on)[-1].strip("/")
                input[i] = stripped
        else:
            input = input.split(strip_on)[-1].strip("/")
        return input

    def _parse_commit_image(self):
        """
        Checks if a commit_image.json exists locally and save it's contents in self.commits_image
        """
        commits_image_json_dir = self.commit_image_json_dir
        try:
            f = open(commits_image_json_dir)
            commits_image = json.load(f)
            self.commits_image = commits_image
        except:
            # The initial empty commit has key:0
            self.commits_image = {0: {
                'commit_date': '',
                'files_in_commit': []
                }
            }

    def _update_commit_image(self):
        """
        Updates the commit_image with the current commit
        """
        base_dir = self.source_dir
        commit_image_json_dir = self.commit_image_json_dir
        commit_image_filename = commit_image_json_dir.rpartition('/')[-1]

        # Get latest id from json file, if it exists, could use max() too
        id = 1
        commits_image = self.commits_image
        if commits_image:
            id = list(commits_image.keys())[-1]
            id = int(id) + 1

        # Get files of current commit
        current_commit = self._get_files(base_dir)
        current_commit = self._strip_dir(current_commit, base_dir)

        # Remove .image_file from current commit if it exists
        if commit_image_filename in current_commit:
            image_file_index = current_commit.index(commit_image_filename)
            current_commit.pop(image_file_index)

        # Format commit for json
        _datetime = datetime.now()
        commits_image.update({
            id: {
                'commit_date': _datetime,
                'files_in_commit': current_commit
             }}
        )

        # Create parent directory of commit_image if it doesn't exist
        commit_image_parent = commit_image_json_dir.rpartition('/')[0]
        try:
            os.makedirs(commit_image_parent, exist_ok=True)
        except Exception as e: raise e

        # Update json
        # Commit with key:0 is the initial empty commit. Remove if it exists
        with open(commit_image_json_dir, 'w') as fp:
            commits_image.pop(0, None)
            json.dump(commits_image, fp, indent=4, default=str)

    def compare_modules(self):
        """
        Returns  lists: updated, moved, deleted
        New are the files that are introduced by the source for the first time
        Updated are the files that exist in both dirs but have been altered
        Moved are the files that exists in both dirs, haven't been altered,
        but have been moved
        Renamed are exsiting files, renamed
        Deleted are files that exist in the target but do not exist
        in the source
        """
        verbose = self.verbose
        commit_image_json_dir = self.commit_image_json_dir
        
        if verbose:
            logger.debug("Checking for changes in module..")

        # Parse last commit image
        self._parse_commit_image()

        # Get hash value of each file in given folder
        source_not_found = {}
        source_dict = self._folder_checksum(
            self.source_dir, ignore=[commit_image_json_dir], remote=False
            )
        target_dict = self._folder_checksum(
            self.target_dir, ignore=[commit_image_json_dir], remote=True
            )

        # Check for updated files
        for source_file in source_dict.keys():
            try:
                source_hash = source_dict[source_file]
                target_hash = target_dict[source_file]
                if source_hash != target_hash:
                    self.UPDATED.append(source_file)
                target_dict.pop(source_file)
            except KeyError:
                source_not_found.update({source_file: source_hash})

        # Check for renamed or moved files
        for source_file in source_not_found.keys():
            for target_file in target_dict.keys():
                if source_dict[source_file] == target_dict[target_file]:
                    change_dict = {"source": source_file, "target": target_file}
                    source_subdir = source_file.rpartition("/")[0]
                    target_subdir = target_file.rpartition("/")[0]
                    # if both source and target files have the
                    # same dir then its just a rename
                    if source_subdir == target_subdir:
                        self.RENAMED.append(change_dict)
                    else:
                        self.MOVED.append(change_dict)
                    break

        # Remove renamed/moved files from dictionaries
        for file in self.MOVED + self.RENAMED:
            source_not_found.pop(file["source"])
            target_dict.pop(file["target"])

        # Whats left on source is considered new file
        self.NEW = list(source_not_found.keys())
        
        # Whats left on target is considered deleted, as it no longer
        # exists on source
        self.DELETED = list(target_dict.keys())
        self._print_changes()

    def update_target(self, requirements="requirements.txt"):
        """
        Uploads target module based on the changes found
        """
        verbose = self.verbose
        source_dir = self.source_dir
        target_dir = self.target_dir

        # Set new and updated files
        new_updated = self.NEW + self.UPDATED
        self.should_rebuild = requirements in new_updated

        for file in new_updated:
            source_dir_file = f"{source_dir}/{file}"
            target_dir_file = f"{target_dir}/{file}"

            # Create recursively file's directory if it doesn't exist
            new_dir = file.rpartition("/")[0]
            self._mkdir(new_dir)
            try:
                self.sftp.put(source_dir_file, target_dir_file)
            except IOError:
                pass

        # Move files
        for file in self.MOVED:
            target_dir_new = "{}/{}".format(target_dir, file["source"])
            target_dir_old = "{}/{}".format(target_dir, file["target"])

            # Create recursively file's directory if it doesn't exist(remotely)
            new_dir = file["source"].rpartition("/")[0]
            self._mkdir(new_dir)
            try:
                self.sftp.rename(target_dir_old, target_dir_new)
            except IOError:
                pass

        # Rename files
        for file in self.RENAMED:
            target_dir_new = "{}/{}".format(target_dir, file["source"])
            target_dir_old = "{}/{}".format(target_dir, file["target"])
            self.sftp.rename(target_dir_old, target_dir_new)

        # Make deletions
        for file in self.DELETED:
            target_dir_file = f"{target_dir}/{file}"
            self.sftp.remove(target_dir_file)

        # Delete empty directories
        may_be_empty = []
        for dict in self.MOVED:
            may_be_empty.append(dict["target"])
        may_be_empty = may_be_empty + self.DELETED
        unique_dirs = list(unique(may_be_empty))
        while unique_dirs:
            file = unique_dirs.pop(0)
            parent_dir = file.rpartition("/")[0]
            full_dir = "{}/{}".format(target_dir, parent_dir)
            # If directory of a deleted file is empty
            has_files = len(self._listdir(full_dir, remote=True))
            if not has_files:
                # delete it
                self.sftp.rmdir(full_dir)
                # Check if parent folder is now empty
                unique_dirs.append(parent_dir)

        if any([self.NEW, self.UPDATED, self.MOVED, self.RENAMED, self.DELETED]):
            self._update_commit_image()

        if verbose:
            self._print_changes()