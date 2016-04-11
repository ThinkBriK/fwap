#!/usr/bin/env python
"""
 Ecrit par Benoit BARTHELEMY
 benoit.barthelemy2@open-groupe.com

 Script permettant de tester l'interface graphique
"""
from tkinter import *

from FWAP import FwapFile

fenetre = Tk()

# vmDeploy(ovfpath, name, vcpu, ram, lan, datacenter, datastore, cluster, esx, vmfolder, ep, rds, demandeur, fonction, eol)
# deployment.connect_vcenter(vcenter=args.vcenter, user=args.user, password=args.password)

label = Label(fenetre, text="Hello World")
label.pack()
# # liste
# liste = Listbox(fenetre)
# liste.insert(1, "Python")
# liste.insert(2, "PHP")
# liste.insert(3, "jQuery")
# liste.insert(4, "CSS")
# liste.insert(5, "Javascript")
#
# liste.pack()
#
# countryvar = "country"
# countries= ("France","Allemagne", "Pays-Bas")
# country = ttk.Combobox(fenetre, values=countries, textvariable=countryvar)
#
# country.pack()
#
# tree = ttk.Treeview(fenetre)
#
# # Inserted at the root, program chooses id:
# tree.insert('', 'end', 'widgets', text='Widget Tour')
#
# # Same thing, but inserted as first child:
# tree.insert('', 0, 'gallery', text='Applications')
#
# # Treeview chooses the id:
# id = tree.insert('', 'end', text='Tutorial')
#
# # Inserted underneath an existing node:
# tree.insert('widgets', 'end', text='Canvas')
# tree.insert(id, 'end', text='Tree')

myFwap = FwapFile("files\FWAP.xml")
tree = myFwap.get_tk_tree(fenetre)
tree.pack()

# bouton de sortie
bouton = Button(fenetre, text="Fermer", command=fenetre.quit)
bouton.pack()

fenetre.mainloop()
