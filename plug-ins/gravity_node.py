import maya.api.OpenMaya as om
import maya.cmds as cmds
import math
import random

def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, object created using the Maya Python API 2.0.
    """
    pass

class CollisionSurfaceRaw:
    tri_elements = None

    def __init__(self, t):
        self.tri_elements = t

    def hit(self, P, V, CollData):
        tmax = CollData['t']
        tc = []
        tc.append(CollData['t'])
        CollData['status'] = False
        isFirst = True

        # Find all triangles that intersect
        for tri in self.tri_elements:
            if tri.hit(P, V, tmax, tc):
                # Find the largest backwards T (tc)
                if isFirst:
                    CollData['t'] = tc[0]
                    CollData['tri'] = tri
                    CollData['status'] = True
                    isFirst = False
                elif tc[0] > CollData['t']:
                    CollData['t'] = tc[0]
                    CollData['tri'] = tri
                    CollData['status'] = True
        return CollData['status']

class CollisionTriangleRaw:

    P0 = None
    P1 = None
    P2 = None
    e1 = None
    e2 = None
    normal = None

    def __init__(self, _p0, _p1, _p2):
        self.P0 = _p0
        self.P1 = _p1
        self.P2 = _p2
        self.e1 = self.P1 - self.P0  #type: om.MVector
        self.e2 = self.P2 - self.P0  #type: om.MVector
        self.normal = self.e1 ^ self.e2  #type: om.MVector
        self.normal.normalize()

    def hit(self, P, V, tmax, t):
        # Detect a collision has happened
        res1 = (P - self.P0) * self.normal
        res2 = ((P - (V * tmax)) - self.P0) * self.normal
        if res1 == 0.0:
            return False
        if (res1 * res2) > 0.0:
            return False
        #om.MGlobal.displayInfo("There is Collision")
        # Compute where and when collision takes place
        t[0] = (self.normal * (P - self.P0)) / (self.normal * V)
        xc = P - (V * t[0])
        #om.MGlobal.displayInfo("Collision Point: {0}".format(xc))
        #om.MGlobal.displayInfo("t: {0}".format(t[0]))
        if (t[0] * tmax < 0) or ((tmax - t[0])/tmax < 1e-6):
            return False

        result = self.is_in_triangle(xc)
        #om.MGlobal.displayInfo("Is in the triangle: {0}".format(result))
        return result

    def is_in_triangle(self, X):
        u = ((self.e2 ^ self.e2) * (self.e2 ^ (X - self.P0))) / (math.pow((self.e2 ^ self.e1).length(), 2))
        v = ((self.e1 ^ self.e2) * (self.e1 ^ (X - self.P0))) / (math.pow((self.e1 ^ self.e2).length(), 2))

        if (0 <= u) and (u <= 1) and ((0 <= v) and (v <= 1)) and ((0 <= (v + u)) and ((v + u) <= 1)):
            return True
        return False

class GravityNode(om.MPxNode):

    TYPE_NAME = "gravitynode"
    TYPE_ID = om.MTypeId(0x0007F7F9)

    aTime = None
    position = None
    reset = None

    def __init__(self):
        super(GravityNode, self).__init__()
        self._initialized = False
        self._previousTime = om.MTime()
        self._mass = 1.0
        self._gravity = om.MVector(0.0, -1.0, 0.0)
        self._accelerate = om.MVector(0.0, 0.0, 0.0)
        vel_x = random.uniform(-1.0, 1.0)
        vel_y = random.uniform(-1.0, 1.0)
        vel_z = random.uniform(-1.0, 1.0)
        self._velocity = om.MVector(vel_x, vel_y, vel_z)
        self._position = om.MVector(0.0, 0.0, 0.0)
        
        self.coeff_sticky = 1.0
        self.coeff_restitution = 1.0
        self.cube = GenerateCollisionCube(11.8)
        self.surf = CollisionSurfaceRaw(self.cube)
        self.cube2 = GenerateCollisionCube(25.0)
        self.dt = 0.1

    def resetParameter(self):
        self._gravity = om.MVector(0.0, -1.0, 0.0)
        self._accelerate = om.MVector(0.0, 0.0, 0.0)
        self._velocity = om.MVector(0.0, 0.0, 0.0)
        self._position = om.MVector(0.0, 0.0, 0.0)

    def handleCollisions(self, dt):
        CollData = {'t': dt, 'tri': None, 'status': False}
        while self.surf.hit(self._position, self._velocity, CollData):
            t = CollData['t']
            tri = CollData['tri']
            norm = tri.normal
            vn = norm * self._velocity
            vp = self._velocity - norm * vn
            vr = (self.coeff_sticky * vp) - (self.coeff_restitution * norm * vn)

            # Set new point
            xc = self._position - self._velocity * t
            x = xc + vr * t
            #om.MGlobal.displayInfo("Pos: {0}, Vel: {1}".format(self._position, self._velocity))
            self._position = x
            self._velocity = vr

    def compute(self, plug, data):
        if plug != GravityNode.position:
            return

        # Get the inputs
        currentTime = data.inputValue(self.aTime).asTime()
        isReset = data.inputValue(self.reset).asBool()
        if isReset:
            self.resetParameter()

        if not self._initialized:
            self._previousTime = currentTime
            self._initialized = True

        # Check if the timestep is just 1 frame since we want a stable simulation
        timeDifference = currentTime.value - self._previousTime.value
        if timeDifference > 1.0 or timeDifference < 0.0:
            self._initialized = False
            self._previousTime = currentTime
            data.setClean(plug)
            return

        self._previousTime = om.MTime(currentTime)
        self._accelerate = self._gravity / self._mass
        self._position += self._velocity * self.dt
        self.handleCollisions(self.dt)
        self._velocity += self._accelerate * self.dt

        position_data_handle = data.outputValue(GravityNode.position)
        outVector = om.MFloatVector(self._position.x, self._position.y, self._position.z)
        position_data_handle.setMFloatVector(outVector)
        position_data_handle.setClean()
        data.setClean(plug)

    @classmethod
    def creator(cls):
        return GravityNode()

    @classmethod
    def initialize(cls):
        numeric_attr = om.MFnNumericAttribute()
        unit_attr = om.MFnUnitAttribute()

        cls.aTime = unit_attr.create('time', 'time', om.MFnUnitAttribute.kTime, 0.0)
        unit_attr.keyable = True

        cls.position = numeric_attr.createPoint("translate", "tran")
        numeric_attr.writable = False

        cls.reset = numeric_attr.create("reset", "reset", om.MFnNumericData.kBoolean, 0)

        cls.addAttribute(cls.position)
        cls.addAttribute(cls.aTime)
        cls.addAttribute(cls.reset)

        cls.attributeAffects(cls.aTime, cls.position)
        cls.attributeAffects(cls.reset, cls.position)

def GenerateCollisionCube(size):
    verts = []
    verts.append(om.MVector(-1.0, -1.0, -1.0) * size)
    verts.append(om.MVector(1.0, -1.0, -1.0) * size)
    verts.append(om.MVector(1.0, 1.0, -1.0) * size)
    verts.append(om.MVector(-1.0, 1.0, -1.0) * size)
    verts.append(om.MVector(-1.0, -1.0, 1.0) * size)
    verts.append(om.MVector(1.0, -1.0, 1.0) * size)
    verts.append(om.MVector(1.0, 1.0, 1.0) * size)
    verts.append(om.MVector(-1.0, 1.0, 1.0) * size)
    faces = []
    face = [0] * 4
    face[0] = 1
    face[1] = 2
    face[2] = 6
    face[3] = 5
    faces.append(face)
    face = [0] * 4
    face[0] = 2
    face[1] = 3
    face[2] = 7
    face[3] = 6
    faces.append(face)
    face = [0] * 4
    face[0] = 0
    face[1] = 3
    face[2] = 2
    face[3] = 1
    faces.append(face)
    face = [0] * 4
    face[0] = 0
    face[1] = 4
    face[2] = 7
    face[3] = 3
    faces.append(face)
    face = [0] * 4
    face[0] = 0
    face[1] = 1
    face[2] = 5
    face[3] = 4
    faces.append(face)
    face = [0] * 4
    face[0] = 5
    face[1] = 6
    face[2] = 7
    face[3] = 4
    faces.append(face)
    surfs = []
    for face in faces:
        tri1 = CollisionTriangleRaw(verts[face[0]], verts[face[1]], verts[face[2]])
        result = verts[face[0]]
        surfs.append(tri1)
        tri2 = CollisionTriangleRaw(verts[face[2]], verts[face[3]], verts[face[0]])
        surfs.append(tri2)
    return surfs


def initializePlugin(plugin):
    vecdor = "Xicheng"
    version = "1.0.0"

    fnPlugin = om.MFnPlugin(plugin, vecdor, version, 'Any')
    try:
        fnPlugin.registerNode(GravityNode.TYPE_NAME,
                              GravityNode.TYPE_ID,
                              GravityNode.creator,
                              GravityNode.initialize,
                              om.MPxNode.kDependNode)
    except:
        om.MGlobal.displayError("Failed to register node: {0}".format(GravityNode.TYPE_NAME))

def uninitializePlugin(plugin):
    fnPlugin = om.MFnPlugin(plugin)
    try:
        fnPlugin.deregisterNode(GravityNode.TYPE_ID)
    except:
        om.MGlobal.displayError("Failed to deregister node: {0}".format(GravityNode.TYPE_NAME))

if __name__ == "__main__":
    """
    For Development Only
    """
    # Any code required before unloading the plug-in (e.g. creating a new scene)
    cmds.file(new=True, force=True)

    # Reload the plugin
    plugin_name = "gravity_node.py"

    cmds.evalDeferred('if cmds.pluginInfo("{0}", q=True, loaded=True): cmds.unloadPlugin("{0}")'.format(plugin_name))
    cmds.evalDeferred('if not cmds.pluginInfo("{0}", q=True, loaded=True): cmds.loadPlugin("{0}")'.format(plugin_name))
    cmds.evalDeferred('cmds.file("C:\\Users\\abc\\Desktop\\collision.mb", open=True, force=True)')

    # Any setup code to help speed up testing (e.g. loading a test scene)
    # cmds.evalDeferred('cmds.createNode("gravitynode")')

    # Connect outTime to time attribute
    # cmds.evalDeferred('cmds.connectAttr("time1.outTime", "gravitynode1.time", f=True)')
