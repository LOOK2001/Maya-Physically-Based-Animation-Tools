from PySide2 import QtCore
from PySide2 import QtWidgets
from PySide2 import QtGui
from shiboken2 import wrapInstance

import maya.OpenMayaUI as omui

import maya.cmds as cmds
import random

def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)

class TestDialog(QtWidgets.QDialog):
    
    def __init__(self, parent=maya_main_window()):
        super(TestDialog, self).__init__(parent)
        
        self.setWindowTitle("Test Dialog")
        self.setMinimumWidth(200)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)
        
        self.create_widgets()
        self.create_layout()
        self.create_connections()
        
    def create_widgets(self):
        self.title_label = QtWidgets.QLabel("Boids")
        self.title_label.setAlignment(QtCore.Qt.AlignHCenter)
        myFont=QtGui.QFont('Arial', 12)
        myFont.setBold(True)
        self.title_label.setFont(myFont)

        self.reload_plug_btn = QtWidgets.QPushButton("Reload")
        self.create_boids_btn = QtWidgets.QPushButton("Create Boids")
        self.connect_boids_btn = QtWidgets.QPushButton("Connect Boids")
        self.setup_boids_btn = QtWidgets.QPushButton("Setup Boids")
        self.ok_btn = QtWidgets.QPushButton("OK")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        
    def create_layout(self):
        function_layout = QtWidgets.QVBoxLayout()
        function_layout.addStretch()
        function_layout.addWidget(self.title_label)
        function_layout.addWidget(self.reload_plug_btn)
        function_layout.addWidget(self.create_boids_btn)
        function_layout.addWidget(self.connect_boids_btn)
        function_layout.addWidget(self.setup_boids_btn)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(function_layout)
        main_layout.addLayout(button_layout)

    def create_connections(self):
        self.reload_plug_btn.clicked.connect(self.reload_plugin)

        self.create_boids_btn.clicked.connect(self.create_boids)

        self.connect_boids_btn.clicked.connect(self.connect_boids)

        self.setup_boids_btn.clicked.connect(self.setup_boids)

        self.cancel_btn.clicked.connect(self.close)

    def reload_plugin(self):
        cmds.file(new=True, force=True)

        plugin_name = "boid_node.py"

        cmds.evalDeferred('if cmds.pluginInfo("{0}", q=True, loaded=True): cmds.unloadPlugin("{0}")'.format(plugin_name))
        cmds.evalDeferred('if not cmds.pluginInfo("{0}", q=True, loaded=True): cmds.loadPlugin("{0}")'.format(plugin_name))
        #cmds.evalDeferred('cmds.file("C:/Users/abc/Desktop/collision.mb", open=True, force=True)')

        cmds.evalDeferred('cmds.createNode("boidnode")')

        cmds.evalDeferred('cmds.connectAttr("time1.outTime", "boidnode1.time", f=True)')
        print cmds.playbackOptions(maxTime=1000, e=True)

    def create_boids(self):
        cmds.select(clear=True)
        boids = []
        for i in xrange(5):
            boid = cmds.polySphere()
            boids.append(boid[0])
            x = random.uniform(-3.0,3.0)
            y = random.uniform(-3.0,3.0)
            z = random.uniform(-3.0,3.0)
            cmds.setAttr(boid[0]+'.translate', x, y, z, type='double3')
            cmds.setAttr(boid[0]+'.scale', 0.35, 0.35, 0.35, type='double3')
        cmds.select(boids)
    
    def connect_boids(self):
        items = cmds.ls(selection=True)

        for it in xrange(len(items)):
            tran = cmds.getAttr(items[it]+'.translate')[0]
            print tran
            cmds.setAttr('boidnode1.output[%s]' % it, tran[0], tran[1], tran[2], type="double3")
            cmds.connectAttr("boidnode1.output[%s]" % it, items[it] + ".translate", f=True)

    def setup_boids(self):
        locator = cmds.spaceLocator()
        cmds.connectAttr(locator[0] + ".translate", "boidnode1.goal", f=True)

try:
    test_dialog.close() # pylint: disable=E0601
    test_dialog.deleteLater()
except:
    pass
        
test_dialog = TestDialog()
test_dialog.show()