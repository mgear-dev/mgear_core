
"""
dagmenu mGear module contains all the logic to override Maya's right
click dag menu.
"""

# Stdlib imports
from __future__ import absolute_import
from functools import partial

# Maya imports
from maya import cmds, mel
import pymel.core as pm

# mGear imports
import mgear
from mgear.core.anim_utils import select_all_child_controls
from mgear.core.anim_utils import reset_all_keyable_attributes
from mgear.core.pickWalk import get_all_tag_children
from mgear.core.transform import resetTransform
from mgear.core.anim_utils import mirrorPose
from mgear.core.anim_utils import get_host_from_node
from mgear.core.anim_utils import change_rotate_order
from mgear.core.anim_utils import ikFkMatch


def __change_rotate_order_callback(*args):
    """Wrapper function to call mGears change rotate order function

    Args:
        list: callback from menuItem
    """

    # triggers rotate order change
    change_rotate_order(args[0], args[1])


def __mirror_flip_pose_callback(*args):
    """Wrapper function to call mGears mirroPose function

    Args:
        list: callback from menuItem
    """

    # cast controls into pymel object nodes
    controls = [pm.PyNode(x) for x in args[0]]

    # triggers mirror
    mirrorPose(flip=args[1], nodes=controls)


def __range_switch_callback(*args):
    """ Wrapper function to call mGears range fk/ik switch function

    Args:
        list: callback from menuItem
    """

    cmds.warning("Not implemented wet!")


def __reset_attributes_callback(*args):
    """ Wrapper function to call mGears resetTransform function

    Args:
        list: callback from menuItem
    """

    attribute = args[1]

    for node in args[0]:
        control = pm.PyNode(node)

        if attribute == "translate":
            resetTransform(control, t=True, r=False, s=False)
        if attribute == "rotate":
            resetTransform(control, t=False, r=True, s=False)
        if attribute == "scale":
            resetTransform(control, t=False, r=False, s=True)


def __select_host_callback(*args):
    """ Wrapper function to call mGears select host

    Args:
        list: callback from menuItem
    """

    cmds.select(get_host_from_node(args[0]))


def __switch_fkik_callback(*args):
    """ Wrapper function to call mGears switch fk/ik snap function

    Args:
        list: callback from menuItem
    """

    switch_control = args[0].split("|")[-1].split(":")[-1]
    keyframe = args[1]
    blend_attr = args[2]

    # gets root node for the given control
    root = cmds.ls(args[0], long=True)[0].split("|")[1]

    # first find controls from the ui host control
    ik_controls = {"ik_control": None,
                   "pole_vector": None,
                   "ik_rot": None
                   }
    fk_controls = []

    # loops through connections
    for i in cmds.listConnections("{}.{}".format(args[0], blend_attr)):
        if (cmds.objExists("{}.isCtl".format(i)) and i not in ik_controls
                and "ik" in i or "upv" in i):
            control_type = i.split(":")[-1].split("_")[-2]
            if control_type == "ik":
                ik_controls["ik_control"] = i.split(":")[-1]
            elif control_type == "upv":
                ik_controls["pole_vector"] = i.split(":")[-1]
            elif control_type == "ikRot":
                ik_controls["ik_rot"] = i.split(":")[-1]

        elif cmds.objectType(i) == "reverse":
            for x in cmds.listConnections(i):
                if (cmds.objExists("{}.isCtl".format(x))
                        and x not in fk_controls and "fk" in x):
                    fk_controls.append(x.split(":")[-1])

    fk_controls = sorted(fk_controls)

    # runs switch
    ikFkMatch(model=root,
              ikfk_attr=blend_attr,
              ui_host=switch_control,
              fks=fk_controls,
              ik=ik_controls["ik_control"],
              upv=ik_controls["pole_vector"],
              ik_rot=ik_controls["ik_rot"],
              key=keyframe)


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


def mgear_dagmenu_callback(*args, **kwargs):  # @UnusedVariable
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
        if sel and cmds.objExists("{}.isCtl".format(sel[0])):
            # cleans menu
            _parent_menu = parent_menu.replace('"', '')
            cmds.menu(_parent_menu, edit=True, deleteAllItems=True)

            # fills menu
            mgear_dagmenu_fill(_parent_menu, sel[0])
        else:
            mel.eval("buildObjectMenuItemsNow " + parent_menu)

    # always return parent menu path
    return parent_menu


def mgear_dagmenu_fill(parent_menu, current_control):
    """Fill the given menu with mGear's custom animation menu

    Args:
        parent_menu(str): Parent Menu path name
        current_control(str): current selected mGear control
    """

    # gets current selection to use later on
    _current_selection = cmds.ls(selection=True)

    # handles ik fk blend attributes
    for attr in cmds.listAttr(current_control,
                              userDefined=True,
                              keyable=True) or []:
        if not attr.endswith("_blend"):
            continue
        # found attribute so get current state
        current_state = cmds.getAttr("{}.{}".format(current_control, attr))
        states = {0: "Fk",
                  1: "Ik"}

        rvs_state = states[int(not(current_state))]

        cmds.menuItem(parent=parent_menu, label="Switch {} to {}"
                      .format(attr.split("_blend")[0], rvs_state),
                      command=partial(__switch_fkik_callback, current_control,
                                      False, attr),
                      image="HIKcreateControlRig.png")

        cmds.menuItem(parent=parent_menu, label="Switch {} to {} + Key"
                      .format(attr.split("_blend")[0], rvs_state),
                      command=partial(__switch_fkik_callback, current_control,
                                      True, attr),
                      image="HIKcreateControlRig.png")

        cmds.menuItem(parent=parent_menu, label="Range switch",
                      command=partial(__range_switch_callback, current_control,
                                      True, attr))

        # divider
        cmds.menuItem(parent=parent_menu, divider=True)

    # check is given control is an mGear control
    if cmds.objExists("{}.uiHost".format(current_control)):
        # select ui host
        cmds.menuItem(parent=parent_menu, label="Select host",
                      command=partial(__select_host_callback, current_control),
                      image="parent.png")

    # get child controls
    child_controls = (get_all_tag_children(cmds.ls(cmds.listConnections(
                      current_control), type="controller")))
    child_controls.append(current_control)

    # select all function
    cmds.menuItem(parent=parent_menu, label="Select child controls",
                  command=partial(select_all_child_controls, current_control),
                  image="selectByHierarchy.png")

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # reset selected
    cmds.menuItem(parent=parent_menu, label="Reset",
                  command=partial(reset_all_keyable_attributes,
                                  _current_selection))

    # reset all bellow
    cmds.menuItem(parent=parent_menu, label="Reset all bellow",
                  command=partial(reset_all_keyable_attributes,
                                  child_controls))

    # add transform resets
    k_attrs = cmds.listAttr(current_control, keyable=True)
    for attr in ("translate", "rotate", "scale"):
        # checks if the attribute is a maya transform attribute
        if [x for x in k_attrs if attr in x and len(x) == len(attr) + 1]:
            icon = "{}_M.png".format(attr)
            if attr == "translate":
                icon = "move_M.png"
            cmds.menuItem(parent=parent_menu, label="Reset {}".format(attr),
                          command=partial(__reset_attributes_callback,
                                          _current_selection, attr),
                          image=icon)

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # add mirror
    cmds.menuItem(parent=parent_menu, label="Mirror",
                  command=partial(__mirror_flip_pose_callback,
                                  _current_selection,
                                  False))
    cmds.menuItem(parent=parent_menu, label="Mirror all bellow",
                  command=partial(__mirror_flip_pose_callback,
                                  child_controls,
                                  False))

    # add flip
    cmds.menuItem(parent=parent_menu, label="Flip",
                  command=partial(__mirror_flip_pose_callback,
                                  _current_selection,
                                  True))
    cmds.menuItem(parent=parent_menu, label="Flip all bellow",
                  command=partial(__mirror_flip_pose_callback,
                                  child_controls,
                                  True))

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # rotate order
    if [x for x in k_attrs if "rotateOrder" in x]:
        _current_r_order = cmds.getAttr("{}.rotateOrder"
                                        .format(current_control))
        _rot_men = cmds.menuItem(parent=parent_menu,
                                 subMenu=True, tearOff=False,
                                 label="Rotate Order switch")
        cmds.radioMenuItemCollection(parent=_rot_men)
        orders = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")
        for idx, order in enumerate(orders):
            if idx == _current_r_order:
                state = True
            else:
                state = False
            cmds.menuItem(parent=_rot_men, label=order, radioButton=state,
                          command=partial(__change_rotate_order_callback,
                                          current_control, order))


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
                          mgear_dagmenu_callback, parent_menu))

        # If state is set to False then put back Maya's dag menu
        # This is tricky because Maya's default menu command is a MEL call
        # The override part uses a python function partial call and because of
        # this we need to do some small hack on mGear_dag_menu_callback to give
        # back the default state of Maya's dag menu
        elif not state and type(menu_cmd) == partial:
            # we now check if the command override is one from us
            # here because we override original function we need
            # to get the function name by using partial.func
            if "mgear_dagmenu_callback" in menu_cmd.func.__name__:
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
