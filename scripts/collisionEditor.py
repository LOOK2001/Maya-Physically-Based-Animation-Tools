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
        self.title_label = QtWidgets.QLabel("Collisoin Detection")
        self.title_label.setAlignment(QtCore.Qt.AlignHCenter)
        myFont=QtGui.QFont('Arial', 12)
        myFont.setBold(True)
        self.title_label.setFont(myFont)
        
        self.reload_plug_btn = QtWidgets.QPushButton("Reload")
        self.create_spheres_btn = QtWidgets.QPushButton("Create Spheres")
        self.connect_CD_btn = QtWidgets.QPushButton("Connect Collision Detect")
        self.ok_btn = QtWidgets.QPushButton("OK")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        
    def create_layout(self):
        function_layout = QtWidgets.QVBoxLayout()
        function_layout.addStretch()
        function_layout.addWidget(self.title_label)
        function_layout.addWidget(self.reload_plug_btn)
        function_layout.addWidget(self.create_spheres_btn)
        function_layout.addWidget(self.connect_CD_btn)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(function_layout)
        main_layout.addLayout(button_layout)

    def create_connections(self):
        self.reload_plug_btn.clicked.connect(self.reload_plugin)

        self.create_spheres_btn.clicked.connect(self.create_spheres)

        self.connect_CD_btn.clicked.connect(self.connect_CD)

        self.cancel_btn.clicked.connect(self.close)

    def reload_plugin(self):
        # Any code required before unloading the plug-in (e.g. creating a new scene)
        cmds.file(new=True, force=True)

        # Reload the plugin
        plugin_name = "gravity_node.py"

        cmds.evalDeferred('if cmds.pluginInfo("{0}", q=True, loaded=True): cmds.unloadPlugin("{0}")'.format(plugin_name))
        cmds.evalDeferred('if not cmds.pluginInfo("{0}", q=True, loaded=True): cmds.loadPlugin("{0}")'.format(plugin_name))
        #cmds.evalDeferred('cmds.file("C:/Users/abc/Desktop/collision.mb", open=True, force=True)')

        print cmds.playbackOptions(maxTime=1000, e=True)

    def create_spheres(self):
        cmds.select(clear=True)
        boids = []
        for i in xrange(5):
            boid = cmds.polySphere()
            boids.append(boid[0])
            x = random.uniform(-3.0,3.0)
            y = random.uniform(-3.0,3.0)
            z = random.uniform(-3.0,3.0)
            cmds.setAttr(boid[0]+'.translate', x, y, z, type='double3')
        cmds.select(boids)
    
    def connect_CD(self):
        items = cmds.ls(selection=True)

        for it in xrange(len(items)):
            cmds.createNode("gravitynode")
            cmds.connectAttr("time1.outTime", "gravitynode%s.time" % (it+1), f=True)
            cmds.connectAttr("gravitynode%s.translate" % (it+1), items[it] + ".translate", f=True)


try:
    test_dialog.close() # pylint: disable=E0601
    test_dialog.deleteLater()
except:
    pass
        
test_dialog = TestDialog()
test_dialog.show()