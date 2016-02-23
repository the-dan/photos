#!/usr/bin/env python
# -*- coding: utf-8 -*-


##Поиск дубликатов файлов
##
##В принципе, можно обобщить на любые типы файлов, но пока
##актуально только для картинок.
##
##Что должно уметь:
##    1. находить дубликаты:
##        1.1. по хешу
##        1.2. по имени и времения создания/изменения
##    2. иметь какой-то способ выводить картинки и метаданные к ним
##        для ручной обработки
##    3. быть быстрым
##        3.1. не хешировать то, что уже хешировалось
##            3.1.1. иметь базу, в которой хранить пути и хеши к ним
##        3.2. перехешировать по просьбе пользователя
##
##Из всего сказанного сформировались несколько частей:
##    1. обходчик папок с файлами
##        1.1. который хеширует новые файлы (которых нет в БД)
##        1.2. который хеширует все файлы (если пользователь попросил)
##        [1.3. позволят удалять из БД то, чего уже нет в файловой системе]
##    2. поисковик дубликатов
##        2.1. оперирует с БД
##        2.2. имеет разные алгоритмы поиска дубликатов
##            2.2.1. по хешу
##            2.2.2. по имени+времени создания/изменения
##    3. просмотрщик изменений
##        3.1. позволяет посмотреть side-by-side изменения

from __future__ import print_function
    

import hashlib
import os
import types
import pickle
import sys


from optparse import OptionParser

BASE_PATH=os.path.abspath(os.curdir)
DB_PATH=os.path.join(BASE_PATH, "dups.pickle")

def minus(a,b):
    result = []
    for x in a:
        if x not in b:
            result.append(x)
    return result

class Dups(object):
    """
    `elements` is dict.
    Structure:
    key -> file path
    value -> dict(hash, ctime, mtime, name)
        where name is basename (with extension)


    `hash_index` is a dict.
    Structure:
    key -> SHA1 hash
    value -> file path or list of file paths if there are several files
    with the same name
    """
    def __init__(self, config_file):
        self.config_file = config_file

        if not os.path.exists(config_file):
            self.clear()
            return
        
        with open(self.config_file, "rb") as cf:
            self.indexed_paths = pickle.load(cf)
            self.exts = pickle.load(cf)
            self.elements = pickle.load(cf)
            self.hash_index = pickle.load(cf)
        self.priorities = [
        "/Users/dan/Pictures/iPhoto Library",
#        "/Volumes/Documents/My Pictures",
        "/Volumes/Documents/My Videos"
        ]

    def clear(self):
        self.indexed_paths = []
        self.exts = []
        self.elements = {}
        self.hash_index = {}

    def save(self):
        with open(self.config_file, "wb") as cf:
            pickle.dump(self.indexed_paths, cf)
            pickle.dump(self.exts, cf)
            pickle.dump(self.elements, cf)
            pickle.dump(self.hash_index, cf)
            

    def add_path(self, path):
        assert self.indexed_paths is not None
        
        if not os.path.exists(path):
            print("Path is wrong!")
            return
        path = os.path.abspath(path)
        if path in self.indexed_paths:
            print("Path has been indexed already")
            return
        self.indexed_paths.append(path)

    def remove_path(self, path):
        self.indexed_paths.remove(path)
        # TODO: also remove all files from index

    def add_ext(self, ext):
        ext = ext.lower()
        if ext in self.exts:
            print("Extension has been added already")
            return
        self.exts.append(ext)
      
    def show_possible_duplicates(self):
        # building index "name-size"
        idx = {}
        for (k,v) in self.elements.items():
            name = os.path.basename(k)
            if not os.path.exists(k):
                continue
            size = os.path.getsize(k)
            idx_key = name.lower() #+"-"+str(size)
            idx_val = idx.get(idx_key)
            if idx_val is None:
                idx[idx_key] = [k]
            else:
                idx[idx_key].append(k)
        #print (repr(idx))
        def more_than_one_file(element):
            return type(element) == types.ListType and len(element) > 1
    
        dups = list(filter(lambda x: more_than_one_file(x), idx.values()))

        for dup in sorted(dups):
            print("="*80)
            for p in dup:
                print(p)
        print ("Total dups: %d" % (len(dups),) )
        
        for dup in sorted(dups):
            prio_paths = self.get_prioritized_paths(dup)
            if len(prio_paths) > 0:
                for x in minus(dup, prio_paths):
                    print ("# duped by %s" % (self.list_paths(prio_paths)))
                    #print ("rm %s" % (x,))
                print ('mv "%s" /Volumes/Documents/PHOTO-DUPS-THAT-ARE-IN-IPHOTO' % (x,))
        
    def get_prioritized_paths(self, dup):
        def is_prioritized(path):
            for prio_prefix in self.priorities:
                if path.lower().startswith(prio_prefix.lower()):
                    return True
            return False
        return filter(lambda x: is_prioritized(x), dup)     
           
    def list_paths(self, paths):
        if len(paths) == 1:
            return paths[0]
        else:
            return ",".join(paths)
           
    def show_duplicates(self):
        # more than one file with same hash value
        def more_than_one_file(element):
            return type(element) == types.ListType and len(element) > 1
        
        dups = list(filter(lambda x: more_than_one_file(x), self.hash_index.values()))
        
        for dup in sorted(dups):
            print("="*80)
            for p in dup:
                print(p)
        print ("Total dups: %d" % (len(dups),) )
          
        for dup in sorted(dups):
            prio_paths = self.get_prioritized_paths(dup)
            if len(prio_paths) > 0:
                for x in minus(dup, prio_paths):
                    print ("# duped by %s" % (self.list_paths(prio_paths)))
                    #print ("rm %s" % (x,))
                    print ('mv "%s" /Volumes/Documents/PHOTO-DUPS-THAT-ARE-IN-IPHOTO' % (x,))
        
       #  for dup in sorted(dups):
#               for p in dup:
#                   prio_path = get_if_in_priority(p)
#               # found priority path matching duplicate file
#               if prio_path is not None:
#                   print (prio_path)
#                   for p in dup:
#                       # skip prioritized path
#                       if p == prio_path:
#                           continue
#                       # is it non-matched prioritized path too? 
#                       if get_if_in_priority(p) is None:
#                           print ("rm %s" % (p,))

    def dedup(self):
        def more_than_one_file(element):
            return type(element) == types.ListType and len(element) > 1
        
        dups = list(filter(lambda x: more_than_one_file(x), self.hash_index.values()))

        for dup in sorted(dups):
            n = 0
            m = 1
            if len(dup) > 2:
                print("Wow!!", dup)
                m = 2
            if os.stat(dup[n]) == os.stat(dup[m]):
                f = self.elements[dup[n]]
                del self.elements[dup[n]]
                del self.hash_index[f["hash"]]


    def update(self):
        self.sync()
        self.add_new()
        
    
    def sync(self):
        """
        Syncs indexed files and disk contents

        Checks whether file is still exists, if not it is deleted from index
        """
        for e in self.elements.copy():
            if not os.path.exists(e):
                f = self.elements.get(e)
                if f is None:
                    del self.elements[e]
                    continue
                print("Deleting %s from index" % e)
                if self.hash_index.get(f["hash"]) is not None:
                    del self.hash_index[f["hash"]]
                del self.elements[e]


    def add_new(self):
        """
        Same as reindex() but checks whether file is already in elements
        """
        valid_paths = [x for x in self.indexed_paths if os.path.isdir(x)]
        if len(valid_paths) == 0:
            print("There are no valid paths", self.indexed_paths)
            return
        if len(valid_paths) != len(self.indexed_paths):
            print("Some paths are excluded: ", minus(self.indexed_paths, valid_paths))

        def add_to_index(full_path):
            file_hash = self.elements[full_path]["hash"]
            cur_element = self.hash_index.get(file_hash)
            if cur_element is not None:
                if type(cur_element) == types.ListType:
                    self.hash_index[file_hash].append(full_path)
                else:
                    self.hash_index[file_hash] = [cur_element, full_path]
            else:
                self.hash_index[file_hash] = full_path
    

        for path in valid_paths:
            for root, dirs, files in os.walk(path):
                for filename in files:
                    if len([x for x in self.exts if filename.lower().endswith(x)]) == 0:
                        continue
                    full_path = os.path.abspath(os.path.join(root, filename))
                    
                    # the only difference
                    if self.elements.get(full_path) is not None:
                        continue
                    
                    ctime = os.path.getctime(full_path)
                    mtime = os.path.getmtime(full_path)
                    size = os.path.getsize(full_path)
                    print("Hashing %s..." % full_path, end="")
                    file_hash = hashlib.sha1(open(full_path, "rb").read()).hexdigest()
                    print("done")
                    self.elements[full_path] = { "hash" : file_hash,
                                            "ctime" : ctime,
                                            "mtime" : mtime,
                                            "name" : filename
                                            }
                    add_to_index(full_path)



    def reindex(self):
        valid_paths = [x for x in self.indexed_paths if os.path.isdir(x)]
        if len(valid_paths) == 0:
            print("There is no valid paths", self.indexed_paths)
            return
        if len(valid_paths) != len(self.indexed_paths):
            print("Some paths are excluded: ", minus(self.indexed_paths, valid_paths))

        self.elements = {}
        self.hash_index = {}

        def add_to_index(full_path):
            file_hash = self.elements[full_path]["hash"]
            cur_element = self.hash_index.get(file_hash)
            if cur_element is not None:
                if type(cur_element) == types.ListType:
                    self.hash_index[file_hash].append(full_path)
                else:
                    self.hash_index[file_hash] = [cur_element, full_path]
            else:
                self.hash_index[file_hash] = full_path
    

        for path in valid_paths:
            for root, dirs, files in os.walk(path):
                for filename in files:
                    if len([x for x in self.exts if filename.lower().endswith(x)]) == 0:
                        continue
                    full_path = os.path.abspath(os.path.join(root, filename))
                    ctime = os.path.getctime(full_path)
                    mtime = os.path.getmtime(full_path)
                    size = os.path.getsize(full_path)
                    print("Hashing %s..." % full_path, end="")
                    file_hash = hashlib.sha1(open(full_path, "rb").read()).hexdigest()
                    print("done")
                    self.elements[full_path] = { "hash" : file_hash,
                                            "ctime" : ctime,
                                            "mtime" : mtime,
                                            "name" : filename
                                            }
                    add_to_index(full_path)

    def show_all(self):
        if len(self.indexed_paths) > 0:
            print("Indexable paths:")
            for x in self.indexed_paths:
                print(x)
            print()
        if len(self.exts) > 0:
            print ("Indexable extensions:")
            for x in self.exts:
                print (x)
    
    def show_other(self, excludes):
        valid_paths = [x for x in self.indexed_paths if os.path.isdir(x)]
        if len(valid_paths) == 0:
            print("There are no valid paths", self.indexed_paths)
            return
        if len(valid_paths) != len(self.indexed_paths):
            print("Some paths are excluded: ", minus(self.indexed_paths, valid_paths))

        for path in valid_paths:
            for root, dirs, files in os.walk(path):
                for filename in files:
                    full_path = os.path.abspath(os.path.join(root, filename))
                    if len([x for x in self.exts if filename.lower().endswith(x)]) == 0 and len([x for x in excludes if filename.lower().endswith(x)]) == 0:
                        print (full_path)
                    
                                       
dups = None

def main():
    global dups
    dups = Dups(DB_PATH)

if __name__=="__main__":
        args = sys.argv

        if len(args) < 2:
            print("Usage: ", args[0], " index")
            print(args[0], "remove <path>\tRemoves path from indexed paths list")
            print(args[0], "add <path>\tAdds path to indexed paths list")
            print(args[0], "update\tRemoves deleted from disk files from index and adds new files")
            print(args[0], "reindex\tClears index and recomputes everything")
            print(args[0], "show\tShows duplicates")
            print(args[0], "dedup\tRemoves duplicates. Asks which one to delete first")
            print(args[0], "add_ext\tAdds extension to list of indexable file extensions")
            print(args[0], "del_ext\tRemoves extension from list of indexable file extensions")
            print(args[0], "show_all\tShows all config settings")
            print(args[0], "show_other\tShows files that have non-indexable extensions")
            print("\nOptions:")
            print("-db <dbfile>\t Doesn't work (yet)")
            sys.exit(-1)

        main()

        if args[1] == "add":
            if len(args) > 2:
                if os.path.isdir(args[2]):
                    dups.add_path(args[2])
                else:
                    print("Specified file is not directory")
            else:
                print("Usage: ", args[0], " add <path>")
        elif args[1] == "remove":
            if len(args) > 2:
                p = args[2]
                if p.startswith("-"):
                    p = p[1:]
                    print(p)
                    dups.remove_path(p)
                    print("Deleted")
        elif args[1] == "index":
            dups.reindex()
        elif args[1] == "update":
            dups.update()
        elif args[1] == "show":
            # TODO: specify algorithm (hash-based, mtime/ctime)
            dups.show_duplicates()
        elif args[1] == "show_p":
                 dups.show_possible_duplicates()
        elif args[1] == "add_ext":
            if len(args) > 2:
                dups.add_ext(args[2])
        elif args[1] == "path":
            print(dups.indexed_paths)
        elif args[1] == "clear":
            dups.dedup()
        elif args[1] == "show_all":
            dups.show_all()
        elif args[1] == "show_other":
                excludes = []
                excludes = args[2:]
                dups.show_other(excludes)
        else:
            print("Invalid command")
            
        dups.save()
