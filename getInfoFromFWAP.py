#!/usr/bin/env python
"""
Written by Benoit BARTHELEMY
Email: benoit.barthelemy2@open-groupe.com
Script pour requêter le FWAP.xml afin d'en extraire les informations d'une VM
"""
import pprint
import re

from lxml import etree


def main(fwap_file="files/FWAP.xml", ep="", rds="", servername=""):
    # Parsing FWAP.XML
    tree = etree.parse("file:///" + fwap_file)

    xpath_string = '/FWAP/Environnement'
    if ep:
        xpath_string += "[@EP={ep}]".format(ep=ep)
    xpath_string += "/RoleServeur"
    if rds:
        xpath_string += "[@RDS={rds}]".format(rds=rds)
    xpath_string += "/Cluster/MachineVirtuelle"
    if servername:
        xpath_string += "[@SERVERNAME={servername}]".format(servername=servername)
    r = tree.xpath(xpath_string)

    # Correspondance Image DVD/OS
    os = {
        "rhel_5.3_DVD": "RHEL 5.3",
        "rhel_6.3_DVD": "RHEL 6.3",
        "ceos_6.5_DVD": "Centos 6.5",
    }

    serveurs = {}
    for result in r:
        # It's possible to make a subtree search with Xpath using the "./" notation
        # print(result.get('SERVERNAME')+ "(" + result.xpath('./IPADDR')[0].text+")")
        serveurs[result.get('SERVERNAME')] = {}
        # IP
        serveurs[result.get('SERVERNAME')]['IP'] = result.xpath('./IPADDR')[0].text
        # RDS
        serveurs[result.get('SERVERNAME')]['RDS'] = result.xpath('../..')[0].get('RDS')
        # EP
        serveurs[result.get('SERVERNAME')]['EP'] = result.xpath('../../..')[0].get('EP')
        # OS
        m = re.match('.*(?<=_DVD)', result.xpath('../../proprietesroot_RDS/REPO_LINUX')[0].text)
        if m:
            serveurs[result.get('SERVERNAME')]['OS'] = os.get(m.group(0))
        else:
            serveurs[result.get('SERVERNAME')]['OS'] = result.xpath('../../proprietesroot_RDS/REPO_LINUX')[0].text

        # Disques
        serveurs[result.get('SERVERNAME')]['DISKS'] = {}
        diskNodes = result.xpath('./proprietesroot_VM/vg_disque')
        vgNodes = result.xpath('./proprietesroot_VM/vg_nom')

        for disk in diskNodes:
            total_disk_size = 0
            mem_times = 0
            serveurs[result.get('SERVERNAME')]['DISKS'][disk.text] = {}
            for vg in vgNodes:
                if disk.get('indice') == vg.get('indice'):
                    serveurs[result.get('SERVERNAME')]['DISKS'][disk.text]['VG'] = vg.text
                    serveurs[result.get('SERVERNAME')]['DISKS'][disk.text]['LV'] = {}
                    lvNodes = result.xpath(
                        "./proprietesroot_VM/LogicalVolume/lv_vg[text()='{vgtext}']/..".format(vgtext=vg.text))
                    for lv in lvNodes:
                        serveurs[result.get('SERVERNAME')]['DISKS'][disk.text]['LV'][lv.xpath("./lv_nom")[0].text] = {}
                        serveurs[result.get('SERVERNAME')]['DISKS'][disk.text]['LV'][lv.xpath("./lv_nom")[0].text][
                            'montage'] = lv.xpath('./lv_montage')[0].text
                        serveurs[result.get('SERVERNAME')]['DISKS'][disk.text]['LV'][lv.xpath("./lv_nom")[0].text][
                            'taille'] = lv.xpath('./lv_taille')[0].text
                        if not lv.xpath('./lv_taille')[0].text == "[MEM]":
                            total_disk_size += int(lv.xpath('./lv_taille')[0].text)
                        else:
                            mem_times += 1
            if mem_times == 0:
                serveurs[result.get('SERVERNAME')]['DISKS'][disk.text]['taille'] = total_disk_size
            else:
                serveurs[result.get('SERVERNAME')]['DISKS'][disk.text]['taille'] = "%d + MEM x %d" % (
                    total_disk_size, mem_times)

    pprint.pprint(serveurs, width=20)


# Chargement de l'objet Main
if __name__ == "__main__":
    main()
