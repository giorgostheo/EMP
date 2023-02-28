from pathlib import Path
import hashlib
from stat import S_ISDIR
from termcolor import colored
from numpy import unique
import os


def parse_args(target: list) -> list:
    """
    Parses the arguments and returns a dict of commands and args
    """
    commands = []
    processes = target.split(';')
    for i, process in enumerate(processes):
        command_args = process.strip().split(' ',1)
        command = command_args.pop(0)
        args = '' if not command_args else command_args[0].strip()
        commands.append([command, args])
    return commands


def parse_file(path: str) -> list:
    """
    Parses commands from file
    """
    with open(Path(path)) as f:
        lines = [line.rstrip() for line in f]
    commands = ';'.join(lines)
    return parse_args(commands)


class VersionControl():
    '''
    Responsible for finding file changes between local and deployed module
    '''
    def __init__(self, sftp, source_dir, verbose):
        self.sftp = sftp
        self.source_dir = source_dir
        self.target_dir = self.sftp.getcwd()
        self.verbose = verbose
        self.should_rebuild = False
        self.NEW = []
        self.UPDATED = []
        self.MOVED = []
        self.RENAMED = []
        self.DELETED = []

    def _hash_file(self, fname, remote=False):
        '''
        Open file and perform md5 hashing
        '''
        '''TODO: reading in ssh is slow, check speeds of prefetch and
        getting the whole file locally
        '''

        hash_md5 = hashlib.md5()
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
        return hash_md5.hexdigest()
            
    def _listdir(self, dir, remote):
        listdir = self.sftp.listdir_attr(dir) if remote else os.listdir(dir)
        return listdir

    def _isdir(self, dir, file, remote):
        isdir = S_ISDIR(file.st_mode) if remote else os.path.isdir(self._join(dir, file, remote))
        return isdir

    def _join(self, dir, file, remote):
        return f'{dir}/{file.filename}' if remote else f'{dir}/{file}'
    
    def _folder_checksum(self, directory, remote=False):
        '''
        Returns a dictionary with the each file and its hash value
        '''
        relative_dir = '/{}/'.format(directory.strip('/').split('/')[-1])
        try:
            files_dict = {}
            available_folders = [directory]
            while available_folders:
                current_folder = available_folders.pop(0)
                for file in self._listdir(current_folder, remote):
                    file_path = self._join(current_folder, file, remote)
                    if self._isdir(current_folder, file, remote):
                        available_folders.append(file_path)
                    else:
                        file_hash = self._hash_file(file_path, remote)
                        f_name = '{}'.format(file_path.split(relative_dir, 1)[-1])
                        files_dict.update({
                            f_name: str(file_hash)
                        })
            return files_dict
        except Exception as e:
            raise e
        
    def _print_changes(self):
        '''
        Prints the changes found in the source versus the target module
        '''
        if any([self.NEW, self.UPDATED, self.MOVED, self.RENAMED, self.DELETED]):
            print('Changes deployed in module:')

            new_updated = self.NEW+self.UPDATED
            if new_updated:
                print('NEW/UPDATED FILES:') 
            for file in (self.NEW+self.UPDATED):
                print(colored(f'\t- {file}', 'green'))

            moved_renamed = self.MOVED+self.RENAMED
            if moved_renamed:
                print('MOVED/RENAMED FILES:')
            for file in moved_renamed:
                change_str = '{} -> {}'.format(file['target'], file['source'])
                print(colored(f'\t- {change_str}', 'yellow'))

            if self.DELETED:
                print('DELETED FILES:')
            for file in (self.DELETED):
                print(colored(f'\t- {file}', 'red'))
        else:
            print('No changes detected')

    def compare_modules(self):
        '''
        Returns  lists: updated, moved, deleted
        New are the files that are introduced by the source for the first time
        Updated are the files that exist in both dirs but have been altered
        Moved are the files that exists in both dirs, haven't been altered,
        but have been moved
        Renamed are exsiting files, renamed
        Deleted are files that exist in the target but do not exist
        in the source
        '''
        verbose = self.verbose
        if verbose:
            print('\n-Checking for changes in module..')
        source_not_found = {}
        source_dict = self._folder_checksum(self.source_dir)
        target_dict = self._folder_checksum(self.target_dir, remote=True)
        for source_file in source_dict.keys():
            try:
                source_hash = source_dict[source_file]
                target_hash = target_dict[source_file]
                if source_hash != target_hash:
                    self.UPDATED.append(source_file)
                target_dict.pop(source_file)
            except KeyError:
                source_not_found.update({source_file: source_hash})
        for source_file in source_not_found.keys():
            for target_file in target_dict.keys():
                if source_dict[source_file] == target_dict[target_file]:
                    change_dict = {
                        'source': source_file,
                        'target': target_file
                        }
                    source_subdir = source_file.rpartition('/')[0]
                    target_subdir = target_file.rpartition('/')[0]
                    # if both source and target files have the 
                    # same dir then its just a rename
                    if source_subdir == target_subdir:
                        self.RENAMED.append(change_dict)
                    else:
                        self.MOVED.append(change_dict)
                    break
        for file in (self.MOVED+self.RENAMED):
            source_not_found.pop(file['source'])
            target_dict.pop(file['target'])

        self.NEW = list(source_not_found.keys())
        self.DELETED = list(target_dict.keys())

    def update_target(self):
        '''
        Uploads target module based on the changes found
        '''
        verbose = self.verbose
        requirements = 'requirements.txt'

        # set new and updated files
        new_updated = self.NEW+self.UPDATED
        self.should_rebuild = requirements in new_updated

        for file in (new_updated):
            source_dir_file = f'{self.source_dir}/{file}'
            target_dir_file = f'{self.target_dir}/{file}'
            try:
                self.sftp.put(source_dir_file, target_dir_file)
            except IOError:
                # create folders recursivly
                new_dir = file.rpartition('/')[0]
                subfolders = new_dir.split('/')
                current_dir = ''
                for folder in subfolders:
                    current_dir = f'{current_dir}/{folder}'.strip('/')
                    try:
                        self.sftp.mkdir(current_dir)
                    except IOError:
                        pass
                self.sftp.put(source_dir_file, target_dir_file)

        # moves files
        for file in (self.MOVED):
            target_dir_new = '{}/{}'.format(self.target_dir, file['source'])
            target_dir_old = '{}/{}'.format(self.target_dir, file['target'])
            try:
                self.sftp.rename(target_dir_old, target_dir_new)
            except IOError:
                new_dir = file['source'].rpartition('/')[0]
                subfolders = new_dir.split('/')
                current_dir = ''
                for folder in subfolders:
                    current_dir = f'{current_dir}/{folder}'.strip('/')
                    try:
                        self.sftp.mkdir(current_dir)
                    except IOError:
                        pass
                self.sftp.rename(target_dir_old, target_dir_new)

        # renames files
        for file in (self.RENAMED):
            target_dir_new = '{}/{}'.format(self.target_dir, file['source'])
            target_dir_old = '{}/{}'.format(self.target_dir, file['target'])
            self.sftp.rename(target_dir_old, target_dir_new)

        # make deletions
        for file in self.DELETED:
            target_dir_file = f'{self.target_dir}/{file}'
            self.sftp.remove(target_dir_file)

        # delete empty directories
        may_be_empty = []
        for dict in self.MOVED:
            may_be_empty.append(dict['target'])
        may_be_empty = may_be_empty + self.DELETED
        unique_dirs = list(unique(may_be_empty))
        while unique_dirs:
            file = unique_dirs.pop(0)
            parent_dir = file.rpartition('/')[0]
            full_dir = '{}/{}'.format(self.target_dir, parent_dir)
            # if directory of a deleted file is empty
            has_files = len(self._listdir(full_dir, remote=True))
            if not has_files:
                # delete it
                self.sftp.rmdir(full_dir)
                # check if parent folder is now empty
                unique_dirs.append(parent_dir)

        if verbose:
            self._print_changes()
    


                









    
