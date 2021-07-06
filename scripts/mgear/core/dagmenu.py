
"""
dagmenu mGear module contains all the logic to override Maya's right
click dag menu.
"""

# Stdlib imports
from __future__ import absolute_import

import os
from functools import partial

# Maya imports
from maya import cmds, mel
import pymel.core as pm

# mGear imports
import mgear
from mgear.core.anim_utils import reset_all_keyable_attributes
from mgear.core.pickWalk import get_all_tag_children
from mgear.core.transform import resetTransform
from mgear.core.anim_utils import mirrorPose
from mgear.core.anim_utils import get_host_from_node
from mgear.core.anim_utils import change_rotate_order
from mgear.core.anim_utils import ikFkMatch_with_namespace
from mgear.core.anim_utils import get_ik_fk_controls
from mgear.core.anim_utils import get_ik_fk_controls_by_role
from mgear.core.anim_utils import IkFkTransfer
from mgear.core.anim_utils import changeSpace
from mgear.core.anim_utils import getNamespace
from mgear.core.anim_utils import stripNamespace


def __change_rotate_order_callback(*args):
    """Wrapper function to call mGears change rotate order function

    Args:
        list: callback from menuItem
    """

    # triggers rotate order change
    change_rotate_order(args[0], args[1])


def __keyframe_nodes_callback(*args):
    """Wrapper function to call Maya's setKeyframe command on given controls

    Args:
        list: callback from menuItem
    """

    cmds.setKeyframe(args[0])


def __mirror_flip_pose_callback(*args):
    """Wrapper function to call mGears mirroPose function

    Args:
        list: callback from menuItem
    """

    # cast controls into pymel object nodes
    controls = [pm.PyNode(x) for x in args[0]]

    # triggers mirror
    # we handle the mirror/flip each control individually even if the function
    # accepts several controls. Flipping on proxy attributes like blend
    # attributes cause an issue to rather than trying the complete list we do
    # one control to avoid the mirror to stop
    for ctl in controls:
        mirrorPose(flip=args[1], nodes=[ctl])


def _get_controls(switch_control, blend_attr, comp_ctl_list=None):
    # OBSOLETE:This function is obsolete and just keep for
    #          backward compatibility
    # replaced by get_ik_fk_controls_by_role in anim_utils module

    # first find controls from the ui host control
    ik_fk_controls = get_ik_fk_controls(switch_control,
                                        blend_attr,
                                        comp_ctl_list)

    # organise ik controls
    ik_controls = {"ik_control": None,
                   "pole_vector": None,
                   "ik_rot": None
                   }

    # removes namespace from controls and order them in something usable
    # by the ikFkMatch function

    # - IKS
    for x in ik_fk_controls["ik_controls"]:
        control_name = x.split(":")[-1]
        # control_type = control_name.split("_")[-2]
        if "_ik" in control_name.lower():
            ik_controls["ik_control"] = control_name
        elif "_upv" in control_name.lower():
            ik_controls["pole_vector"] = control_name
        elif "_ikrot" in control_name.lower():
            ik_controls["ik_rot"] = control_name

    # - FKS
    fk_controls = [x.split(":")[-1] for x in ik_fk_controls["fk_controls"]]
    fk_controls = sorted(fk_controls)

    return ik_controls, fk_controls


def _is_valid_rig_root(node):
    """
    Simple exclusion of the buffer nodes and org nodes
    Args:
        node: str
    Returns: bool

    """
    short_name = node.split("|")[-1]
    long_name = cmds.ls(node, l=True)[0]
    return not (any(["controllers_org" in long_name, "controlBuffer" in short_name]))


def _list_rig_roots():
    """
    Return all the rig roots in the scene
    Returns: [str,]
    """
    return [n.split(".")[0] for n in cmds.ls("*.is_rig", r=True, l=True) if _is_valid_rig_root(n.split(".")[0])]


def _find_rig_root(node):
    """
    Matches this node to the rig roots in the scene via a simple longName match
    Args:
        node: str
    Returns: str
    """
    long_name = cmds.ls(node, l=True)[0]
    roots = _list_rig_roots()
    for r in roots:
        if long_name.startswith(r):
            # this has to be a shortname otherwise IkFkTransfer will fail
            return r.split("|")[-1]
    return ""


def __range_switch_callback(*args):
    """ Wrapper function to call mGears range fk/ik switch function

    Args:
        list: callback from menuItem
    """

    # instance for the range switch util
    range_switch = IkFkTransfer()

    switch_control = args[0].split("|")[-1]
    blend_attr = args[1]

    # the gets root node for the given control
    # this assumes the rig is root is a root node.  But it's common practice to reference rigs into the scene
    # and use the reference group function to group incoming scene data.  Instead swap to _find_rig_root that will
    # do the same thing but account for potential parent groups.
    # root = cmds.ls(args[0], long=True)[0].split("|")[1]

    root = _find_rig_root(args[0])

    # ik_controls, fk_controls = _get_controls(switch_control, blend_attr)
    # search criteria to find all the components sharing the blend
    criteria = blend_attr.replace("_blend", "") + "_id*_ctl_cnx"
    component_ctl = cmds.listAttr(switch_control,
                                  ud=True,
                                  string=criteria)
    if component_ctl:
        ik_list = []
        ikRot_list = []
        fk_list = []
        upv_list = []

        for com_list in component_ctl:
            # set the initial val for the blend attr in each iteration
            ik_controls, fk_controls = get_ik_fk_controls_by_role(
                switch_control, com_list)
            ik_list.append(ik_controls["ik_control"])
            if ik_controls["ik_rot"]:
                ikRot_list.append(ik_controls["ik_rot"])
            upv_list.append(ik_controls["pole_vector"])
            fk_list = fk_list + fk_controls

        # calls the ui
        range_switch.showUI(model=root,
                            ikfk_attr=blend_attr,
                            uihost=stripNamespace(switch_control),
                            fks=fk_list,
                            ik=ik_list,
                            upv=upv_list,
                            ikRot=ikRot_list)


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


def __select_nodes_callback(*args):
    """ Wrapper function to call Maya select command

    Args:
        list: callback from menuItem
    """

    cmds.select(args[0], add=True)


def __switch_fkik_callback(*args):
    """ Wrapper function to call mGears switch fk/ik snap function

    Args:
        list: callback from menuItem
    """

    switch_control = args[0].split("|")[-1]
    keyframe = args[1]
    blend_attr = args[2]

    # gets namespace
    namespace = getNamespace(switch_control)

    # search criteria to find all the components sharing the blend
    criteria = blend_attr.replace("_blend", "") + "_id*_ctl_cnx"
    component_ctl = cmds.listAttr(switch_control,
                                  ud=True,
                                  string=criteria)
    blend_fullname = "{}.{}".format(switch_control, blend_attr)
    for i, comp_ctl_list in enumerate(component_ctl):
        # we need to need to set the original blend value for each ik/fk match
        if i == 0:
            init_val = cmds.getAttr(blend_fullname)
        else:
            cmds.setAttr(blend_fullname, init_val)

        ik_controls, fk_controls = get_ik_fk_controls_by_role(switch_control,
                                                              comp_ctl_list)

        # runs switch
        ikFkMatch_with_namespace(namespace=namespace,
                                 ikfk_attr=blend_attr,
                                 ui_host=switch_control,
                                 fks=fk_controls,
                                 ik=ik_controls["ik_control"],
                                 upv=ik_controls["pole_vector"],
                                 ik_rot=ik_controls["ik_rot"],
                                 key=keyframe)


def __switch_parent_callback(*args):
    """ Wrapper function to call mGears change space function

    Args:
        list: callback from menuItem
    """

    # creates a map for non logical components controls
    control_map = {"elbow": "mid",
                   "rot": "orbit",
                   "knee": "mid"}

    # switch_control = args[0].split("|")[-1].split(":")[-1]
    switch_control = args[0].split("|")[-1]
    uiHost = pm.PyNode(switch_control)  # UiHost is switch PyNode pointer
    switch_attr = args[1]
    switch_idx = args[2]
    search_token = switch_attr.split("_")[-1].split("ref")[0].split("Ref")[0]
    print search_token
    target_control = None

    # control_01 attr don't standard name ane need to be check
    attr_split_name = switch_attr.split("_")
    if len(attr_split_name) <= 2:
        attr_name = attr_split_name[0]
    else:
        attr_name = "_".join(attr_split_name[:-1])
    # search criteria to find all the components sharing the name
    criteria = attr_name + "_id*_ctl_cnx"
    component_ctl = cmds.listAttr(switch_control,
                                  ud=True,
                                  string=criteria)

    target_control_list = []
    for comp_ctl_list in component_ctl:

        # first search for tokens match in all controls. If not token is found
        # we will use all controls for the switch
        # this token match is a filter for components like arms or legs
        for ctl in uiHost.attr(comp_ctl_list).listConnections():
            if ctl.ctl_role.get() == search_token:
                target_control = ctl.stripNamespace()
                break
            elif (search_token in control_map.keys()
                  and ctl.ctl_role.get() == control_map[search_token]):
                target_control = ctl.stripNamespace()
                break

        if target_control:
            target_control_list.append(target_control)
        else:
            # token didn't match with any target control. We will add all
            # found controls for the match.
            # This is needed for regular ik match in Control_01
            for ctl in uiHost.attr(comp_ctl_list).listConnections():

                target_control_list.append(ctl.stripNamespace())

    # gets root node for the given control
    namespace_value = args[0].split("|")[-1].split(":")
    if len(namespace_value) > 1:
        namespace_value = namespace_value[0]
    else:
        namespace_value = ""

    root = None

    current_parent = cmds.listRelatives(args[0], fullPath=True, parent=True)
    if current_parent:
        current_parent = current_parent[0]

    while not root:

        if cmds.objExists("{}.is_rig".format(current_parent)):
            root = cmds.ls("{}.is_rig".format(current_parent))[0]
        else:
            try:
                current_parent = cmds.listRelatives(current_parent,
                                                    fullPath=True,
                                                    parent=True)[0]
            except TypeError:
                break

    if not root or not target_control_list:
        pm.displayInfo("Not root or target control list for space transfer")
        return

    autokey = cmds.listConnections("{}.{}".format(switch_control, switch_attr),
                                   type="animCurve")

    if autokey:
        for target_control in target_control_list:
            cmds.setKeyframe("{}:{}".format(
                namespace_value, target_control), "{}.{}"
                .format(switch_control, switch_attr),
                time=(cmds.currentTime(query=True) - 1.0))

    # triggers switch
    changeSpace(root,
                switch_control,
                switch_attr,
                switch_idx,
                target_control_list)

    if autokey:
        for target_control in target_control_list:
            cmds.setKeyframe("{}:{}".format(
                namespace_value, target_control), "{}.{}"
                .format(switch_control, switch_attr),
                time=(cmds.currentTime(query=True)))


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

    # get child controls
    child_controls = []
    for ctl in _current_selection:
        [child_controls.append(x)
         for x in get_all_tag_children(ctl)
         if x not in child_controls]
        # [child_controls.append(x)
        #  for x in get_all_tag_children(cmds.ls(cmds.listConnections(ctl),
        #                                        type="controller"))
        #  if x not in child_controls]

    child_controls.append(current_control)

    # handles ik fk blend attributes
    for attr in cmds.listAttr(current_control,
                              userDefined=True,
                              keyable=True) or []:
        if (not attr.endswith("_blend")
            or cmds.addAttr("{}.{}".format(current_control, attr),
                            query=True, usedAsProxy=True)):
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
                      image="kinReroot.png")

        cmds.menuItem(parent=parent_menu, label="Switch {} to {} + Key"
                      .format(attr.split("_blend")[0], rvs_state),
                      command=partial(__switch_fkik_callback, current_control,
                                      True, attr),
                      image="character.svg")

        cmds.menuItem(parent=parent_menu, label="Range switch",
                      command=partial(__range_switch_callback, current_control,
                                      attr))

        # divider
        cmds.menuItem(parent=parent_menu, divider=True)

    # check is given control is an mGear control
    if cmds.objExists("{}.uiHost".format(current_control)):
        # select ui host
        cmds.menuItem(parent=parent_menu, label="Select host",
                      command=partial(__select_host_callback, current_control),
                      image="hotkeySetSettings.png")

    # select all function
    cmds.menuItem(parent=parent_menu, label="Select child controls",
                  command=partial(__select_nodes_callback, child_controls),
                  image="dagNode.svg")

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # reset selected
    cmds.menuItem(parent=parent_menu, label="Reset",
                  command=partial(reset_all_keyable_attributes,
                                  _current_selection),
                  image="holder.svg")

    # reset all below
    cmds.menuItem(parent=parent_menu, label="Reset all below",
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
                                  False),
                  image="redrawPaintEffects.png")
    cmds.menuItem(parent=parent_menu, label="Mirror all below",
                  command=partial(__mirror_flip_pose_callback,
                                  child_controls,
                                  False))

    # add flip
    cmds.menuItem(parent=parent_menu, label="Flip",
                  command=partial(__mirror_flip_pose_callback,
                                  _current_selection,
                                  True),
                  image="redo.png")
    cmds.menuItem(parent=parent_menu, label="Flip all below",
                  command=partial(__mirror_flip_pose_callback,
                                  child_controls,
                                  True))

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # rotate order
    if (cmds.getAttr("{}.rotateOrder".format(current_control), channelBox=True)
        or cmds.getAttr("{}.rotateOrder".format(current_control), keyable=True)
        and not cmds.getAttr("{}.rotateOrder".format(current_control),
                             lock=True)):
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

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # handles constrains attributes (constrain switches)
    for attr in cmds.listAttr(current_control,
                              userDefined=True,
                              keyable=True) or []:

        # filters switch reference attributes
        if (cmds.addAttr("{}.{}".format(current_control, attr),
                         query=True, usedAsProxy=True)
                or not attr.endswith("ref")
                and not attr.endswith("Ref")):
            continue

        part, ctl = (attr.split("_")[0],
                     attr.split("_")[-1].split("Ref")[0].split("ref")[0])
        _p_switch_menu = cmds.menuItem(parent=parent_menu, subMenu=True,
                                       tearOff=False, label="Parent {} {}"
                                       .format(part, ctl),
                                       image="dynamicConstraint.svg")
        cmds.radioMenuItemCollection(parent=_p_switch_menu)
        k_values = cmds.addAttr("{}.{}".format(current_control, attr),
                                query=True, enumName=True).split(":")
        current_state = cmds.getAttr("{}.{}".format(current_control, attr))

        for idx, k_val in enumerate(k_values):
            if idx == current_state:
                state = True
            else:
                state = False
            cmds.menuItem(parent=_p_switch_menu, label=k_val,
                          radioButton=state,
                          command=partial(__switch_parent_callback,
                                          current_control, attr, idx, k_val))

    # divider
    cmds.menuItem(parent=parent_menu, divider=True)

    # select all rig controls
    selection_set = cmds.ls(cmds.listConnections(current_control),
                            type="objectSet")
    all_rig_controls = cmds.sets(selection_set, query=True)
    cmds.menuItem(parent=parent_menu, label="Select all controls",
                  command=partial(__select_nodes_callback, all_rig_controls))

    # key all below function
    cmds.menuItem(parent=parent_menu, label="Keyframe child controls",
                  command=partial(__keyframe_nodes_callback, child_controls),
                  image="setKeyframe.png")


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
        if state and type(menu_cmd) == unicode:
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
                         '"buildObjectMenuItemsNow '
                         + parent_menu.replace('"', '') + '"' + maya_menu)


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
