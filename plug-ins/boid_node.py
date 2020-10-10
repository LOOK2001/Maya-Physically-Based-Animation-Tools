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

class DynamicalState:
    def __init__(self, nb=0):
        self.nb_items = 0
        self.pos = []
        self.vel = []
        self.accel = []
        self.add(nb)
    def expand_to(self, data, n, setRandom = False):
        if len(data) >= n:
            return
        old_size = len(data)
        add_size = n - old_size
        for i in range(add_size):
            if not setRandom:
                data.append(om.MFloatVector(0.0, 0.0, 0.0))
            else:
                x = random.uniform(-1.0, 1.0)
                y = random.uniform(-1.0, 1.0)
                z = random.uniform(-1.0, 1.0)
                data.append(om.MFloatVector(x, y, z))
    def add(self, nb):
        add_size = self.nb_items + nb
        self.expand_to(self.pos, add_size, False)
        self.expand_to(self.vel, add_size, True)
        self.expand_to(self.accel, add_size)
        self.nb_items += nb

class AdvancePosition:
    def __init__(self, pq):
        self.PQ = pq  #type: DynamicalState
    def solve(self, dt):
        # update position
        for i in range(self.PQ.nb_items):
            self.PQ.pos[i] += self.PQ.vel[i] * dt

class AdvancedVelocity:
    def __init__(self, pq, f):
        self.PQ = pq  #type: DynamicalState
        self.force = f  #type: BoidForce
    def solve(self, dt):
        # force compute
        self.force.compute(self.PQ, dt)

        # update velocity
        for i in range(self.PQ.nb_items):
            self.PQ.vel[i] += self.PQ.accel[i] * dt

class BoidForce:
    leadBoid_index = 0
    leadBoid_goal = None

    def __init__(self, a, v, c, Max, rng, rng_ramp=1.0):
        self.A = a
        self.V = v
        self.C = c
        self.amax = Max
        self.range = rng
        self.range_ramp = rng_ramp
        self.fov = 152.0
        self.dfov = 10.0
        self.cosfov = math.cos(self.fov * 3.14159265 / 360.0)
        self.cosfovshell = math.cos(self.dfov * 3.14159265 / 360.0)

    def compute(self, pq, dt):
        for boid in range(pq.nb_items):
            kr = 0.0; kf = 0.0
            a_avoid = om.MFloatVector(0.0, 0.0, 0.0); a_velMat = om.MFloatVector(0.0, 0.0, 0.0); a_center = om.MFloatVector(0.0, 0.0, 0.0)
            _amax = self.amax

            # If the boid is the leader
            if boid == self.leadBoid_index:
                boid_dir = (self.leadBoid_goal - pq.pos[boid]).normal()
                pq.accel[boid] = boid_dir * self.amax
                continue

            for neighbor in range(pq.nb_items):
                if neighbor == boid:
                    continue
                xa = pq.pos[boid]  #type: om.MFloatVector
                xb = pq.pos[neighbor]  #type: om.MFloatVector
                va = pq.vel[boid]  #type: om.MFloatVector
                vb = pq.vel[neighbor]  #type: om.MFloatVector

                # Influence Range
                r = (xa - xb).length()
                if r < self.range:
                    kr = 1
                elif r > self.range and r < self.range_ramp:
                    kr = (self.range_ramp - r) / (self.range_ramp - self.range)
                elif r > self.range_ramp:
                    kr = 0

                # Influence FOV
                t = (xb - xa).normalize() * va.normal()
                if t > self.cosfovshell:
                    kf = 1
                elif t > self.cosfov and t < self.cosfovshell:
                    kf = (self.cosfov - t) / (self.cosfov - self.cosfovshell)
                elif t < self.cosfov:
                    kf = 0

                # Avoidance
                a_avoid += (self.A * (xa - xb).normalize() * (1 / (xa - xb).length()) * kr * kf)  #type: om.MFloatVector
                # Velocity Matching
                a_velMat += (self.V * (vb - va) * kr * kf)
                # Centering
                a_center += (self.C * (xb - xa) * kr * kf)

            # Acceleration Prioritization
            a_len = a_avoid.length()
            if a_len > self.amax:
                a_avoid = _amax * a_avoid.normal()
                a_velMat = a_center = om.MFloatVector(0.0, 0.0, 0.0)
            else:
                _amax = _amax - a_len
                a_len = a_velMat.length()
                if a_len > _amax:
                    a_velMat = _amax * a_velMat.normal()
                    a_center = om.MFloatVector(0.0, 0.0, 0.0)
                else:
                    _amax = _amax - a_len
                    a_len = a_center.length()
                    if a_len > _amax:
                        a_center = _amax * a_center.normal()
            aTotal = a_avoid + a_velMat + a_center

            # If the boid is the lead boid
            pq.accel[boid] = aTotal


class BoidNode(om.MPxNode):

    TYPE_NAME = "boidnode"
    TYPE_ID = om.MTypeId(0x0007F7FA)

    aTime = None
    aPos = None
    aOutput = None
    aLeadBoid_Index = None
    aGoal = None

    def __init__(self):
        super(BoidNode, self).__init__()
        self._initialized = False
        self._previousTime = om.MTime()
        self._mass = 1.0

        self.timeStep = 0.01
        self.state = DynamicalState()
        self.state.add(0)
        self.force = BoidForce(0.8, 1.0, 1.0, 5.0, 3.0, 5.0)
        self.positionSolve = AdvancePosition(self.state)
        self.velocitySolve = AdvancedVelocity(self.state, self.force)

    def resetParameter(self):
        pass

    def updatePos(self, plug, data):
        if self.state.nb_items < plug.numElements():
            self.state.add(plug.numElements() - self.state.nb_items)
        for plugIndex in xrange(plug.numElements()):
            aPlug = plug.elementByLogicalIndex(plugIndex)
            for childIndex in xrange(aPlug.numChildren()):
                self.state.pos[plugIndex][childIndex] = aPlug.child(childIndex).asFloat()

    def updateOutput(self, plug, data):
        if self.state.nb_items < plug.numElements():
            self.state.add(plug.numElements() - self.state.nb_items)
        for plugIndex in xrange(plug.numElements()):
            aPlug = plug.elementByLogicalIndex(plugIndex)
            for childIndex in xrange(aPlug.numChildren()):
                aPlug.child(childIndex).setFloat(self.state.pos[plugIndex][childIndex])

    def solve(self, dt):
        self.positionSolve.solve(dt)
        self.velocitySolve.solve(dt)

    def compute(self, plug, data):
        if plug != BoidNode.aOutput or plug.isArray == False:
            return

        # Get the inputs
        currentTime = data.inputValue(self.aTime).asTime()
        goal = data.inputValue(self.aGoal).asFloatVector()
        leadBoid = data.inputValue(self.aLeadBoid_Index).asInt()
        self.force.leadBoid_index = leadBoid
        self.force.leadBoid_goal = goal

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

        self.updatePos(plug, data)

        self.solve(self.timeStep)

        self.updateOutput(plug, data)

        output_data_handle = data.outputValue(BoidNode.aPos)  #type: om.MDataHandle
        output_data_handle.setClean()
        data.setClean(plug)

    @classmethod
    def creator(cls):
        return BoidNode()

    @classmethod
    def initialize(cls):
        numeric_attr = om.MFnNumericAttribute()
        unit_attr = om.MFnUnitAttribute()

        cls.aTime = unit_attr.create('time', 'time', om.MFnUnitAttribute.kTime, 0.0)
        unit_attr.keyable = True
        unit_attr.readable = False

        cls.aPos = numeric_attr.createPoint("translate", "tran")
        numeric_attr.writable = False

        cls.aOutput = numeric_attr.createPoint('output', 'output')
        numeric_attr.array = True
        numeric_attr.writable = True
        numeric_attr.usesArrayDataBuilder = True
        numeric_attr.connectable = True

        cls.aLeadBoid_Index = numeric_attr.create("reset", "reset", om.MFnNumericData.kInt, 0)

        cls.aGoal = numeric_attr.createPoint('goal', 'goal')
        numeric_attr.keyable = True

        cls.addAttribute(cls.aPos)
        cls.addAttribute(cls.aTime)
        cls.addAttribute(cls.aOutput)
        cls.addAttribute(cls.aLeadBoid_Index)
        cls.addAttribute(cls.aGoal)

        cls.attributeAffects(cls.aTime, cls.aOutput)

def initializePlugin(plugin):
    vecdor = "Xicheng"
    version = "1.0.0"

    fnPlugin = om.MFnPlugin(plugin, vecdor, version, 'Any')
    try:
        fnPlugin.registerNode(BoidNode.TYPE_NAME,
                              BoidNode.TYPE_ID,
                              BoidNode.creator,
                              BoidNode.initialize,
                              om.MPxNode.kDependNode)
    except:
        om.MGlobal.displayError("Failed to register node: {0}".format(BoidNode.TYPE_NAME))

def uninitializePlugin(plugin):
    fnPlugin = om.MFnPlugin(plugin)
    try:
        fnPlugin.deregisterNode(BoidNode.TYPE_ID)
    except:
        om.MGlobal.displayError("Failed to deregister node: {0}".format(BoidNode.TYPE_NAME))

if __name__ == "__main__":
    """
    For Development Only
    """
    # Any code required before unloading the plug-in (e.g. creating a new scene)
    cmds.file(new=True, force=True)

    # Reload the plugin
    plugin_name = "boid_node.py"

    cmds.evalDeferred('if cmds.pluginInfo("{0}", q=True, loaded=True): cmds.unloadPlugin("{0}")'.format(plugin_name))
    cmds.evalDeferred('if not cmds.pluginInfo("{0}", q=True, loaded=True): cmds.loadPlugin("{0}")'.format(plugin_name))
    #cmds.evalDeferred('cmds.file("C:/Users/abc/Desktop/collision.mb", open=True, force=True)')

    # Any setup code to help speed up testing (e.g. loading a test scene)
    # cmds.evalDeferred('cmds.createNode("boidnode")')

    # Connect outTime to time attribute
    # cmds.evalDeferred('cmds.connectAttr("time1.outTime", "boidnode1.time", f=True)')
