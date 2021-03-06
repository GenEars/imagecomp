# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 12:25:27 2020

@author: lione

"""

# https://pypi.org/project/ImageHash/
# https://pypi.org/project/exif/

# =============================================================================
# Import

import argparse
import os
import glob  # https://docs.python.org/3/library/glob.html
import logging
#import yaml
import datetime
import re

import multiprocessing as mp # cf. https://docs.python.org/2/library/multiprocessing.html

import xml.etree.ElementTree as ET
from xml.dom import minidom

# PIL: see https://pillow.readthedocs.io/en/3.1.x/reference/Image.html
from PIL import Image  # See Based on PIL/Pillow Image, numpy and scipy.fftpack (for pHash) Easy installation through pypi.
import imagehash

from exif import Image as ExifImage

# =============================================================================
# Initialisation du loggeur
loggingFormatString = '%(asctime)s:%(levelname)s:%(threadName)s:%(funcName)s:%(message)s'
logging.basicConfig(format=loggingFormatString, level=logging.DEBUG)

# Initialisation des valeurs par défaut
home = os.path.expanduser("~")
destdir_default = home
projectdir_default = os.getcwd()

dir_list_default = ['']

usage_description = "Extraction de fichiers photo avec enrichissement pour comparaison"
usage_exec = r"python3 imagecomp.py --projectDir \"C:/Users/lione/Pictures/Video Projects\""

# =============================================================================
# Gestionnaire d'arguments

parser = argparse.ArgumentParser(description=usage_description,
                                 epilog='Exemple de commande : ' + '\n' + usage_exec + '\n')

# TODO: ajouter la possibilité de mentionner un fichier ou un dossier
# TODO: ajouter la possibilité d'activer / désactiver le résursif
# TODO: ajouter un pointeur vers un fichier de config de l'outil https://docs.python.org/3/library/configparser.html
parser.add_argument('--projectDir',
                    action='store',
                    default=projectdir_default,
                    help='Chemin du dossier contenant le projet à analyser (default: ' + projectdir_default + ')')

parser.add_argument('--destDir',
                    action='store',
                    default=destdir_default,
                    help='Chemin du dossier de destination des resultats (default: ' + destdir_default + ')')


parser.add_argument('--computeHash',
                    action='store',
                    default=True,
                    type=bool,
                    choices=[True, False],
                    help='Active/desactive le calcul du hash (default: True)')

parser.add_argument('--getExif',
                    action='store',
                    default=True,
                    type=bool,
                    choices=[True, False],
                    help='Active/desactive la collecte des donnees EXIF (default: True)')

args = parser.parse_args()


# =============================================================================
# Démarrage  du traitement

logging.info('INIT')

# TODO: allow user to specify project name
project_name = os.path.basename(args.projectDir)
logging.debug('INIT:VARS:project_name=%s', project_name)

# =============================================================================

hash_method_list = ['ahash', 'phash', 'dhash', 'whash-haar', 'whash-db4']

def compute_hash(img, hash_method='ahash'):
    
    if hash_method == 'ahash':
        hashfunc = imagehash.average_hash
    elif hash_method == 'phash':
        hashfunc = imagehash.phash
    elif hash_method == 'dhash':
        hashfunc = imagehash.dhash
    elif hash_method == 'whash-haar':
        hashfunc = imagehash.whash
    elif hash_method == 'whash-db4':
        hashfunc = lambda img: imagehash.whash(img, mode='db4')
    else:
        raise('No hashfunc found')

    hash = hashfunc(Image.open(img))
    
    return hash
    
# =============================================================================

def get_exif(img):
    with open(img, 'rb') as image_file:
        my_image = ExifImage(image_file)
        
    kg_imageexif = ET.Element('EXIF')

    # Détection de la présence d'Exif
    logging.debug('BROWSE:EXIF:file=%s:hasExif=%s', file, my_image.has_exif)
    kg_imageexif_hasExif = ET.Element('hasExif')
    kg_imageexif_hasExif.text = str(my_image.has_exif)    
    kg_imageexif.append(kg_imageexif_hasExif)
    
    # Traitement des attributs Exif
    if my_image.has_exif:
        image_attributes = dir(my_image)
        for image_attribute in image_attributes:
            try:
                if my_image.get(image_attribute) is not None:
                    logging.debug('BROWSE:EXIF:file=%s:image_attribute=%s', file, image_attribute)
                    kg_imageexif_element = ET.Element(re.sub("[<>\s]", "_", image_attribute))
                    kg_imageexif_element.text = str(my_image.get(image_attribute))    
                    kg_imageexif.append(kg_imageexif_element)
            except Exception as exif_e:
                logging.warning('BROWSE:EXIF:file=%s:err=%s', file, str(exif_e))
    
    return kg_imageexif


def worker():
    # Préparation de métadonnées concernant le fichier traité
    head, filename = os.path.split(file)
    relative_dir = os.path.basename(head)
    file_ext = os.path.splitext(file)[1]
    file_uri = '{0}/{1}/{2}'.format(files_base_uri, relative_dir, filename)
    logging.debug('BROWSE:PARSE:relative_dir=%s:keys=%s:file_uri=%s', relative_dir, filename, file_uri)

    # Sous-éléments spécifiques au fichier référençant les variables
    kg_file = ET.Element('File')
    kg_file.set('URI', file_uri)

    kg_file_name = ET.Element('FileName')
    kg_file_name.text = filename

    kg_file_extension = ET.Element('FileExtension')
    kg_file_extension.text = file_ext

    kg_file_path = ET.Element('FilePath')
    kg_file_path.text = file

    kg_file.append(kg_file_name)
    kg_file.append(kg_file_extension)
    kg_file.append(kg_file_path)

    # Sous-éléments spécifiques au phashHash
    if args.computeHash:

        kg_imagehash = ET.Element('ImageHash')

        for hashm in hash_method_list:
            hash = compute_hash(file, hashm)
            kg_imagehash_hash = ET.Element(hashm)
            kg_imagehash_hash.text = str(hash)
            kg_imagehash.append(kg_imagehash_hash)

        kg_file.append(kg_imagehash)

    # Sous-éléments spécifiques à EXIF

    if args.getExif:
        kg_file.append(get_exif(file))

    # Ajout de l'élément File à la structure Files
    kg_files.append(kg_file)
    logging.info('BROWSE:PARSE:ADD_NODE:FILE:file_uri=%s', file_uri)


# =============================================================================
# Basic Knowledge Graph
logging.info('INIT:CREATE_BASIC_KG')

# Création de la structure Project
kg_project = ET.Element('Project')

kg_project_name = ET.SubElement(kg_project, 'ProjectName')
kg_project_name.text = project_name
kg_project_path = ET.SubElement(kg_project, 'ProjectPath')
kg_project_path.text = args.projectDir
kg_project_crawldate = ET.SubElement(kg_project, 'CrawlDate')
kg_project_crawldate.text = datetime.datetime.utcnow().isoformat()



# Création de la structure
kg_files = ET.Element('Files')

# Préparation de valeurs communes
files_base_uri = '{0}/files'.format(project_name)

# =============================================================================
# List interresting files
logging.info('INIT:GLOB:START')

# TODO: check if dir exist
# TODO: read dir_list from config file
# TODO: enable other file types
dir_list = dir_list_default
logging.info('INIT:GLOB:dir_list=%s', dir_list)
file_list = list()
# TODO: add file ext argument in CLI
file_exts = ['jpeg', 'jpg', 'png', 'bmp', 'gif']
for dir_current in dir_list:
    for file_ext in file_exts:
        path_to_browse = os.path.join(args.projectDir, dir_current, '**', '*.%s' % file_ext)
        files_in_path_to_browse = glob.glob(path_to_browse, recursive=True)
        logging.debug('INIT:GLOB:path_to_browse=%s:files_in_path_to_browse=%s', path_to_browse, files_in_path_to_browse)
        file_list.extend(files_in_path_to_browse)
logging.info('INIT:GLOB:file_list=%s', file_list)




# =============================================================================

# Preparation du multithread
pool = mp.Pool(mp.cpu_count()) # HACK pool = mp.Pool(os.cpu_count())
logging.info('INIT:MPROC:mp.cpu_count:%s', mp.cpu_count()) # HACK
proc_results = []

# =============================================================================
# Load files and get caracteristics
for file in file_list:
    # TODO: go multiproc
    logging.info('BROWSE:OPEN:file=%s', file)
    try:        
        proc = pool.apply_async(worker, args = [file])
        proc_results.append(proc)

    except Exception as e:
        logging.error('BROWSE:PARSE:file=%s:err=%s', file, str(e))

# close and wait for pool to finish
logging.info('BROWSE:MPROC:WAITING_FOR_POOL')
pool.close()
pool.join()

# Parcours des resultats du pool
procReturnDict = {}
for proc in proc_results:
    procReturn_result = proc.get()
    procReturnDict.update(procReturn_result)
    logging.info('procReturn_result:%s', procReturn_result)
logging.debug('procReturnDict:%s', procReturnDict)

# =============================================================================
# Ajout des sous-structures à l'arbre
kg_root = ET.Element('ImageComp')
kg_root.extend((kg_project, kg_files))
kg_tree = ET.ElementTree(kg_root)

# Préparation de la sauvegarde
resultKGraphFileName = '{0}_imagecomp.xml'.format(project_name)
dest_full_path = os.path.join(args.destDir, resultKGraphFileName)

# Sauvegarde
xmlstr = minidom.parseString(ET.tostring(kg_root)).toprettyxml(indent="   ")
with open(dest_full_path, "wb") as f:
    f.write(xmlstr.encode('utf-8'))

logging.info('KGRAPH:%s:%s', 'STORED', dest_full_path)



# =============================================================================

logging.info('END')
# TODO: __main()__

