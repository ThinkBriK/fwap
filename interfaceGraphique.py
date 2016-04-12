import sys
import tkinter as Tk
from tkinter import ttk

import pyVmomi

import FWAP
import OVF


########################################################################
class MyApp(object):
    """"""

    # ----------------------------------------------------------------------
    def __init__(self, parent, fwapfile):
        """Constructor"""
        self.root = parent
        self.root.title("Déploiement TAT1")
        self.frame = Tk.Frame(parent)
        self.frame.grid()
        self.fwapfile = FWAP.FwapFile(fwapfile)
        self._create_widgets()

    def _create_widgets(self):
        # create the notebook
        nb = ttk.Notebook(self.frame, name='notebook')

        # extend bindings to top level window allowing
        #   CTRL+TAB - cycles thru tabs
        #   SHIFT+CTRL+TAB - previous tab
        #   ALT+K - select tab using mnemonic (K = underlined letter)
        nb.enable_traversal()
        nb.grid(row=0, column=0, padx=2, pady=3)

        handler = lambda: "Lancement du déploiement"
        btn = ttk.Button(self.frame, text="Lancer le déploiement", command=handler, state="disabled", name='deploy')
        btn.grid(row=1, column=0, sticky='N')

        self._create_fwap_tab(nb)
        self._create_vcenter_tab(nb)
        self._create_request_tab(nb)
        self._create_vi_tab(nb)


    # ----------------------------------------------------------------------
    def onFwapSelect(self, tree):
        choix = tree.focus()

        # On vérifie qu'on soit bien sur un serveur (feuille)
        if len(tree.get_children(choix)) == 0:
            self.name = tree.item(choix)['text']

            rds = tree.parent(choix)
            self.rds = tree.item(rds)['text']

            ep = tree.parent(rds)
            self.ep = tree.item(ep)['text']

            self.validate()


    def _create_fwap_tab(self, notebook):
        frame = ttk.Frame(notebook, name='fwap')
        tree = self.fwapfile.get_tk_tree(parent=frame, label="Choisissez un serveur", type='serveur')
        # tree.bind('<<TreeviewSelect>>', self.fwap_select)
        tree.grid(row=0, column=0)

        handler = lambda: self.onFwapSelect(tree)
        boutonOK = Tk.Button(frame, text="OK", command=handler)
        boutonOK.grid(row=0, column=1, sticky='SE')

        # add to notebook (underline = index for short-cut character)
        notebook.add(frame, text='FWAP', padding=2)

    def onChooseDeployServer(self, tree):
        choix = tree.focus()

        # On vérifie qu'on soit bien sur un serveur (feuille)
        if len(tree.get_children(choix)) == 0:
            self.esx = tree.item(choix)['text']
            self.validate()
    # ----------------------------------------------------------------------
    def onSetViCredentials(self, vcenter, usr, passwd, notebook):
        try:
            si = OVF.connect_vcenter(vcenter=vcenter.get(), user=usr.get(), password=passwd.get())
        except:
            print(sys.exc_info()[0])
            notebook.tab('current', text='Connexion vCenter (erreur)')
            notebook.tab(3, state="disabled")
            return
        self.onUpdateParams(
            params_dict={'vcenter': vcenter.get(), 'password': passwd.get(), 'user': usr.get(), 'si': si})
        notebook.tab('current', text='Connexion vCenter (OK)')
        notebook.tab(3, state="normal")
        frame = notebook.children['vi']
        tree = ttk.Treeview(frame, selectmode='browse')
        content = si.RetrieveContent()
        # TODO Remplacer l'alimentation de l'arbre vmware par une fonction récursive
        # Datacenters
        for datacenter_element in content.rootFolder.childEntity:
            if type(datacenter_element) == pyVmomi.types.vim.Datacenter:
                dc_id = tree.insert(parent='', index='end', text=datacenter_element.name)
                # Clusters
                for host_element in datacenter_element.hostFolder.childEntity:
                    if type(host_element) == pyVmomi.types.vim.ComputeResource:
                        host_id = tree.insert(parent=dc_id, index='end', text=host_element.name)
                    elif type(host_element) == pyVmomi.types.vim.ClusterComputeResource:
                        cluster_id = tree.insert(parent=dc_id, index='end', text=host_element.name)
                        for cluster_member in host_element.host:
                            host_id = tree.insert(parent=cluster_id, index='end', text=cluster_member.name)
                    elif type(host_element) == pyVmomi.types.vim.Folder:
                        folder_id = tree.insert(parent=dc_id, index='end', text=host_element.name)
                        for folder_member in host_element.childEntity:
                            if type(folder_member) == pyVmomi.types.vim.ComputeResource:
                                host_id = tree.insert(parent=folder_id, index='end', text=folder_member.name)
                            elif type(folder_member) == pyVmomi.types.vim.ClusterComputeResource:
                                cluster_id = tree.insert(parent=folder_id, index='end', text=folder_member.name)
                                for cluster_member in folder_member.host:
                                    host_id = tree.insert(parent=cluster_id, index='end', text=cluster_member.name)
        tree.grid(row=0, column=0)
        handler = lambda: self.onChooseDeployServer(tree)
        btn = Tk.Button(frame, text="OK", command=handler)
        btn.grid(row=0, column=1, sticky='W')

    def _create_vcenter_tab(self, notebook):
        """"""
        frame = ttk.Frame(notebook, name='vcenter')
        label_vcenter = Tk.Label(frame, text="vCenter")
        label_vcenter.grid(row=0, column=0, sticky='W')
        vcenter = ttk.Combobox(frame, values=("a82avce02.agora.msanet", "a82avce96.agora.msanet"), width=25)
        vcenter.set("a82avce02.agora.msanet")
        vcenter.grid(row=0, column=1, sticky='W')

        label_usr = Tk.Label(frame, text="User vCenter")
        label_usr.grid(row=1, column=0, sticky='W')
        usr = Tk.Entry(frame, width=25)
        usr.grid(row=1, column=1, sticky='W')

        label_pwd = Tk.Label(frame, text="Password vCenter")
        label_pwd.grid(row=2, column=0, sticky='W')
        passwd = Tk.Entry(frame, show="*", width=25)
        passwd.grid(row=2, column=1, sticky='W')

        handler = lambda: self.onSetViCredentials(vcenter, usr, passwd, notebook)
        btn = Tk.Button(frame, text="OK", command=handler)
        btn.grid(row=3, column=1, sticky='W')

        notebook.add(frame, text='Connexion vCenter (déconnecté)', padding=2)

        # ----------------------------------------------------------------------

    # ----------------------------------------------------------------------
    def _create_request_tab(self, notebook):
        # demandeur, fonction, eol

        frame = ttk.Frame(notebook, name='request')
        handler = lambda: self.onUpdateParams(
            params_dict={'demandeur': demandeur.get(), 'fonction': fonction.get(), 'eol': eol.get(),
                         'vcpus': vcpus.get(), 'ram': ram.get()})

        label_demandeur = Tk.Label(frame, text="Demandeur")
        label_demandeur.grid(row=0, column=0, sticky='W')
        demandeur = Tk.Entry(frame, width=30)
        demandeur.grid(row=0, column=1, sticky='W')

        label_fonction = Tk.Label(frame, text="Fonction")
        label_fonction.grid(row=1, column=0, sticky='W')
        fonction = Tk.Entry(frame, width=30)
        fonction.grid(row=1, column=1, sticky='W')

        label_eol = Tk.Label(frame, text="Fin de vie")
        label_eol.grid(row=2, column=0, sticky='W')
        eol = Tk.Entry(frame, width=30)
        eol.value = "Perenne"
        eol.grid(row=2, column=1, sticky='W')

        sep = ttk.Separator(orient='horizontal')
        sep.grid(row=3, column=0, sticky='W')

        label_vcpu = Tk.Label(frame, text="Entrez le nombre de vCPUs")
        label_vcpu.grid(row=4, column=0, sticky='W')
        vcpus = Tk.Spinbox(frame, from_=1, to=12)
        vcpus.value = 1
        vcpus.grid(row=4, column=1, sticky='W')

        label_ram = Tk.Label(frame, text="RAM en GB")
        label_ram.grid(row=5, column=0, sticky='W')
        ram = Tk.Spinbox(frame, from_=1, to=64)
        ram.value = 1
        ram.grid(row=5, column=1, sticky='W')

        btn = Tk.Button(frame, text="OK", command=handler)
        btn.grid(row=6, column=1, sticky='W')

        notebook.add(frame, text='Demande', padding=2)

    # ----------------------------------------------------------------------
    def _create_vi_tab(self, notebook):
        # TODO Rajouter esx et en fonction lan, datacenter, datastore, cluster, esx, vmfolder,
        frame = ttk.Frame(notebook, name='vi')
        notebook.add(frame, text='Infrastructure vmWare', padding=2, state='disabled')
    # ----------------------------------------------------------------------
    def onUpdateParams(self, params_dict):
        """"""
        for key in params_dict.keys():
            setattr(self, key, params_dict[key])

        self.validate()

    def __repr__(self):
        representation = ''
        for key in self.__dict__.keys():
            if key != 'password':
                representation += key + " : " + str(self.__dict__[key]) + "\n"
            else:
                representation += key + ": ********\n"
        return representation

    def validate(self):
        print(self)
        # ovfpath, name, vcpu, ram, lan, datacenter, datastore,cluster, esx, vmfolder, ep, rds, demandeur, fonction, eol
        # required_args=['name', 'vcpu', 'ram', 'lan', 'datacenter', 'datastore','cluster', 'esx', 'vmfolder', 'ep', 'rds', 'demandeur', 'fonction', 'eol']
        required_args = ['name', 'vcpus', 'ram', 'esx', 'ep', 'rds', 'demandeur', 'fonction', 'eol']
        ready = True
        for arg in required_args:
            if not hasattr(self, arg):
                ready = False
        if ready:
            self.frame.children['deploy'].config(state='normal')


# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = Tk.Tk()
    root.geometry()
    app = MyApp(root, 'files/FWAP.xml')
    root.mainloop()

    # TODO Passer ovfpath en params
