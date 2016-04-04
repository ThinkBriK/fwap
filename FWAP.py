#!/usr/bin/env python
"""
Written by Benoit BARTHELEMY
Email: benoit.barthelemy2@open-groupe.com
Script pour requêter le FWAP.xml afin d'en extraire les informations des VM
"""
import pprint
import re

from lxml import etree

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

    def __init__(self, file):
        """

        :param file: Chemin du fichier FWAP à utiliser
        """
        self.file = file

    def parse(self, ep=None, rds=None, servername=None):
        """
        :param ep: Environnement produit
        :param rds: Role de serveur
        :param servername: Nom du serveur
        :return: Une liste de FWAP.Server
        Extraction des donnees du fichier FWAP
        """
        tree = etree.parse("file:///" + self.file)

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


class Server(object):
    def __init__(self):
        return

    def __init__(self, element):
        """

        :type element: lxml.etree._Element
        """
        self.element = element
        self.servername = element.get('SERVERNAME')
        self.ip = element.xpath('./IPADDR')[0].text
        self.rds = element.xpath('../..')[0].get('RDS')
        self.ep = element.xpath('../../..')[0].get('EP')
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
                            total_disk_size += int(lv.xpath('./lv_taille')[0].text)
                        else:
                            mem_times += 1
        self.disks.append(
            ServerDisk(name=diskNode.text, vg=vgName, lvs=lvs, rawsize=total_disk_size, extra_mem_times_size=mem_times))
        return

    def print(self):
        pprint.pprint(self.__dict__)


class ServerDisk(object):
    def __init__(self, name, vg, lvs, rawsize, extra_mem_times_size):
        self.name = name
        self.vg = vg
        self.lvs = lvs
        self.rawsize = rawsize
        self.extra_mem_times_size = extra_mem_times_size
        return

    def __repr__(self):
        return "%s : %s Ko (%s) volumes %s" % (self.name, self.rawsize, self.vg, self.lvs)


class LogicalVolume(object):
    def __init__(self, name, mount, size):
        self.name = name
        self.mount = mount
        self.size = size
        return

    def __repr__(self):
        return "%s on %s (%s Ko)" % (self.name, self.mount, self.size)


def main():
    # Parsing FWAP.XML
    r = FwapFile("files/FWAP.xml").parse(servername="a82bic202")

    for result in r:
        result.print()


# Chargement de la fonction Main
if __name__ == "__main__":
    main()
