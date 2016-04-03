from lxml import etree

# Parsing FWAP.XML
tree = etree.parse('file:///files/FWAP.xml')
# Select XML nodes via Xpath
# Example : Get IP Addresses of Integration VMs
r = tree.xpath('/FWAP/Environnement[@EP="I"]/RoleServeur/Cluster/MachineVirtuelle')
# Print retrieved tags
for result in r:
    # It's possible to make a subtree search with Xpath using the "./" notation
    serverName = result.get('SERVERNAME')
    vgDiskNodes = result.xpath('./proprietesroot_VM/vg_disque')
    vgNameNodes = result.xpath('./proprietesroot_VM/vg_nom')
    nomVgLvSoft = result.xpath("./proprietesroot_VM/LogicalVolume/lv_nom[text()='lv_soft']/../lv_vg")[0].text
    indiceVgLvSoft = result.xpath("./proprietesroot_VM/vg_nom[text()='{nomVg}']".format(nomVg=nomVgLvSoft))[0].get(
        'indice')
    for disk in vgDiskNodes:
        if disk.get('indice') == indiceVgLvSoft:
            print("%s : %s is on %s" % (serverName, 'lv_soft', disk.text))
