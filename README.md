# fwap
custom XML management for AGORA written in python

Le programme principal est interfaceGraphique.py.

Il nécessite d'avoir les librairies suivantes installées :

- lxml (Pour le support de xpath)
- pyvmomi >= 5.5.0 (Pour les bindings vsphere)

Et d'avoir cURL pour windows d'installé et dispo dans le PATH (j'ai pas eu le temps de le remplacer par un librairie python)
afin de gérer l'upload des OVF.
