import math
import os
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Vector, Matrix

from BionicleHeroesTools.file_utils import FileBuffer
from BionicleHeroesTools.load_nup import load_textures, create_material
from BionicleHeroesTools.mesh_utils import unstripify
from BionicleHeroesTools.nup import AnimatedTexturesChunk
from BionicleHeroesTools.hgp import HGPModel


def import_hgp_from_path(hgp_path: Path):
    with FileBuffer(hgp_path) as buf:
        hgp = HGPModel.from_buffer(buf)

    tas_cache = (hgp_path.parent / "TAS_CACHE")
    os.makedirs(tas_cache, exist_ok=True)

    load_textures(hgp.textures, tas_cache)

    root = bpy.data.objects.new("ROOT", None)
    root.matrix_world = Euler((math.radians(90), 0, 0), "XYZ").to_matrix().to_4x4()
    bpy.context.scene.collection.objects.link(root)
    model_name = hgp_path.stem
    armature = bpy.data.armatures.new(f"{model_name}_ARM_DATA")
    armature_obj = bpy.data.objects.new(f"{model_name}_ARM", armature)
    armature_obj['MODE'] = 'SourceIO'
    armature_obj.show_in_front = True
    bpy.context.scene.collection.objects.link(armature_obj)

    armature_obj.select_set(True)
    bpy.context.view_layer.objects.active = armature_obj

    bpy.ops.object.mode_set(mode='EDIT')
    bl_bones = []
    for bone in hgp.bones:
        bl_bone = armature.edit_bones.new(bone.name)
        bl_bones.append(bl_bone)
    for bl_bone, s_bone in zip(bl_bones, hgp.bones):
        bl_bone.tail = Vector([0, 0, 0.3]) + bl_bone.head
        if s_bone.parent != -1:
            bl_parent = bl_bones[s_bone.parent]
            bl_bone.parent = bl_parent

    bpy.ops.object.mode_set(mode='POSE')
    for n, se_bone in enumerate(hgp.bones):
        bl_bone = armature_obj.pose.bones.get(se_bone.name)
        mat = Matrix(se_bone.matrix1).transposed()
        bl_bone.matrix_basis.identity()
        bl_bone.matrix = bl_bone.parent.matrix @ mat if bl_bone.parent else mat

    bpy.ops.pose.armature_apply()
    bpy.ops.object.mode_set(mode='OBJECT')

    armature_obj.parent = root
    for layer in hgp.layers:
        models, bone_models = layer
        for model in models:
            vertex_count = 0
            indices_count = 0
            indices = []
            indices_id_offset = 0
            indices_offset = 0
            material_indices = []
            materials_offset = 0
            for mesh in model.models:

                if (hgp.materials[mesh.material_id].unk_flags >> 6) & 1:
                    continue

                strip = mesh.strips[0]
                index_block = hgp.index_buffers[0]
                if strip.index_mode == 5:
                    tri_list = unstripify(index_block.read_indices(strip.indices_offset, strip.indices_count))
                elif strip.index_mode == 4:
                    tri_list = index_block.read_indices(strip.indices_offset, strip.indices_count)
                else:
                    raise NotImplementedError(f"Unsupported index mode({strip.index_mode})")
                remapped_indices = np.asarray(tri_list, np.uint32) + indices_id_offset
                material_indices.extend(np.full(len(tri_list), materials_offset))
                indices.extend(remapped_indices)
                indices_count += len(tri_list)
                vertex_count += mesh.vertex_count
                indices_id_offset += mesh.vertex_count
                indices_offset += len(tri_list)
                materials_offset += 1

            vertex_offset = 0
            global_vertex_data = {}

            mesh_data = bpy.data.meshes.new(model_name + "_DATA")
            mesh_obj = bpy.data.objects.new(model_name, mesh_data)

            for entry in model.models:
                if (hgp.materials[entry.material_id].unk_flags >> 6) & 1:
                    continue

                mat = create_material(AnimatedTexturesChunk(), mesh_obj, hgp.materials[entry.material_id],
                                      entry.material_id,
                                      tas_cache)
                mat["unk0"] = entry.unk_0
                mat["unk1"] = entry.unk_1
                mat["vertex_size"] = entry.vertex_size

                material = hgp.materials[entry.material_id]
                vertex_dtype = material.construct_vertex_dtype()
                vertex_block = hgp.vertex_buffers[entry.vertex_block_ids[0]]
                entry_vertex_data = vertex_block.read_vertices(vertex_dtype, entry.vertex_count)

                if "pos" not in global_vertex_data:
                    global_vertex_data["pos"] = np.zeros((vertex_count, 3), np.float32)
                vertex_slice = slice(vertex_offset, vertex_offset + entry.vertex_count)

                if material.packed_blend_weight:
                    blend_weights = entry_vertex_data["weights"].astype(np.float32) / 255
                    if "weights" not in global_vertex_data:
                        global_vertex_data["weights"] = np.zeros((vertex_count, 3), np.float32)
                    global_vertex_data["weights"][vertex_slice] = blend_weights[:, :3]

                if material.blend_weight:
                    blend_weights = entry_vertex_data["weights"]
                    if "weights" not in global_vertex_data:
                        global_vertex_data["weights"] = np.zeros((vertex_count, 2), np.float32)
                    global_vertex_data["weights"][vertex_slice] = blend_weights

                if material.packed_blend_indices:
                    blend_indices = entry_vertex_data["indices"].astype(np.uint32)
                    if "indices" not in global_vertex_data:
                        global_vertex_data["indices"] = np.zeros((vertex_count, 3), np.uint32)
                    assert len(entry.strips) == 1
                    for strip in entry.strips:
                        remap_table = np.asarray(strip.remap_table, np.uint32)
                        blend_indices = remap_table[blend_indices[:, :3]]
                    global_vertex_data["indices"][vertex_slice] = blend_indices

                if material.has_vcolors:
                    vertex_colors = np.asarray(entry_vertex_data["color"].copy(), np.float32) / 127
                    tmp = vertex_colors.copy()
                    vertex_colors[:, 0] = tmp[:, 2]
                    vertex_colors[:, 1] = tmp[:, 1]
                    vertex_colors[:, 2] = tmp[:, 0]
                    vertex_colors[:, 3] = tmp[:, 3]
                    if "color" not in global_vertex_data:
                        global_vertex_data["color"] = np.ones((vertex_count, 4), np.float32)
                    global_vertex_data["color"][vertex_slice] = vertex_colors

                if material.has_vcolors2:
                    vertex_colors = np.asarray(entry_vertex_data["color1"].copy(), np.float32) / 127
                    tmp = vertex_colors.copy()
                    vertex_colors[:, 0] = tmp[:, 2]
                    vertex_colors[:, 1] = tmp[:, 1]
                    vertex_colors[:, 2] = tmp[:, 0]
                    vertex_colors[:, 3] = tmp[:, 3]
                    if "color1" not in global_vertex_data:
                        global_vertex_data["color1"] = np.ones((vertex_count, 4), np.float32)
                    global_vertex_data["color1"][vertex_slice] = vertex_colors

                for uv_layer_id in range(material.uv_layer_count):
                    uv_name = f"UV{uv_layer_id}"
                    uv = entry_vertex_data[uv_name].copy()
                    uv[:, 1] = 1 - uv[:, 1]
                    if uv_name not in global_vertex_data:
                        global_vertex_data[uv_name] = np.ones((vertex_count, 2), np.float32)
                    global_vertex_data[uv_name][vertex_slice] = uv

                global_vertex_data["pos"][vertex_slice] = entry_vertex_data["pos"]

                vertex_offset += entry.vertex_count

            mesh_obj.parent = root
            mesh_data.from_pydata(global_vertex_data["pos"], [], indices)
            mesh_data.update()
            mesh_obj["entity_data"] = {}

            mesh_data.polygons.foreach_set('material_index', material_indices)

            vertex_indices = np.zeros((len(mesh_data.loops, )), dtype=np.uint32)
            mesh_data.loops.foreach_get('vertex_index', vertex_indices)
            if "color" in global_vertex_data:
                vertex_colors = mesh_data.vertex_colors.new(name="col")
                vertex_colors.data.foreach_set('color', global_vertex_data["color"][vertex_indices].ravel())
            if "color1" in global_vertex_data:
                vertex_colors = mesh_data.vertex_colors.new(name="col1")
                vertex_colors.data.foreach_set('color', global_vertex_data["color1"][vertex_indices].ravel())

            for uv_layer_id in range(8):
                uv_name = f"UV{uv_layer_id}"
                if uv_name in global_vertex_data:
                    uv_layer = mesh_data.uv_layers.new(name=uv_name)
                    uv_ = global_vertex_data[uv_name].copy()
                    uv_layer.data.foreach_set('uv', uv_[vertex_indices].flatten())

            if "weights" in global_vertex_data:
                bone_names = [bone.name for bone in hgp.bones]
                weight_groups = {bone: mesh_obj.vertex_groups.new(name=bone) for bone in bone_names}
                for n, (index_group, weight_group), in enumerate(
                    zip(global_vertex_data["indices"], global_vertex_data["weights"])):
                    for index, weight in zip(index_group, weight_group):
                        if weight > 0:
                            weight_groups[bone_names[index]].add([n], weight, 'REPLACE')
                modifier = mesh_obj.modifiers.new(type="ARMATURE", name="Armature")
                modifier.object = armature_obj
                mesh_obj.parent = armature_obj

            bpy.context.scene.collection.objects.link(mesh_obj)
