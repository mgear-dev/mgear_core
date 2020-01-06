
"""
dagmenu mGear module contains all the logic to override Maya's right
click dag menu.
"""

# imports
from __future__ import absolute_import
from functools import partial
from maya import cmds, mel
import mgear


def get_option_var_state():
    """ Gets dag menu option variable

    Maya's optionVar command installs a variable that is kept on Maya's
    settings so that you can use it on future sessions.

    Maya's optionVar are a quick and simple way to store a custom variable on
    Maya's settings but beware that they are kept even after mGear's uninstall
    so you will need to run the following commands.

    Returns:
        bool: Whether or not mGear's dag menu override is used

    Example:
        The following removes mgears dag menu optionVar

        .. code-block:: python

           from maya import cmds

           if not cmds.optionVar(exists="mgear_dag_menu_OV"):
               cmds.optionVar(remove="mgear_dag_menu_OV")
    """

    # if there is no optionVar the create one that will live during maya
    # current and following sessions
    if not cmds.optionVar(exists="mgear_dag_menu_OV"):
        cmds.optionVar(intValue=("mgear_dag_menu_OV", 0))

    return cmds.optionVar(query="mgear_dag_menu_OV")


def install():
    """ Installs dag menu option
    """

    # get state
    state = get_option_var_state()

    cmds.setParent(mgear.menu_id, menu=True)
    cmds.menuItem("mgear_dagmenu_menuitem", label="mGear Viewport Menu ",
                  command=run, checkBox=state)
    cmds.menuItem(divider=True)

    run(state)


def mgear_dag_menu_callback(*args, **kwargs):  # @UnusedVariable
    """ Triggers dag menu display

    If selection is ends with **_ctl** then display mGear's contextual menu.
    Else display Maya's standard right click dag menu

    Args:
        *args: Parent Menu path name / Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        str: Menu object name/path that is passed to the function
    """

    # cast args into more descend variable name
    parent_menu = args[0]

    # if second argument if not a bool then means that we are running
    # the override
    if type(args[1]) != bool:
        sel = cmds.ls(selection=True, long=True, exactType="transform")
        if sel and sel[0].endswith("_ctl"):
            cmds.menu(parent_menu.replace('"', ''), edit=True,
                      deleteAllItems=True)
            cmds.menuItem(parent=parent_menu.replace('"', ''), label="test me")
        else:
            mel.eval("buildObjectMenuItemsNow " + parent_menu)

    # always return parent menu path
    return parent_menu


def mgear_dagmenu_toggle(state):
    """Set on or off the mgear dag menu override

    This function is responsible for turning ON or OFF mgear's right click
    menu override. When turned on this will interact with dag nodes that
    have **_ctl** at the end of their name.

    Args:
        state (bool): Whether or not to override Maya's dag menu with mGear's
                      dag menu
    """

    # First loop on Maya menus as Maya's dag menu is a menu
    for maya_menu in cmds.lsUI(menus=True):

        # We now get the menu's post command which is a command used for
        # dag menu
        menu_cmd = cmds.menu(maya_menu, query=True, postMenuCommand=True) or []

        # If state is set top True then override Maya's dag menu
        if state and type(menu_cmd) != partial:
            if "buildObjectMenuItemsNow" in menu_cmd:
                # Maya's dag menu post command has the parent menu in it
                parent_menu = menu_cmd.split(" ")[-1]
                # Override dag menu with custom command call
                cmds.menu(maya_menu, edit=True, postMenuCommand=partial(
                          mgear_dag_menu_callback, parent_menu))

        # If state is set to False then put back Maya's dag menu
        # This is tricky because Maya's default menu command is a MEL call
        # The override part uses a python function partial call and because of
        # this we need to do some small hack on mGear_dag_menu_callback to give
        # back the default state of Maya's dag menu
        elif not state and type(menu_cmd) == partial:
            # we now check if the command override is one from us
            # here because we override original function we need
            # to get the function name by using partial.func
            if "mgear_dag_menu_callback" in menu_cmd.func.__name__:
                # we call the mGear_dag_menu_callback with the future state
                # this will return the original menu parent so that we
                # can put Maya's original dag menu command in mel
                parent_menu = menu_cmd(state)

                # we set the old mel command
                # don't edit any space or syntax here as this is what Maya
                # expects
                mel.eval('menu -edit -postMenuCommand '
                         '"buildObjectMenuItemsNow ' +
                         parent_menu.replace('"', '') + '"' + maya_menu)


def run(*args, **kwargs):  # @UnusedVariable
    """ Menu run execution

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """

    # get check-box state
    state = args[0]

    if state:
        cmds.optionVar(intValue=("mgear_dag_menu_OV", 1))
    else:
        cmds.optionVar(intValue=("mgear_dag_menu_OV", 0))

    # runs dag menu right click mgear's override
    mgear_dagmenu_toggle(state)
