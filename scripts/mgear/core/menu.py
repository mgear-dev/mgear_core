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
        ("Import Skin", partial(skin.importSkin, None)),
        ("Import Skin Pack", partial(skin.importSkinPack, None)),
        ("-----", None),
        ("Export Skin", partial(skin.exportSkin, None, None)),
        ("Export Skin Pack Binary", partial(skin.exportSkinPack, None, None)),
        ("Export Skin Pack ASCII", partial(skin.exportJsonSkinPack,
                                           None,
                                           None)),
        ("-----", None),
        ("Get Names in gSkin File", partial(skin.getObjsFromSkinFile, None))
    )

    mgear.menu.install("Skinning", commands)


def install_utils_menu(m):
    """Install core utils submenu
    """
    pm.setParent(m, menu=True)
    pm.menuItem(divider=True)
    pm.menuItem(label="Compile PyQt ui", command=pyqt.ui2py)
