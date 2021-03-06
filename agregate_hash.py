# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 17:15:54 2020

@author: lione
"""

# =============================================================================
# Import

import argparse
import os
import logging
#import yaml
import datetime

from lxml import etree  # see https://python.doctor/page-xml-python-xpath
from xml.dom import minidom

# =============================================================================
# Initialisation du loggeur
loggingFormatString = '%(asctime)s:%(levelname)s:%(threadName)s:%(funcName)s:%(message)s'
logging.basicConfig(format=loggingFormatString, level=logging.DEBUG)

# Initialisation des valeurs par défaut
home = os.path.expanduser("~")
destdir_default = home
projectdir_default = os.getcwd()

usage_description = "Extraction de fichiers photo avec enrichissement pour comparaison"
usage_exec = r"python3 agregate_hash.py --filePath \"C:/Users/lione/Pictures_imagecomp.xml\""

# =============================================================================
# Gestionnaire d'arguments

parser = argparse.ArgumentParser(description=usage_description,
                                 epilog='Exemple de commande : ' + '\n' + usage_exec + '\n')

# TODO: ajouter la possibilité de mentionner un fichier ou un dossier
# TODO: ajouter la possibilité d'activer / désactiver le résursif
# TODO: ajouter un pointeur vers un fichier de config de l'outil https://docs.python.org/3/library/configparser.html
parser.add_argument('--filePath',
                    action='store',
                    default=projectdir_default,
                    help='Chemin du referentiel ImageComp à analyser (default: ' + projectdir_default + ')')

parser.add_argument('--destDir',
                    action='store',
                    default=destdir_default,
                    help='Chemin du dossier de destination des resultats (default: ' + destdir_default + ')')


args = parser.parse_args()


# =============================================================================
# Démarrage  du traitement

logging.info('INIT')


logging.debug('INIT:OPEN_FILE:args.filePath=%s', args.filePath)
tree = etree.parse(args.filePath)

hash_key_names = list()

# ADD METHOD
for hash_key in tree.xpath('//ImageHash'):
    logging.debug('BROWSE:ImageHash:hash_key=%s', hash_key)
    for children in hash_key:
        if children.tag not in hash_key_names:
            logging.debug('ADD_HASH_METHOD:method_name=%s', children.tag)
            hash_key_names.append(children.tag)
logging.debug('BROWSE:hash_key_names=%s', hash_key_names)

    
hashs_tree = etree.Element("Hashs")

for method in hash_key_names:
    logging.debug('PARSE:method=%s', method)
    method_tree = etree.Element(method)
    hash_values = list()
    for hash_key in tree.xpath('//ImageHash/{0}'.format(method)):
        if hash_key.text not in hash_values:
            logging.debug('PARSE:ADD_HASH_VALUE:method=%s:hash_key.text=%s', method, hash_key.text)
            hash_values.append(hash_key.text)
    for hash_value in hash_values:
        logging.debug('PARSE:FIND_HASH_VALUE:method=%s:hash_value=%s', method, hash_value)
        file_ref = tree.xpath("//File[ImageHash/{0} = '{1}']".format(method, hash_value))
        logging.debug('PARSE:FIND_HASH_VALUE_RESPONSE:method=%s:hash_value=%s:len(file_ref)=%s', method, hash_value, len(file_ref))
        
        hash_ref = etree.Element("HashRef", HashValue=hash_key.text, FileRefCount=str(len(file_ref)))

        for file in file_ref:
            logging.debug('PARSE:ADDFILE_REF:method=%s:hash_value=%s:len(file_ref)=%s', method, hash_value, len(file_ref))

            
            file_entry = etree.Element("FileRef", FilePath=file.findtext("FilePath"))
            hash_ref.append(file_entry)

        method_tree.append(hash_ref)

    logging.debug('BROWSE:method=%:method_tree=%s', method, etree.tostring(method_tree))
    hashs_tree.append(method_tree)



dest_full_path = os.path.join(args.destDir, 'agregate_hash.xml')
with open(dest_full_path, 'wb') as f:
    xml_str = etree.tostring(hashs_tree, pretty_print=True, xml_declaration=True, encoding="utf-8")
    f.write(xml_str)
logging.info('KGRAPH:%s:%s', 'STORED', dest_full_path)

# =============================================================================

logging.info('END')
# TODO: __main()__

