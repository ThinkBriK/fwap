from lxml import etree

# Parsing FWAP.XML
tree = etree.parse('file:///D:/BBA/Projets/FWAP/FWAP.xml')
# Select XML nodes via Xpath
# Example : Get IP Addresses of Integration VMs
r = tree.xpath('/FWAP/Environnement[@EP="I"]/RoleServeur/Cluster/MachineVirtuelle')
# Print retrieved tags
for result in r:
    # It's possible to make a subtree search with Xpath using the "./" notation
    # print(result.get('SERVERNAME')+ "(" + result.xpath('./IPADDR')[0].text+")")
    print("%s - %s" % (result.get('SERVERNAME'), result.xpath('./IPADDR')[0].text))
