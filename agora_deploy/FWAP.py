#!/usr/bin/env python
"""
Written by Benoit BARTHELEMY
Email: benoit.barthelemy2@open-groupe.com
Script pour requêter le FWAP.xml afin d'en extraire les informations des VM
"""
import pprint
from tkinter import *
from tkinter import ttk

from lxml import etree

import tools.autocombo

# Correspondance Image DVD/OS
os = {
    "rhel_5.3_DVD": "RHEL 5.3",
    "rhel_6.3_DVD": "RHEL 6.3",
    "ceos_6.5_DVD": "Centos 6.5",
}


class FwapFile(object):
    """
    Cette Classe permet de manipuler les fichers FWAP.xml d'Agora
    """

    def __init__(self, url):
        """

        :param url: URL du fichier FWAP à utiliser
        """
        self.url = url

    def parse(self, ep=None, rds=None, servername=None):
        """
        :param ep: Environnement produit
        :param rds: Role de serveur
        :param servername: Nom du serveur
        :return: Une liste de FWAP.Server
        Extraction des donnees du fichier FWAP
        """
        tree = etree.parse(self.url)

        xpath_string = '/FWAP/Environnement'
        if ep:
            xpath_string += '[@EP="{ep}"]'.format(ep=ep)
        xpath_string += "/RoleServeur"
        if rds:
            xpath_string += '[@RDS="{rds}"]'.format(rds=rds)
        xpath_string += "/Cluster/MachineVirtuelle"
        if servername:
            xpath_string += '[@SERVERNAME="{servername}"]'.format(servername=servername)

        result = []

        for fwap_entry in tree.xpath(xpath_string):
            result.append(Server(element=fwap_entry))
        return result

    def get_tk_tree(self, parent, type, name, label="FWAP.XML"):

        """
        Retourne une arborescence contenant les éléments du FWAP
        :param parent: Element auquel ratacher le TreeView
        :param label: Titre du treeView
        :param name: Nom du treeview
        :param type: Type d'élément à sélectionner (serveur|ep|rds)
        :return: treeView généré
        """
        tree = ttk.Treeview(parent, selectmode='browse', name=name)
        tree.column("#0", stretch=True)
        tree.heading('#0', text=label)
        xmltree = etree.parse(self.url)
        xpath_string = '/FWAP/Environnement'
        for ep_entry in xmltree.xpath(xpath_string):
            ep_id = tree.insert(parent='', index='end', text=ep_entry.get('EP'))
            if type != 'ep':

                # Tri des RDS
                rds_entries = ep_entry.xpath('./RoleServeur')
                data = []
                for elem in rds_entries:
                    key = elem.get('RDS')
                    data.append((key, elem))
                data.sort(key=lambda rds: rds[0])
                rds_entries[:] = [item[-1] for item in data]

                for rds_entry in rds_entries:
                    rds_id = tree.insert(parent=ep_id, index='end', text=rds_entry.get('RDS'))
                    if type != 'rds':
                        for server_entry in rds_entry.xpath('./Cluster/MachineVirtuelle'):
                            tree.insert(parent=rds_id, index='end', text=server_entry.get('SERVERNAME'))
        return tree

    def get_tk_combobox(self, parent, **kwargs):
        """
        Fournit une combobox des serveurs disponibles
        :param parent: Element auquel ratacher la combobox
        :return: combobox générée
        """
        combo = tools.autocombo.AutocompleteCombobox(parent, **kwargs)
        serverlist = self.get_serverlist()
        if not serverlist is None:
            combo.set_completion_list(serverlist)

        return combo

    def get_serverlist(self):
        """ Fournit la liste des serveurs correspondant à l'url de l'objet"""
        xpath_string = '/FWAP/Environnement/RoleServeur/Cluster/MachineVirtuelle/@SERVERNAME'
        xmltree = etree.parse(self.url)
        return sorted(xmltree.xpath(xpath_string))


class Server(object):
    """ Objet représentant un serveur et ses détails"""
    def __init__(self):
        return

    def __init__(self, element):
        """
        Constrution à partir d'un élément d'une extraction XML
        :type element: lxml.etree._Element
        """
        self.element = element
        self.servername = element.get('SERVERNAME')
        self.ip = element.xpath('./IPADDR')[0].text
        self.rds = element.xpath('../..')[0].get('RDS')
        self.ep = element.xpath('../../..')[0].get('EP')
        self.mtl = element.xpath('./MTL_HOST_REPO')[0].text
        # OS
        m = re.match('.*(?<=_DVD)', element.xpath('../../proprietesroot_RDS/REPO_LINUX')[0].text)
        if m:
            self.os = os.get(m.group(0))
        else:
            self.os = element.xpath('../../proprietesroot_RDS/REPO_LINUX')[0].text

        # Disques
        self.disks = {}
        diskNodes = element.xpath('./proprietesroot_VM/vg_disque')
        vgNodes = element.xpath('./proprietesroot_VM/vg_nom')

        self.disks = []

        for diskNode in diskNodes:
            total_disk_size = 0
            mem_times = 0
            lvs = []
            for vgNode in vgNodes:
                if diskNode.get('indice') == vgNode.get('indice'):
                    vgName = vgNode.text
                    lvNodes = element.xpath(
                        "./proprietesroot_VM/LogicalVolume/lv_vg[text()='{vgtext}']/..".format(vgtext=vgNode.text))
                    for lv in lvNodes:
                        newlv = LogicalVolume(name=lv.xpath("./lv_nom")[0].text, mount=lv.xpath('./lv_montage')[0].text,
                                              size=lv.xpath('./lv_taille')[0].text)
                        lvs.append(newlv)
                        if not newlv.size == "[MEM]":
                            # La taille nécessaire à la partition représente 105% de la taille de la partition en EXT3
                            total_disk_size += int(int(lv.xpath('./lv_taille')[0].text) * 105 / 100)
                        else:
                            mem_times += 1
            # TODO Rajouter gestion Javacore
            self.disks.append(
                ServerDisk(name=diskNode.text, vg=vgName, lvs=lvs, partsize=total_disk_size,
                           extra_mem_times_size=mem_times))
        return

    def print(self):
        """ Affichage des caractéristiques de l'objet """
        pprint.pprint(self.__dict__)


class ServerDisk(object):
    """ Objet représentant un disque de serveur """
    def __init__(self, name, vg, lvs, partsize, extra_mem_times_size):
        self.name = name
        self.vg = vg
        self.lvs = lvs
        self.partsize = partsize
        self.extra_mem_times_size = extra_mem_times_size
        return

    def __repr__(self):
        """ Affichage des détails d'un disque """
        return "%s : %s Mo (%s) volumes %s" % (self.name, self.partsize, self.vg, self.lvs)


class LogicalVolume(object):
    """ Objet représentant le VG présent sur un disque """
    def __init__(self, name, mount, size):
        self.name = name
        self.mount = mount
        self.size = size
        return

    def __repr__(self):
        """ Affichage des détails d'un VG """
        return "%s on %s (%s Mo)" % (self.name, self.mount, self.size)


def main():
    # Parsing FWAP.XML
    r = FwapFile("http://a82amtl02.agora.msanet/repo/agora/scripts/referentiel.xml").parse(servername="a82sxpm02")

    for result in r:
        result.print()


# Chargement de la fonction Main
if __name__ == "__main__":
    main()
