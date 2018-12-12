"""pyQt/pySide widgets and helper functions for mGear"""

#############################################
# GLOBAL
#############################################
import os
import traceback
import maya.OpenMayaUI as omui
import pymel.core as pm

from mgear.vendor.Qt import QtWidgets, QtCompat

UI_EXT = "ui"

#################
# Old qt importer
#################


def _qt_import(binding, shi=False, cui=False):
    QtGui = None
    QtCore = None
    QtWidgets = None
    wrapInstance = None

    if binding == "PySide2":
        from PySide2 import QtGui, QtCore, QtWidgets
        import shiboken2 as shiboken
        from shiboken2 import wrapInstance
        from pyside2uic import compileUi

    elif binding == "PySide":
        from PySide import QtGui, QtCore
        import PySide.QtGui as QtWidgets
        import shiboken
        from shiboken import wrapInstance
        from pysideuic import compileUi

    elif binding == "PyQt4":
        from PyQt4 import QtGui
        from PyQt4 import QtCore
        import PyQt4.QtGui as QtWidgets
        from sip import wrapinstance as wrapInstance
        from PyQt4.uic import compileUi
        print("Warning: 'shiboken' is not supported in 'PyQt4' Qt binding")
        shiboken = None

    else:
        raise Exception("Unsupported python Qt binding '%s'" % binding)

    rv = [QtGui, QtCore, QtWidgets, wrapInstance]
    if shi:
        rv.append(shiboken)
    if cui:
        rv.append(compileUi)
    return rv


def qt_import(shi=False, cui=False):
    """
    import pyside/pyQt

    Returns:
        multi: QtGui, QtCore, QtWidgets, wrapInstance

    """
    lookup = ["PySide2", "PySide", "PyQt4"]

    preferredBinding = os.environ.get("MGEAR_PYTHON_QT_BINDING", None)
    if preferredBinding is not None and preferredBinding in lookup:
        lookup.remove(preferredBinding)
        lookup.insert(0, preferredBinding)

    for binding in lookup:
        try:
            return _qt_import(binding, shi, cui)
        except Exception:
            pass

    raise _qt_import("ThisBindingSurelyDoesNotExist", False, False)


compileUi = qt_import(shi=True, cui=True)[-1]

#############################################
# helper Maya pyQt functions
#############################################


def ui2py(filePath=None, *args):
    """Convert qtDesigner .ui files to .py"""

    if not filePath:
        startDir = pm.workspace(q=True, rootDirectory=True)
        filePath = pm.fileDialog2(dialogStyle=2,
                                  fileMode=1,
                                  startingDirectory=startDir,
                                  fileFilter='PyQt Designer (*%s)' % UI_EXT,
                                  okc="Compile to .py")
        if not filePath:
            return False
        filePath = filePath[0]
    if not filePath:
        return False

    if not filePath.endswith(UI_EXT):
        filePath += UI_EXT
    compiledFilePath = filePath[:-2] + "py"
    pyfile = open(compiledFilePath, 'w')
    compileUi(filePath, pyfile, False, 4, False)
    pyfile.close()

    info = "PyQt Designer file compiled to .py in: "
    pm.displayInfo(info + compiledFilePath)


def maya_main_window():
    """Get Maya's main window

    Returns:
        QMainWindow: main window.

    """

    main_window_ptr = omui.MQtUtil.mainWindow()
    return QtCompat.wrapInstance(long(main_window_ptr), QtWidgets.QWidget)


def showDialog(dialog, dInst=True, dockable=False, *args):
    """
    Show the defined dialog window

    Attributes:
        dialog (QDialog): The window to show.

    """
    if dInst:
        try:
            for c in maya_main_window().children():
                if isinstance(c, dialog):
                    c.deleteLater()
        except Exception:
            pass

    # Create minimal dialog object

    # if versions.current() >= 20180000:
    #     windw = dialog(maya_main_window())
    # else:
    windw = dialog()

    # ensure clean workspace name
    if hasattr(windw, "toolName") and dockable:
        control = windw.toolName + "WorkspaceControl"
        if pm.workspaceControl(control, q=True, exists=True):
            pm.workspaceControl(control, e=True, close=True)
            pm.deleteUI(control, control=True)

    windw.move(QtWidgets.QApplication.desktop().screen().rect().center()
               - windw.rect().center())

    # Delete the UI if errors occur to avoid causing winEvent
    # and event errors (in Maya 2014)
    try:
        if dockable:
            windw.show(dockable=True)
        else:
            windw.show()
        return windw
    except Exception:
        windw.deleteLater()
        traceback.print_exc()


def deleteInstances(dialog, checkinstance):
    """Delete any instance of a given dialog

    Delete any instance of a given dialog and if the dialog is
    instance of checkinstance.

    Attributes:
        dialog (QDialog): The dialog to delete.
        checkinstance (QDialog): The instance to check the type of dialog.

    """
    mayaMainWindow = maya_main_window()
    for obj in mayaMainWindow.children():
        if isinstance(obj, checkinstance):
            if obj.widget().objectName() == dialog.toolName:
                print 'Deleting instance {0}'.format(obj)
                mayaMainWindow.removeDockWidget(obj)
                obj.setParent(None)
                obj.deleteLater()


def fakeTranslate(*args):
    """Fake Translation

    fake QApplication.translate. This function helps to bypass the
    incompativility for the Unicode utf8  deprecated in pyside2

    """
    return args[1]
