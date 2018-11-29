from functools import partial
import mgear
import mgear.menu
from mgear.core import skin, pyqt
import pymel.core as pm


def install_skinning_menu():
    """Install Skinning submenu
    """
    commands = (
        ("Copy Skin", partial(skin.skinCopy, None, None)),
        ("Select Skin Deformers", skin.selectDeformers),
        ("-----", None),
        ("Import Skin", skin.importSkin),
        ("Import Skin Pack", skin.importSkinPack),
        ("-----", None),
        ("Export Skin", skin.exportSkin),
        ("Export Skin Pack", skin.exportSkinPack),
        ("-----", None),
        ("Get Names in gSkin File", skin.getObjsFromSkinFile)
    )

    mgear.menu.install("Skinning", commands)


def install_utils_menu(m):
    """Install core utils submenu
    """
    pm.setParent(m, menu=True)
    pm.menuItem(divider=True)
    pm.menuItem(label="Compile PyQt ui", command=pyqt.ui2py)
