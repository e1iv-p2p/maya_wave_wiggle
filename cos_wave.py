import math
import sys
from PySide2 import QtWidgets, QtCore
import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMayaUI as omui
try:    # noinspection PyUnresolvedReferences,PyUnboundLocalVariable
    long
except NameError:   # Python 3 compatibility
    long = int
    unicode = str

Wgt_instance = None

#ZVParent stuff
PARENT_HANDLE_SUFFIX = '_PH'
SNAP_GROUP_SUFFIX = '_SN'
PARENT_CONSTRAINT_SUFFIX = '_PC'
CONTROL_SUFFIX = '_CTRL'
REMOVE_CONTROL_SUFFIX = False
ALLOW_REFERENCE_ROOT = True
#ZVParent stuff

controls = None
num =None



# How to use:
# Select controls for wiggle
# create_parent_groups() to create offset
# create_locators() then place this shit whenever u want, but X-axis is better choice)
# wiggle_build()
# connect_to_wiggle() can be different for different cases


def connect_to_wiggle():
    for i, x in enumerate(controls, start=1):
        wig_grp = pm.PyNode(f'Wiggle_Offset_{i}')
        trgt_node = pm.PyNode(f'{x.name()}{SNAP_GROUP_SUFFIX}')
        wig_grp.ty >> trgt_node.tz
        wig_grp.rz >> trgt_node.ry


def create_locators():
    create_parent_groups()
    pm.selectPref(tso=1)
    global controls, num
    controls = pm.ls(sl=1)
    if not controls:
        pm.warning('Select controls!')
        return
    num = len(controls)
    loc_up = pm.spaceLocator(n='chain_loc_end')
    loc_up.ty.set(1)
    loc_down = pm.spaceLocator(n='chain_loc_start')
    pm.warning('Place 2 locators for spline, on top and bottom of deformable geo')
    pm.warning('Then press create lattice')
    pm.warning("Don't forget about joint quantity")
    pm.select(loc_up)


def wiggle_build():
    wig_con = pm.createNode('transform', n='wiggle_control')
    pm.addAttr(wig_con, ln='first_wave_amp', at='double', min=-5, max=10, dv=0, keyable=True)
    pm.addAttr(wig_con, ln='first_wave_wavelength', at='double', min=0.01, max=5, dv=1, keyable=True)
    pm.addAttr(wig_con, ln='second_wave_amp', at='double', min=-5, max=5, dv=0, keyable=True)
    pm.addAttr(wig_con, ln='second_wave_wavelength', at='double', min=0.01, max=5, dv=1, keyable=True)
    pm.addAttr(wig_con, ln='third_wave_amp', at='double', min=-5, max=5, dv=0, keyable=True)
    pm.addAttr(wig_con, ln='third_wave_wavelength', at='double', min=0.01, max=5, dv=1, keyable=True)
    # pm.addAttr(wig_con, ln='z_wave_amp', at='double', min=-5, max=5, dv=0)
    # pm.addAttr(wig_con, ln='z_wave_wavelength', at='double', min=0.01, max=5, dv=1)
    pm.addAttr(wig_con, ln='speed', at='double', min=-15, max=15, dv=1, keyable=True)
    pm.addAttr(wig_con, ln='interp', at='long', min=0, max=3, dv=0, keyable=True)

    remap_exp = remap_exp_func(num)
    remap_linear = remap_linear_func(num)
    rev_remap_exp = rev_remap_exp_func(num)
    rev_remap_linear = rev_remap_linear_func(num)
    remap_mirror_exp = remap_mirror_exp_func(num)

    off_lst, joi_lst, off_root_lst, curve = curve_to_joints(num, False)

    pm.parent(off_root_lst, wig_con)
    math_expr_lst = []

    curveInfo = pm.createNode("curveInfo")
    curve.worldSpace >> curveInfo.inputCurve

    for i, grp in enumerate(off_lst):
        wave_math = pm.expression(n='wave_math',
                                  s="$x = .I[0];\n$first_wave_amp = .I[1];\n$first_wave_wavelength = .I[2];\n$second_wave_amp = .I[3];\n$second_wave_wavelength = .I[4];\n$third_wave_amp = .I[5];\n$third_wave_wavelength = .I[6];\n$z_wave_amp = .I[7];\n$z_wave_wavelength = .I[8];\n$speed = .I[9];\n$interp = .I[10];\n$interp_linear = .I[11];\n$interp_exp = .I[12];\n$interp_mirror_exp = .I[13];\n$interp_linear_rev = .I[14];\n\n\n\n\n\nfloat $interp_component;\nfloat $z, $y, $y1, $y2, $y3;\n$z = 0;\n\n\n\nif (frame >= 0)\n\t{\n\tif ($interp == 0)\n\t\t$interp_component = $interp_linear;\n\telse if ($interp == 1)\n\t\t$interp_component = $interp_exp;\n\telse if ($interp == 2)\n\t\t$interp_component = $interp_mirror_exp;\n\telse \t\n\t\t$interp_component = $interp_linear_rev;\n\n\t$y += $first_wave_amp * $interp_component * sin(($x / $first_wave_wavelength - $speed * time / sqrt($first_wave_wavelength)));\n\t//$z = $rot_amplitude * $interp_component * cos(($x / $rot_waveLength - $speed * time / $rot_waveLength));\n\n\t$y += $second_wave_amp * $interp_component * sin(($x / $second_wave_wavelength - $speed * time / sqrt($second_wave_wavelength)));\n\t//$z = $rot_amplitude * $interp_component * cos(($x / $rot_waveLength - $speed * time / $rot_waveLength));\n\n\t$y += $third_wave_amp * $interp_component * sin(($x / $third_wave_wavelength - $speed * time / sqrt($third_wave_wavelength)));\n\t//$z = $rot_amplitude * $interp_component * cos(($x / $rot_waveLength - $speed * time / $rot_waveLength));\n\n\t\n\t\n\t.O[0] = $y;\n\t.O[1] = $z;\n\t}"
                                  )
        wave_math.input[0].set(curveInfo.arcLength.get() / num - i)
        wig_con.first_wave_amp >> wave_math.input[1]
        wig_con.first_wave_wavelength >> wave_math.input[2]
        wig_con.second_wave_amp >> wave_math.input[3]
        wig_con.second_wave_wavelength >> wave_math.input[4]
        wig_con.third_wave_amp >> wave_math.input[5]
        wig_con.third_wave_wavelength >> wave_math.input[6]
        # wig_con.z_wave_amp >> wave_math.input[7]
        # wig_con.z_wave_wavelength >> wave_math.input[8]
        wig_con.speed >> wave_math.input[9]
        wig_con.interp >> wave_math.input[10]
        remap_linear.value[i].value_FloatValue >> wave_math.input[11]
        remap_exp.value[i].value_FloatValue >> wave_math.input[12]
        remap_mirror_exp.value[i].value_FloatValue >> wave_math.input[13]
        rev_remap_linear.value[i].value_FloatValue >> wave_math.input[14]

        wave_math.output[0] >> grp.ty
        wave_math.output[1] >> grp.tz

        math_expr_lst.append(wave_math)

    set_rotate(off_lst)
    mel.eval('cycleCheck -e off')

def curve_to_joints(num, direction):
    if direction:
        step = 1
    else:
        step = -1
    loc_up = pm.PyNode('chain_loc_end')
    loc_down = pm.PyNode('chain_loc_start')

    joi_lst = []
    off_lst = []
    off_root_lst = []
    curve = pm.curve(d=3, periodic=0, n='stretch_curva',
                     p=[pm.xform(loc_up, ws=1, q=1, t=1),
                        pm.xform(loc_up, ws=1, q=1, t=1),
                        pm.xform(loc_down, ws=1, q=1, t=1),
                        pm.xform(loc_down, ws=1, q=1, t=1)],
                     )
    shape = pm.listRelatives(curve, shapes=1)

    if pm.objectType(shape) == "nurbsCurve":
        newCV = pm.duplicate(shape, n="myRebuildCurve")
        rebuildCV = pm.rebuildCurve(
            newCV, rt=0, s=num, replaceOriginal=True)

        pm.delete("{0}.cv[1]".format(rebuildCV[0]))
        pm.delete("{1}.cv[{0}]".format(num, rebuildCV[0]))

        i = 1
        for x in range(0, num)[::step]:
            cvPoint = "{1}.cv[{0}]".format(x, rebuildCV[0])
            locPos = pm.xform(cvPoint, q=True, ws=True, t=True)
            offset1 = pm.createNode("transform", n=f"Wiggle_Offset_{i}")
            offset2 = pm.createNode("transform", n=f"Wiggle_Offset_Root_{i}")
            offset1.t.set(locPos)
            offset2.t.set(locPos)

            joint = pm.joint(n=f'wiggle_{i}')
            pm.parent(joint, offset1)
            pm.parent(offset1, offset2)
            joi_lst.append(joint)
            off_lst.append(offset1)
            off_root_lst.append(offset2)
            i += 1

        pm.delete(rebuildCV)

    pm.delete(loc_up)
    pm.delete(loc_down)

    return off_lst, joi_lst, off_root_lst, curve


def remap_mirror_exp_func(num):
    remap_mirror_exp = pm.createNode('remapValue', n='remap_mirror_exp')
    for i in range(num):
        remap_mirror_exp.value[i].value_Position.set(i / num)
        if i < num / 2:
            remap_mirror_exp.value[i].value_FloatValue.set(math.exp(-4 * i / num))
        else:
            remap_mirror_exp.value[i].value_FloatValue.set(math.exp(-4 * (num - i) / num))
        remap_mirror_exp.value[i].value_Interp.set(3)

    return (remap_mirror_exp)


def remap_exp_func(num):
    remap_exp = pm.createNode('remapValue', n='remap_exp')
    for i in range(num):
        remap_exp.value[i].value_Position.set(i / num)
        remap_exp.value[i].value_FloatValue.set(1 - math.exp(-4 * i / num))
        remap_exp.value[i].value_Interp.set(3)

    return (remap_exp)


def remap_linear_func(num):
    remap_linear = pm.createNode('remapValue', n='remap_linear')
    for i in range(num):
        remap_linear.value[i].value_Position.set(i / num)
        remap_linear.value[i].value_FloatValue.set(i / num)
        remap_linear.value[i].value_Interp.set(3)

    return (remap_linear)


def rev_remap_exp_func(num):
    rev_remap_exp = pm.createNode('remapValue', n='rev_remap_exp')
    for i in range(num):
        rev_remap_exp.value[i].value_Position.set(i / num)
        rev_remap_exp.value[i].value_FloatValue.set(math.exp(-4 * (num - i) / num))
        rev_remap_exp.value[i].value_Interp.set(3)

    return (rev_remap_exp)


def rev_remap_linear_func(num):
    rev_remap_linear = pm.createNode('remapValue', n='rev_remap_linear')
    for i in range(num):
        rev_remap_linear.value[i].value_Position.set(i / num)
        rev_remap_linear.value[i].value_FloatValue.set((num - i) / num)
        rev_remap_linear.value[i].value_Interp.set(3)

    return (rev_remap_linear)


def set_rotate(off_lst):
    for i, grp in enumerate(off_lst):
        if grp != off_lst[-1]:
            next_grp = off_lst[i + 1]
            decompose_start = pm.createNode('decomposeMatrix', n=f'decomp_start_{i}')
            decompose_end = pm.createNode('decomposeMatrix', n=f'decomp_end_{i}')
            get_vec = pm.createNode('plusMinusAverage', n=f'get_vector_{i}')
            get_vec.operation.set(2)
            angle_between = pm.createNode('angleBetween', n=f'angle_between_{i}')
            rev_angle = pm.createNode('floatMath', n=f'reverce_sign_{i}')
            rev_angle.operation.set(2)
            rev_angle.floatB.set(-1)

            grp.worldMatrix >> decompose_start.inputMatrix
            next_grp.worldMatrix >> decompose_end.inputMatrix
            decompose_end.outputTranslate >> get_vec.input3D[0]
            decompose_start.outputTranslate >> get_vec.input3D[1]
            get_vec.output3D >> angle_between.vector1
            angle_between.vector2.set(1, 0, 0)
            angle_between.euler.eulerZ >> rev_angle.floatA
            rev_angle.outFloat >> grp.rz

        else:
            rev_angle = pm.PyNode(f'reverce_sign_{i - 1}')
            rev_angle.outFloat >> grp.rz


# ZVParent start
def _get_parent_handle(obj):
    """Restituisce il nome del parent handle."""

    if REMOVE_CONTROL_SUFFIX and obj.endswith(CONTROL_SUFFIX):
        obj = obj[:-len(CONTROL_SUFFIX)]

    return obj + PARENT_HANDLE_SUFFIX


def _get_snap_group(obj):
    """Restituisce il nome dello snap group."""

    if REMOVE_CONTROL_SUFFIX and obj.endswith(CONTROL_SUFFIX):
        obj = obj[:-len(CONTROL_SUFFIX)]

    return obj + SNAP_GROUP_SUFFIX


def create_parent_groups(translation=True, rotation=True):
    """Funzione popup per la preparazione dei controlli nel file reference."""

    # carica la selezione
    ctrls = cmds.ls(sl=True)

    # se non ci sono elementi selezionati esci
    if not ctrls:
        raise Exception('You must select one or more objects')

    counter = 0
    for ctrl in ctrls:
        # se l'oggetto non e' provvisto di parent handle e snap group creali
        temp = cmds.ls(_get_parent_handle(ctrl))
        if not temp:
            # se l'oggetto e' referenziato interrompi il ciclo
            if not _create_parent_master(ctrl, translation, rotation):
                return
            counter += 1
    # alla fine riseleziona i controlli
    cmds.select(ctrls)

    # messaggio
    if counter == 1:
        singplur = ''
    else:
        singplur = 's'
    sys.stdout.write('Parent groups created for %d object%s\n' % (len(ctrls), singplur))


def _create_parent_master(obj, translation=True, rotation=True):
    """Crea i gruppi necessari per utilizzare il parent master."""

    # creo il parent handle e lo snap group dell'oggetto (aventi stesso pivot)
    # un file referenziato genera eccezione
    if cmds.referenceQuery(obj, inr=True) and (not ALLOW_REFERENCE_ROOT or cmds.listRelatives(obj, p=True)):
        sys.stdout.write('Read-only hierarchy detected\n')
        msg = 'Are you working with referenced files?\n\n' \
              'ZVPM can\'t group "%s" because it\'s in a read-only hierarchy.\n\n\n' \
              'Do the following:\n\n' \
              '- Open the referenced file.\n' \
              '- Select this object, right-click on "Attach objects" button and "Create parent groups".\n' \
              '- Save the file.' % obj
        cmds.confirmDialog(title='Referenced file - ZV Parent Master', message=msg)
        return False

    # crea gruppi con la matrice del parente e il pivot dell'oggetto
    piv = cmds.xform(obj, q=True, rp=True, ws=True)
    obj_relatives = cmds.listRelatives(obj, p=True, pa=True)
    obj_parent = obj_relatives and obj_relatives[0] or None
    ph = pm.createNode('transform', p=obj_parent, n=_get_parent_handle(obj))
    sg = pm.createNode('transform', p=ph, n=_get_snap_group(obj))
    cmds.xform(ph.name(), sg.name(), piv=piv, ws=True)
    pm.parent(pm.PyNode(obj), sg)

    # locca gli attributi non diponibili e quelli non richiesti
    ts = {'tx', 'ty', 'tz'}
    rs = {'rx', 'ry', 'rz'}

    avail_attrs = set(cmds.listAttr(obj, k=True, u=True, sn=True) or [])
    attrs_to_lock = (ts | rs) - avail_attrs
    if not translation:
        attrs_to_lock |= ts
    if not rotation:
        attrs_to_lock |= rs

    for attr in attrs_to_lock:
        pm.setAttr('%s.%s' % (ph, attr), lock=True)

    return True
# ZVParent end


class Wiggle(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(Wiggle, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window)
        self.setWindowTitle('Wiggle')
        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_widgets(self):
        self.label = QtWidgets.QLabel('Select controls you want affect then press Create locators button')
        self.btn_loc = QtWidgets.QPushButton('Create locators')
        self.btn_wiggle = QtWidgets.QPushButton('Create wiggle')

    def create_layouts(self):
        self.main_lo = QtWidgets.QVBoxLayout(self)
        self.main_lo.addWidget(self.label)
        self.main_lo.addWidget(self.btn_loc)
        self.main_lo.addWidget(self.btn_wiggle)

    def create_connections(self):
        self.btn_loc.pressed.connect(self.btn_loc_press)
        self.btn_wiggle.pressed.connect(self.btn_wiggle_press)

    def btn_loc_press(self):
        self.label.setText('Now we think in 2d space, place locator chain_loc_end on x axis with coordinates for example (5,0,0)\nThen press Create wiggle button')
        create_locators()

    def btn_wiggle_press(self):
        self.label.setText('All control info in wiggle control node\nTo move this, set wave amp != 0 and change frames')
        wiggle_build()
        connect_to_wiggle()


def create_ui():
    global Wgt_instance
    if Wgt_instance is None:
        q_maya_window = get_maya_window()
        Wgt_instance = Wiggle(parent=q_maya_window)

    Wgt_instance.show()
    Wgt_instance.setWindowState(QtCore.Qt.WindowNoState | QtCore.Qt.WindowActive)
    Wgt_instance.activateWindow()
    return Wgt_instance


def get_maya_window():
    ptr = omui.MQtUtil.mainWindow()
    if ptr is not None:
        return wrp(long(ptr), QtWidgets.QMainWindow)





