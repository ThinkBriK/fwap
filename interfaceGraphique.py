import tkinter as Tk

import FWAP


########################################################################
class OtherFrame(Tk.Toplevel):
    """"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        Tk.Toplevel.__init__(self)
        self.geometry("400x300")
        self.title("otherFrame")


########################################################################
class MyApp(object):
    """"""

    # ----------------------------------------------------------------------
    def __init__(self, parent, fwapfile):
        """Constructor"""
        self.root = parent
        self.root.title("Déploiement TAT1")
        self.frame = Tk.Frame(parent)
        self.frame.pack()
        self.fwapfile = FWAP.FwapFile(fwapfile)
        self.display_xml_window()

    # ----------------------------------------------------------------------
    def hide(self):
        """"""
        self.root.withdraw()

    # ----------------------------------------------------------------------
    def openFrame(self):
        """"""
        self.hide()
        subFrame = OtherFrame()
        handler = lambda: self.onCloseOtherFrame(subFrame)
        btn = Tk.Button(subFrame, text="Close", command=handler)
        btn.pack()

    # ----------------------------------------------------------------------
    def onCloseOtherFrame(self, otherFrame):
        """"""
        otherFrame.destroy()
        self.show()

    # ----------------------------------------------------------------------
    def show(self):
        """"""
        self.root.update()
        self.root.deiconify()

    # ----------------------------------------------------------------------
    def display_xml_window(self):
        fenetre = self.frame
        tree = self.fwapfile.get_tk_tree(fenetre, label="Choisissez un serveur", type='serveur')
        tree.pack()

        # bouton de sortie
        boutonFermer = Tk.Button(fenetre, text="Fermer", command=fenetre.quit)
        boutonFermer.pack(side='left')
        boutonOK = Tk.Button(fenetre, text="OK", command=fenetre.quit)
        boutonOK.pack(side='right')
        fenetre.mainloop()
        choix = tree.focus()

        # TODO Manquent vcenter, user, password, vcpu, ram, lan, datacenter, datastore, cluster, esx, vmfolder, demandeur, fonction, eol,
        # TODO passer ovfpath en conf


        servername = tree.item(choix)['text']
        print("servername = " + servername)

        rds = tree.parent(choix)
        print("RDS = " + tree.item(rds)['text'])

        ep = tree.parent(rds)
        print("EP = " + tree.item(ep)['text'])


# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = Tk.Tk()
    root.geometry()
    app = MyApp(root, 'files/FWAP.xml')
    root.mainloop()
