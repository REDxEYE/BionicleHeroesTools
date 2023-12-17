import math
import os
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

import bpy
from mathutils import Matrix, Vector, Euler
from .bpy_utils import add_material, get_or_create_collection
from .common import Vector4
from .file_utils import FileBuffer, Buffer
from .job import Job, SplineEditor
from .material_utils import clear_nodes, create_node, Nodes, connect_nodes, create_texture_node, \
    create_animated_texture_node
from .mesh_utils import unstripify
from .nup import NupModel, Container, Texture, Material, AnimatedTexture, Instance, Spec, Spline, TST0Chunk, \
    AnimatedTexturesChunk


def build_material(tas0: AnimatedTexturesChunk, material_id: int, mat, material: Material, animated_texture_path: Path):
    mat.use_nodes = True
    clear_nodes(mat)

    if material.texture_id1:
        create_texture_node(mat, bpy.data.images[f"tex_{material.texture_id1 - 1:04}.dds"])
    if material.texture_id2:
        create_texture_node(mat, bpy.data.images[f"tex_{material.texture_id2 - 1:04}.dds"])
    if material.texture_id3:
        create_texture_node(mat, bpy.data.images[f"tex_{material.texture_id3 - 1:04}.dds"])

    animated_texture_info: Optional[AnimatedTexture] = None
    if tas0:
        animated_texture_info = next(filter(lambda a: a.material_id == material_id, tas0), None)

    if animated_texture_info is not None and len(animated_texture_info.frames) > 1 and material.texture_id0:
        ati_index = tas0.index(animated_texture_info)
        tex_node = create_animated_texture_node(mat, animated_texture_path / f"{ati_index}_0000.dds",
                                                frame_count=animated_texture_info.frame_count - 1)
    elif material.texture_id0:
        image = bpy.data.images[f"tex_{material.texture_id0 - 1:04}.dds"]
        tex_node = create_texture_node(mat, image)
    else:
        tex_node = None

    output_node = create_node(mat, Nodes.ShaderNodeOutputMaterial)
    bsdf_node = create_node(mat, Nodes.ShaderNodeBsdfPrincipled)
    bsdf_node.inputs["Specular"].default_value = 0
    bsdf_node.inputs["Roughness"].default_value = 1
    connect_nodes(mat, bsdf_node.outputs[0], output_node.inputs[0])

    if material.transparency2 and tex_node:
        connect_nodes(mat, tex_node.outputs[1], bsdf_node.inputs["Alpha"])
        mat.blend_method = 'HASHED'
        mat.shadow_method = 'HASHED'

    if material.has_vcolors and tex_node:
        vertex_color = create_node(mat, Nodes.ShaderNodeVertexColor)
        mix = create_node(mat, Nodes.ShaderNodeMixRGB)
        mix.inputs[0].default_value = 1
        mix.blend_type = "MULTIPLY"
        connect_nodes(mat, vertex_color.outputs[0], mix.inputs[1])
        connect_nodes(mat, tex_node.outputs[0], mix.inputs[2])
        connect_nodes(mat, mix.outputs[0], bsdf_node.inputs["Base Color"])
    else:
        bsdf_node.inputs["Base Color"].default_value = material.color
    # if material.has_vcolors:
    #     vertex_color = create_node(mat, Nodes.ShaderNodeVertexColor)
    #     mix = create_node(mat, Nodes.ShaderNodeMixRGB)
    #     mix.inputs[0].default_value = 1
    #     mix.blend_type = "MULTIPLY"
    #     connect_nodes(mat, vertex_color.outputs[0], mix.inputs[1])
    #
    #     # if material.glow:
    #     #     if tex_node:
    #     #         connect_nodes(mat, tex_node.outputs[0], bsdf_node.inputs["Emission"])
    #     #     else:
    #     #         bsdf_node.inputs["Emission"].default_value = (0, 1, 1, 0)
    #     #     bsdf_node.inputs["Emission Strength"].default_value = 1
    #
    #
    #
    #     # if material.transparent:
    #     #     if material.ignore_valpha:
    #     #         if tex_node is not None:
    #     #             connect_nodes(mat, tex_node.outputs[1], bsdf_node.inputs["Alpha"])
    #     #     else:
    #     #         a_mix = create_node(mat, Nodes.ShaderNodeMath)
    #     #         a_mix.operation = "MULTIPLY"
    #     #         connect_nodes(mat, vertex_color.outputs[1], a_mix.inputs[0])
    #     #         if tex_node is not None:
    #     #             connect_nodes(mat, tex_node.outputs[1], a_mix.inputs[1])
    #     #         else:
    #     #             a_mix.inputs[1].default_value = 1.0
    #     #         connect_nodes(mat, a_mix.outputs[0], bsdf_node.inputs["Alpha"])
    #     if material.additive:
    #         if tex_node is not None:
    #             connect_nodes(mat, tex_node.outputs[0], bsdf_node.inputs["Alpha"])
    #
    #     if tex_node is not None:
    #         connect_nodes(mat, tex_node.outputs[0], mix.inputs[2])
    #     else:
    #         mix.inputs[2].default_value = (1.0, 1.0, 1.0, 1.0)
    #     connect_nodes(mat, mix.outputs[0], bsdf_node.inputs["Base Color"])
    # else:
    #     if tex_node is not None:
    #         connect_nodes(mat, tex_node.outputs[0], bsdf_node.inputs["Base Color"])
    #         if material.transparency2:
    #             connect_nodes(mat, tex_node.outputs[1], bsdf_node.inputs["Alpha"])
    #         elif material.additive:
    #             connect_nodes(mat, tex_node.outputs[0], bsdf_node.inputs["Alpha"])


def create_material(tas0: AnimatedTexturesChunk, obj, material_info: Material, material_id: int,
                    animated_texture_path: Path):
    mat = add_material(f"material_{material_id}", obj)
    if mat.get("loaded", False):
        return mat
    if 0:
        mat["transparency"] = (material_info.flags >> 0) & 1
        mat["b01"] = (material_info.flags >> 1) & 1
        mat["b02"] = (material_info.flags >> 2) & 1
        mat["b03"] = (material_info.flags >> 3) & 1
        mat["b04"] = (material_info.flags >> 4) & 1
        mat["b05"] = (material_info.flags >> 5) & 1
        mat["b06"] = (material_info.flags >> 6) & 1
        mat["b07"] = (material_info.flags >> 7) & 1
        mat["b08"] = (material_info.flags >> 8) & 1
        mat["b09"] = (material_info.flags >> 9) & 1
        mat["b10"] = (material_info.flags >> 10) & 1
        mat["b11"] = (material_info.flags >> 11) & 1
        mat["b12"] = (material_info.flags >> 12) & 1
        mat["b13"] = (material_info.flags >> 13) & 1
        mat["b14"] = (material_info.flags >> 14) & 1
        mat["b15"] = (material_info.flags >> 15) & 1
        mat["b16"] = (material_info.flags >> 16) & 1
        mat["vertex_lightmap0"] = (material_info.flags >> 17) & 1
        mat["vertex_lightmap1"] = (material_info.flags >> 18) & 1
        mat["b19"] = (material_info.flags >> 19) & 1
        mat["b20"] = (material_info.flags >> 20) & 1
        mat["b21"] = (material_info.flags >> 21) & 1
        mat["b22"] = (material_info.flags >> 22) & 1
        mat["b23"] = (material_info.flags >> 23) & 1
        mat["b24"] = (material_info.flags >> 24) & 1
        mat["b25"] = (material_info.flags >> 25) & 1
        mat["b26"] = (material_info.flags >> 26) & 1
        mat["b27"] = (material_info.flags >> 27) & 1
        mat["b28"] = (material_info.flags >> 28) & 1
        mat["b29"] = (material_info.flags >> 29) & 1
        mat["b30"] = (material_info.flags >> 30) & 1
        mat["b31"] = (material_info.flags >> 31) & 1
    if 1:
        mat["b00"] = (material_info.unk_flags >> 0) & 1
        mat["b01"] = (material_info.unk_flags >> 1) & 1
        mat["b02"] = (material_info.unk_flags >> 2) & 1
        mat["b03"] = (material_info.unk_flags >> 3) & 1
        mat["b04"] = (material_info.unk_flags >> 4) & 1
        mat["b05"] = (material_info.unk_flags >> 5) & 1
        mat["b06"] = (material_info.unk_flags >> 6) & 1
        mat["b07"] = (material_info.unk_flags >> 7) & 1
        mat["b08"] = (material_info.unk_flags >> 8) & 1
        mat["b09"] = (material_info.unk_flags >> 9) & 1
        mat["b10"] = (material_info.unk_flags >> 10) & 1
        mat["b11"] = (material_info.unk_flags >> 11) & 1
        mat["b12"] = (material_info.unk_flags >> 12) & 1
        mat["b13"] = (material_info.unk_flags >> 13) & 1
        mat["b14"] = (material_info.unk_flags >> 14) & 1
        mat["b15"] = (material_info.unk_flags >> 15) & 1
        mat["b16"] = (material_info.unk_flags >> 16) & 1
        mat["b17"] = (material_info.unk_flags >> 17) & 1
        mat["b18"] = (material_info.unk_flags >> 18) & 1
        mat["b19"] = (material_info.unk_flags >> 19) & 1
        mat["b20"] = (material_info.unk_flags >> 20) & 1
        mat["transparency2_b21"] = material_info.transparency2
        mat["b22"] = (material_info.unk_flags >> 22) & 1
        mat["b23"] = (material_info.unk_flags >> 23) & 1
        mat["b24"] = (material_info.unk_flags >> 24) & 1
        mat["b25"] = (material_info.unk_flags >> 25) & 1
        mat["b26"] = (material_info.unk_flags >> 26) & 1
        mat["b27"] = (material_info.unk_flags >> 27) & 1
        mat["b28"] = (material_info.unk_flags >> 28) & 1
        mat["b29"] = (material_info.unk_flags >> 29) & 1
        mat["b30"] = (material_info.unk_flags >> 30) & 1
        mat["b31"] = (material_info.unk_flags >> 31) & 1
    build_material(tas0, material_id, mat, material_info, animated_texture_path)
    mat["loaded"] = True
    return mat


def load_obj(nup: NupModel, mesh_info: Container, name, matrix: Optional[Matrix],
             parent_object: bpy.types.Object,
             custom_data: dict,
             animated_texture_path: Path):
    if mesh_info.models:
        vertex_count = 0
        indices_count = 0
        indices = []
        indices_id_offset = 0
        indices_offset = 0
        material_indices = []
        materials_offset = 0

        for entry in mesh_info.models:
            if (nup.ms00[entry.material_id].unk_flags >> 6) & 1:
                continue

            strip = entry.strips[0]
            index_block = nup.vbib.index_buffers[0]
            if strip.index_mode == 5:
                tri_list = unstripify(index_block.read_indices(strip.indices_offset, strip.indices_count))
            elif strip.index_mode == 4:
                tri_list = index_block.read_indices(strip.indices_offset, strip.indices_count)
            else:
                raise NotImplementedError(f"Unsupported index mode({strip.index_mode})")
            remapped_indices = np.asarray(tri_list, np.uint32) + indices_id_offset
            material_indices.extend(np.full(len(tri_list), entry.material_id))
            indices.extend(remapped_indices)
            indices_count += len(tri_list)
            vertex_count += entry.vertex_count
            indices_id_offset += entry.vertex_count
            indices_offset += len(tri_list)
            materials_offset += 1

        vertex_offset = 0
        global_vertex_data = {}

        mesh_data = bpy.data.meshes.new(name + "_DATA")
        mesh_obj = bpy.data.objects.new(name, mesh_data)

        materials = []
        for n, material in enumerate(nup.ms00):
            mat = create_material(AnimatedTexturesChunk(), mesh_obj, material, n, animated_texture_path)
            materials.append(mat)

        for entry in mesh_info.models:
            if (nup.ms00[entry.material_id].unk_flags >> 6) & 1:
                continue

            mat = materials[entry.material_id]

            mat["unk0"] = entry.unk_0
            mat["unk1"] = entry.unk_1
            mat["vertex_size"] = entry.vertex_size

            material = nup.ms00[entry.material_id]
            vertex_dtype = material.construct_vertex_dtype()
            vertex_block = nup.vbib.vertex_buffers[entry.vertex_block_ids[0]]
            entry_vertex_data = vertex_block.read_vertices(vertex_dtype, entry.vertex_count)

            if "pos" not in global_vertex_data:
                global_vertex_data["pos"] = np.zeros((vertex_count, 3), np.float32)

            if material.has_vcolors:
                vertex_colors = np.asarray(entry_vertex_data["color"].copy(), np.float32) / 127
                tmp = vertex_colors.copy()
                vertex_colors[:, 0] = tmp[:, 2]
                vertex_colors[:, 1] = tmp[:, 1]
                vertex_colors[:, 2] = tmp[:, 0]
                vertex_colors[:, 3] = tmp[:, 3]
                if "color" not in global_vertex_data:
                    global_vertex_data["color"] = np.ones((vertex_count, 4), np.float32)
                global_vertex_data["color"][vertex_offset:vertex_offset + entry.vertex_count] = vertex_colors

            if material.has_vcolors2:
                vertex_colors = np.asarray(entry_vertex_data["color1"].copy(), np.float32) / 127
                tmp = vertex_colors.copy()
                vertex_colors[:, 0] = tmp[:, 2]
                vertex_colors[:, 1] = tmp[:, 1]
                vertex_colors[:, 2] = tmp[:, 0]
                vertex_colors[:, 3] = tmp[:, 3]
                if "color1" not in global_vertex_data:
                    global_vertex_data["color1"] = np.ones((vertex_count, 4), np.float32)
                global_vertex_data["color1"][vertex_offset:vertex_offset + entry.vertex_count] = vertex_colors

            for uv_layer_id in range(material.uv_layer_count):
                uv_name = f"UV{uv_layer_id}"
                uv = entry_vertex_data[uv_name].copy()
                uv[:, 1] = 1 - uv[:, 1]
                if uv_name not in global_vertex_data:
                    global_vertex_data[uv_name] = np.ones((vertex_count, 2), np.float32)
                global_vertex_data[uv_name][vertex_offset:vertex_offset + entry.vertex_count] = uv

            global_vertex_data["pos"][vertex_offset:vertex_offset + entry.vertex_count] = entry_vertex_data["pos"]

            vertex_offset += entry.vertex_count

        mesh_obj.parent = parent_object
        mesh_data.from_pydata(global_vertex_data["pos"], [], indices)
        mesh_data.update()
        mesh_obj["entity_data"] = {}
        mesh_obj["entity_data"]["entity"] = custom_data

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

        if matrix is not None:
            mesh_obj.matrix_local = matrix
        return mesh_obj
    return None


def load_particle(nup: NupModel, object_info: Container, name: str, matrix: Optional[Matrix],
                  parent_object: bpy.types.Object,
                  custom_data: dict,
                  animated_texture_path: Path):
    objects = []
    obj = bpy.data.objects.new(name, None)
    obj.matrix_local = matrix
    obj.parent = parent_object
    obj["entity_data"] = {}
    obj["entity_data"]["entity"] = custom_data

    for n, entry in enumerate(object_info.particle_groups):
        for j, (unk, unk1) in enumerate(zip(entry.positions, entry.scale_and_color)):
            obj2 = bpy.data.objects.new(f"{name}_{n}_{j}", None)
            obj2.location = unk
            obj2.parent = obj
            obj2.empty_display_type = 'IMAGE'
            material = nup.ms00[entry.material_id]
            animated_texture_info: AnimatedTexture = next(
                filter(lambda a: a.material_id == entry.material_id, nup.tas0), None)

            if animated_texture_info is not None and len(
                animated_texture_info.frames) >= 1 and material.texture_id0:
                ati_index = nup.tas0.index(animated_texture_info)
                image = (bpy.data.images.get((animated_texture_path / f"{ati_index}_0000.dds").as_posix()) or
                         bpy.data.images.load((animated_texture_path / f"{ati_index}_0000.dds").as_posix()))
                obj2.data = image
                obj2.data.source = 'SEQUENCE'
                obj2.image_user.use_auto_refresh = True
                obj2.image_user.use_cyclic = True
                obj2.image_user.frame_duration = animated_texture_info.frame_count - 1
                obj2.image_user.frame_start = 0
            else:
                obj2.data = bpy.data.images.get(f"tex_{material.texture_id0 - 1}")
            obj2.scale[0] = unk1[0]
            obj2.scale[1] = unk1[1]
            obj2.use_empty_image_alpha = True
            obj2.color[0] = unk1[2] / 127
            obj2.color[1] = unk1[3] / 127
            obj2.color[2] = unk1[4] / 127
            obj2.color[3] = unk1[5] / 127

            objects.append(obj2)
    objects.append(obj)
    return objects


def load_inst(nup: NupModel, instance: Instance,
              name: str,
              texture_cache: Path,
              override_matrix: Optional[Matrix] = None,
              parent_collection: Optional[bpy.types.Collection] = None,
              parent_object: Optional[bpy.types.Object] = None,
              bbox_data: Optional[Tuple[Vector4, Tuple[Vector4, Vector4]]] = None):
    mesh_data = nup.obj0[(instance.mesh_id & 0x000FFFFF)]
    if not (mesh_data.models or mesh_data.particle_groups):
        print("Instance without geometry/billboard data")
        return []
    matrix = Matrix(np.transpose(instance.matrix))
    custom_data = {"inst_flags": instance.flags,
                   "inst_unk0": instance.unk0,
                   "inst_unk1": instance.unk1, }
    if mesh_data.models:
        object = load_obj(nup, mesh_data, name, override_matrix or matrix, parent_object, custom_data,
                          texture_cache)
        objects = [object]
    elif mesh_data.particle_groups:
        objects = load_particle(nup, mesh_data, name, override_matrix or matrix, parent_object, custom_data,
                                texture_cache)
    else:
        print(f"Unsupported type of Instance: {instance}")
        return []

    center, bbox = bbox_data
    bmin, bmax = bbox
    center = center
    bmin = Vector(bmin)
    bmax = Vector(bmax)
    scale = Vector(bmax - bmin) / 2
    e_dim = bpy.data.objects.new(f"{name}_BBOX", None)
    e_dim.empty_display_type = 'CUBE'
    e_dim.location = center
    e_dim.parent = objects[0]
    e_dim.matrix_world = ((override_matrix or matrix).inverted() @ Matrix.LocRotScale(center, None, scale))
    if parent_collection:
        parent_collection.objects.link(e_dim)
        for obj in objects:
            parent_collection.objects.link(obj)
    return objects


def prepare_animated_textures(nup: NupModel, cache_folder: Path):
    if nup.tas0:
        for anim_id, anim_tex in enumerate(nup.tas0):
            anim_tex: AnimatedTexture
            anim_name = nup.ntbl[anim_tex.name_offset]
            anim_other_name = nup.ntbl[anim_tex.other_name_offset]
            assert anim_name == anim_other_name
            for n, frame in enumerate(anim_tex.frames):
                tex = nup.tst0[frame]
                frame_name = f"{anim_id}_{n:04}.dds"
                with (cache_folder / frame_name).open("wb") as f:
                    f.write(tex.data)


def load_textures(tst0: TST0Chunk, cache_folder: Path):
    for i, tex in enumerate(tst0):
        if not tex.data:
            continue
        tex: Texture
        texture_name = f"tex_{i:04}.dds"
        with (cache_folder / texture_name).open("wb") as f:
            f.write(tex.data)

        image = bpy.data.images.load((cache_folder / texture_name).as_posix())
        image.use_fake_user = True
        image.alpha_mode = 'STRAIGHT'


def load_job(job: Job, parent_object: bpy.types.Object, parent_collection: bpy.types.Collection):
    possible_flags = set()
    if job is not None:
        spline_editor: Optional[SplineEditor] = next(filter(lambda a: a.name == "Splines", job.editors), None)
        if spline_editor is not None:
            for spline in spline_editor.splines.splines:
                points = []
                spline_points = []
                l_points = []

                for point in spline.points:
                    possible_flags.add(point[3])
                    l_points.append(point)

                    if point[3] != 0:
                        if len(l_points) == 1:
                            points.extend(l_points)
                        else:
                            spline_points.append(l_points)
                        l_points = []
                if l_points:
                    spline_points.append(l_points)
                if spline_points:
                    curve_data = bpy.data.curves.new(f"{spline.name}_DATA", 'CURVE')
                    curve_object = bpy.data.objects.new(spline.name, curve_data)
                    curve_data.dimensions = '3D'
                    props = {}
                    # for flag in InstFlags:
                    #     props[flag.name] = bool(spline.flags & flag.value)
                    curve_object["entity_data"] = {}
                    curve_object["entity_data"]["entity"] = props

                    curve_object.parent = parent_object

                    parent_collection.objects.link(curve_object)
                    for spline in spline_points:
                        bezier = curve_data.splines.new('BEZIER')
                        bezier.bezier_points.add(len(spline) - 1)
                        for i, point in enumerate(spline):
                            bezier.bezier_points[i].co = point[0]
                            bezier.bezier_points[i].handle_left = point[1]
                            bezier.bezier_points[i].handle_right = point[2]
                if points:
                    for point in points:
                        point_object = bpy.data.objects.new(spline.name, None)
                        point_object.location = point[0]
                        point_object.parent = parent_object
                        parent_collection.objects.link(point_object)
    print(possible_flags)


def load_spline(nup: NupModel, spline: Spline,
                parent_object: bpy.types.Object,
                parent_collection: bpy.types.Collection):
    name = nup.ntbl[spline.name_offset]
    curve_data = bpy.data.curves.new(f"{name}_DATA", 'CURVE')
    curve_object = bpy.data.objects.new(name, curve_data)
    curve_object.data.dimensions = '3D'

    parent_collection.objects.link(curve_object)

    nurbs = curve_data.splines.new('POLY')
    nurbs.points.add(len(spline.vertices) - 1)
    for i, point in enumerate(spline.vertices):
        nurbs.points[i].co = (*point, 1)
    curve_object.parent = parent_object


def import_nup_from_buffer(root_path: Path, nup_buffer: Buffer):
    tas_cache = (root_path / "TAS_CACHE")
    os.makedirs(tas_cache, exist_ok=True)
    nup = NupModel.from_buffer(nup_buffer)
    import_nup(nup, tas_cache)


def import_nup_from_path(nup_path: Path):
    job_path = nup_path.with_suffix(".job")
    tas_cache = (nup_path.parent / "TAS_CACHE")
    os.makedirs(tas_cache, exist_ok=True)
    if job_path.exists():
        job = Job.from_buffer(FileBuffer(job_path))
    else:
        job = None
    nup = NupModel.from_buffer(FileBuffer(nup_path))

    root, spline_collection = import_nup(nup, tas_cache)

    job_spline_collection = get_or_create_collection("JOB_SPLINES", spline_collection)
    load_job(job, root, job_spline_collection)


def import_nup(nup, tas_cache):
    prepare_animated_textures(nup, tas_cache)
    load_textures(nup.tst0, tas_cache)
    root = bpy.data.objects.new("ROOT", None)
    root.matrix_world = Euler((math.radians(90), 0, 0), "XYZ").to_matrix().to_4x4()
    bpy.context.scene.collection.objects.link(root)
    spec_collection = get_or_create_collection("SPEC", bpy.context.scene.collection)
    inst_collection = get_or_create_collection("INST", bpy.context.scene.collection)
    inst_to_spec_map = {spec.instance_id: spec for spec in nup.spec}
    for instance_id, instance in enumerate(nup.inst):
        if nup.bnds:
            bbox_data = (nup.bnds.centers[instance_id][:3],
                         (nup.bnds.bboxes[instance_id][0][:3], nup.bnds.bboxes[instance_id][1][:3]))
        else:
            bbox_data = None

        spec: Optional[Spec] = inst_to_spec_map.get(instance_id)
        if spec is None:
            parent_collection = inst_collection
            if instance.flags & 1:
                parent_collection = get_or_create_collection("INST_HIDDEN", inst_collection)
            elif not instance.flags & 32:
                parent_collection = get_or_create_collection("INST_STATIC", inst_collection)
            load_inst(nup, instance, f"INSTANCE_{instance_id}", tas_cache, None, parent_collection, root, bbox_data)
        else:
            parent_collection = spec_collection
            name = nup.ntbl[spec.name_offset]
            if "faceon" in name.lower():
                parent_collection = get_or_create_collection("SPEC_FACEON", spec_collection)
            else:
                if instance.flags & 1:
                    parent_collection = get_or_create_collection("SPEC_HIDDEN", spec_collection)
                elif not instance.flags & 32:
                    parent_collection = get_or_create_collection("SPEC_STATIC", spec_collection)
            matrix = Matrix(np.transpose(instance.matrix))
            load_inst(nup, instance, name, tas_cache, matrix, parent_collection, root, bbox_data)
    spline_collection = get_or_create_collection("SPLINES", bpy.context.scene.collection)
    sst_spline_collection = get_or_create_collection("SST0_SPLINES", spline_collection)
    for spline in nup.sst0:
        load_spline(nup, spline, root, sst_spline_collection)
    return root, spline_collection
