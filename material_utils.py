import random
from pathlib import Path

import bpy


def create_material(mat_name, model_ob):
    md = model_ob.data
    mat = bpy.data.materials.get(mat_name, None)
    if mat:
        if md.materials.get(mat.name, None):
            return mat
        else:
            md.materials.append(mat)
    else:
        mat = bpy.data.materials.new(mat_name)
        mat.diffuse_color = [random.uniform(.4, 1) for _ in range(3)] + [1.0]
        md.materials.append(mat)
    return mat


class Nodes:
    ShaderNodeAddShader = 'ShaderNodeAddShader'
    ShaderNodeAmbientOcclusion = 'ShaderNodeAmbientOcclusion'
    ShaderNodeAttribute = 'ShaderNodeAttribute'
    ShaderNodeBackground = 'ShaderNodeBackground'
    ShaderNodeBevel = 'ShaderNodeBevel'
    ShaderNodeBlackbody = 'ShaderNodeBlackbody'
    ShaderNodeBrightContrast = 'ShaderNodeBrightContrast'
    ShaderNodeBsdfAnisotropic = 'ShaderNodeBsdfAnisotropic'
    ShaderNodeBsdfDiffuse = 'ShaderNodeBsdfDiffuse'
    ShaderNodeBsdfGlass = 'ShaderNodeBsdfGlass'
    ShaderNodeBsdfGlossy = 'ShaderNodeBsdfGlossy'
    ShaderNodeBsdfHair = 'ShaderNodeBsdfHair'
    ShaderNodeBsdfHairPrincipled = 'ShaderNodeBsdfHairPrincipled'
    ShaderNodeBsdfPrincipled = 'ShaderNodeBsdfPrincipled'
    ShaderNodeBsdfRefraction = 'ShaderNodeBsdfRefraction'
    ShaderNodeBsdfToon = 'ShaderNodeBsdfToon'
    ShaderNodeBsdfTranslucent = 'ShaderNodeBsdfTranslucent'
    ShaderNodeBsdfTransparent = 'ShaderNodeBsdfTransparent'
    ShaderNodeBsdfVelvet = 'ShaderNodeBsdfVelvet'
    ShaderNodeBump = 'ShaderNodeBump'
    ShaderNodeCameraData = 'ShaderNodeCameraData'
    ShaderNodeClamp = 'ShaderNodeClamp'
    ShaderNodeCombineHSV = 'ShaderNodeCombineHSV'
    ShaderNodeCombineRGB = 'ShaderNodeCombineRGB'
    ShaderNodeCombineXYZ = 'ShaderNodeCombineXYZ'
    ShaderNodeCustomGroup = 'ShaderNodeCustomGroup'
    ShaderNodeDisplacement = 'ShaderNodeDisplacement'
    ShaderNodeEeveeSpecular = 'ShaderNodeEeveeSpecular'
    ShaderNodeEmission = 'ShaderNodeEmission'
    ShaderNodeFresnel = 'ShaderNodeFresnel'
    ShaderNodeGamma = 'ShaderNodeGamma'
    ShaderNodeGroup = 'ShaderNodeGroup'
    ShaderNodeHairInfo = 'ShaderNodeHairInfo'
    ShaderNodeHoldout = 'ShaderNodeHoldout'
    ShaderNodeHueSaturation = 'ShaderNodeHueSaturation'
    ShaderNodeInvert = 'ShaderNodeInvert'
    ShaderNodeLayerWeight = 'ShaderNodeLayerWeight'
    ShaderNodeLightFalloff = 'ShaderNodeLightFalloff'
    ShaderNodeLightPath = 'ShaderNodeLightPath'
    ShaderNodeMapRange = 'ShaderNodeMapRange'
    ShaderNodeMapping = 'ShaderNodeMapping'
    ShaderNodeMath = 'ShaderNodeMath'
    ShaderNodeMixRGB = 'ShaderNodeMixRGB'
    ShaderNodeMixShader = 'ShaderNodeMixShader'
    ShaderNodeNewGeometry = 'ShaderNodeNewGeometry'
    ShaderNodeNormal = 'ShaderNodeNormal'
    ShaderNodeNormalMap = 'ShaderNodeNormalMap'
    ShaderNodeObjectInfo = 'ShaderNodeObjectInfo'
    ShaderNodeOutputAOV = 'ShaderNodeOutputAOV'
    ShaderNodeOutputLight = 'ShaderNodeOutputLight'
    ShaderNodeOutputLineStyle = 'ShaderNodeOutputLineStyle'
    ShaderNodeOutputMaterial = 'ShaderNodeOutputMaterial'
    ShaderNodeOutputWorld = 'ShaderNodeOutputWorld'
    ShaderNodeParticleInfo = 'ShaderNodeParticleInfo'
    ShaderNodeRGB = 'ShaderNodeRGB'
    ShaderNodeRGBCurve = 'ShaderNodeRGBCurve'
    ShaderNodeRGBToBW = 'ShaderNodeRGBToBW'
    ShaderNodeScript = 'ShaderNodeScript'
    ShaderNodeSeparateHSV = 'ShaderNodeSeparateHSV'
    ShaderNodeSeparateRGB = 'ShaderNodeSeparateRGB'
    ShaderNodeSeparateXYZ = 'ShaderNodeSeparateXYZ'
    ShaderNodeShaderToRGB = 'ShaderNodeShaderToRGB'
    ShaderNodeSqueeze = 'ShaderNodeSqueeze'
    ShaderNodeSubsurfaceScattering = 'ShaderNodeSubsurfaceScattering'
    ShaderNodeTangent = 'ShaderNodeTangent'
    ShaderNodeTexBrick = 'ShaderNodeTexBrick'
    ShaderNodeTexChecker = 'ShaderNodeTexChecker'
    ShaderNodeTexCoord = 'ShaderNodeTexCoord'
    ShaderNodeTexEnvironment = 'ShaderNodeTexEnvironment'
    ShaderNodeTexGradient = 'ShaderNodeTexGradient'
    ShaderNodeTexIES = 'ShaderNodeTexIES'
    ShaderNodeTexImage = 'ShaderNodeTexImage'
    ShaderNodeTexMagic = 'ShaderNodeTexMagic'
    ShaderNodeTexMusgrave = 'ShaderNodeTexMusgrave'
    ShaderNodeTexNoise = 'ShaderNodeTexNoise'
    ShaderNodeTexPointDensity = 'ShaderNodeTexPointDensity'
    ShaderNodeTexSky = 'ShaderNodeTexSky'
    ShaderNodeTexVoronoi = 'ShaderNodeTexVoronoi'
    ShaderNodeTexWave = 'ShaderNodeTexWave'
    ShaderNodeTexWhiteNoise = 'ShaderNodeTexWhiteNoise'
    ShaderNodeUVAlongStroke = 'ShaderNodeUVAlongStroke'
    ShaderNodeUVMap = 'ShaderNodeUVMap'
    ShaderNodeValToRGB = 'ShaderNodeValToRGB'
    ShaderNodeValue = 'ShaderNodeValue'
    ShaderNodeVectorCurve = 'ShaderNodeVectorCurve'
    ShaderNodeVectorDisplacement = 'ShaderNodeVectorDisplacement'
    ShaderNodeVectorMath = 'ShaderNodeVectorMath'
    ShaderNodeVectorRotate = 'ShaderNodeVectorRotate'
    ShaderNodeVectorTransform = 'ShaderNodeVectorTransform'
    ShaderNodeVertexColor = 'ShaderNodeVertexColor'
    ShaderNodeVolumeAbsorption = 'ShaderNodeVolumeAbsorption'
    ShaderNodeVolumeInfo = 'ShaderNodeVolumeInfo'
    ShaderNodeVolumePrincipled = 'ShaderNodeVolumePrincipled'
    ShaderNodeVolumeScatter = 'ShaderNodeVolumeScatter'
    ShaderNodeWavelength = 'ShaderNodeWavelength'
    ShaderNodeWireframe = 'ShaderNodeWireframe'


def create_texture(texture_path: Path):
    return bpy.data.images.load(texture_path.as_posix())


def clear_nodes(material):
    for node in material.node_tree.nodes:
        material.node_tree.nodes.remove(node)


def create_node(material, node_type: str, name: str = None, location=None):
    node = material.node_tree.nodes.new(node_type)
    if name:
        node.name = name
        node.label = name
    if location is not None:
        node.location = location
    return node


def create_texture_node(material, texture, name=None, location=None):
    texture_node = create_node(material, Nodes.ShaderNodeTexImage, name)
    if texture is not None:
        texture_node.image = texture
    if location is not None:
        texture_node.location = location
    return texture_node


def create_animated_texture_node(material, path: Path, frame_count: int = 0, name=None, location=None):
    texture_node = create_node(material, Nodes.ShaderNodeTexImage, name)
    texture_node.image = bpy.data.images.get(path.as_posix()) or bpy.data.images.load(path.as_posix())
    texture_node.image.source = 'SEQUENCE'
    texture_node.image_user.use_auto_refresh = True
    texture_node.image_user.use_cyclic = True
    texture_node.image_user.frame_duration = frame_count
    texture_node.image_user.frame_start = 0

    if location is not None:
        texture_node.location = location
    return texture_node


def create_node_group(material, group_name, location=None, *, name=None):
    group_node = create_node(material, Nodes.ShaderNodeGroup, name or group_name)
    group_node.node_tree = bpy.data.node_groups.get(group_name)
    group_node.width = group_node.bl_width_max
    if location is not None:
        group_node.location = location
    return group_node


def connect_nodes(material, output_socket, input_socket):
    material.node_tree.links.new(output_socket, input_socket)
