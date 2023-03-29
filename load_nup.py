import math
import os
from pathlib import Path
from typing import Optional

import numpy as np

import bpy
from mathutils import Matrix, Vector
from .bpy_utils import add_material, get_or_create_collection
from .file_utils import FileBuffer
from .job import Job, SplineEditor, InstFlags
from .material_utils import clear_nodes, create_node, Nodes, connect_nodes, create_texture_node, \
    create_animated_texture_node
from .mesh_utils import unstripify
from .nup import NupModel, Container, Texture, Material, AnimatedTexture, Instance, Spec


def build_material(nup: NupModel, material_id: int, mat, material: Material, animated_texture_path: Path):
    mat.use_nodes = True
    clear_nodes(mat)
    if material.transparent:
        mat.blend_method = 'HASHED'
        mat.shadow_method = 'HASHED'
    output_node = create_node(mat, Nodes.ShaderNodeOutputMaterial)
    bsdf_node = create_node(mat, Nodes.ShaderNodeBsdfPrincipled)
    bsdf_node.inputs["Specular"].default_value = 0
    bsdf_node.inputs["Roughness"].default_value = 1
    connect_nodes(mat, output_node.inputs[0], bsdf_node.outputs[0])
    if material.texture_id2:
        create_texture_node(mat, bpy.data.images[f"tex_{material.texture_id2 - 1:04}.dds"])
    if material.texture_id3:
        create_texture_node(mat, bpy.data.images[f"tex_{material.texture_id3 - 1:04}.dds"])

    animated_texture_info: Optional[AnimatedTexture] = None
    if nup.tas0:
        animated_texture_info = next(filter(lambda a: a.material_id == material_id, nup.tas0), None)

    if animated_texture_info is not None and len(animated_texture_info.frames) > 1 and material.texture_id1:
        ati_index = nup.tas0.index(animated_texture_info)
        tex_node = create_animated_texture_node(mat, animated_texture_path / f"{ati_index}_0000.dds",
                                                frame_count=animated_texture_info.frame_count - 1)
    elif material.texture_id1:
        image = bpy.data.images[f"tex_{material.texture_id1 - 1:04}.dds"]
        tex_node = create_texture_node(mat, image)
    else:
        tex_node = None

    if material.has_vcolors:
        vertex_color = create_node(mat, Nodes.ShaderNodeVertexColor)
        mix = create_node(mat, Nodes.ShaderNodeMixRGB)
        mix.inputs[0].default_value = 1
        mix.blend_type = "MULTIPLY"
        connect_nodes(mat, vertex_color.outputs[0], mix.inputs[1])

        # if material.glow:
        #     if tex_node:
        #         connect_nodes(mat, tex_node.outputs[0], bsdf_node.inputs["Emission"])
        #     else:
        #         bsdf_node.inputs["Emission"].default_value = (0, 1, 1, 0)
        #     bsdf_node.inputs["Emission Strength"].default_value = 1

        if material.transparent:
            if material.ignore_valpha:
                if tex_node is not None:
                    connect_nodes(mat, tex_node.outputs[1], bsdf_node.inputs["Alpha"])
            else:
                a_mix = create_node(mat, Nodes.ShaderNodeMath)
                a_mix.operation = "MULTIPLY"
                connect_nodes(mat, vertex_color.outputs[1], a_mix.inputs[0])
                if tex_node is not None:
                    connect_nodes(mat, tex_node.outputs[1], a_mix.inputs[1])
                else:
                    a_mix.inputs[1].default_value = 1.0
                connect_nodes(mat, a_mix.outputs[0], bsdf_node.inputs["Alpha"])
        elif material.additive:
            if tex_node is not None:
                connect_nodes(mat, tex_node.outputs[0], bsdf_node.inputs["Alpha"])

        if tex_node is not None:
            connect_nodes(mat, tex_node.outputs[0], mix.inputs[2])
        else:
            mix.inputs[2].default_value = (1.0, 1.0, 1.0, 1.0)
        connect_nodes(mat, mix.outputs[0], bsdf_node.inputs["Base Color"])
    else:
        if tex_node is not None:
            connect_nodes(mat, tex_node.outputs[0], bsdf_node.inputs["Base Color"])
            if material.transparent:
                connect_nodes(mat, tex_node.outputs[1], bsdf_node.inputs["Alpha"])
            elif material.additive:
                connect_nodes(mat, tex_node.outputs[0], bsdf_node.inputs["Alpha"])


def load_obj(nup: NupModel, mesh_info: Container, name, matrix: Optional[Matrix],
             parent_object: bpy.types.Object,
             custom_data: dict,
             animated_texture_path: Path):
    if mesh_info.entries:
        objects = []
        for entry in mesh_info.entries:
            model_name = f"{name}_{entry.material_id}"
            mesh_data = bpy.data.meshes.new(model_name + "_DATA")
            mesh_obj = bpy.data.objects.new(model_name, mesh_data)
            mesh_obj.parent = parent_object
            objects.append(mesh_obj)

            assert len(entry.vertex_block_ids) == 1
            assert len(entry.strips) == 1
            strip = entry.strips[0]
            vertex_block = nup.vbib.vertex_buffers[entry.vertex_block_ids[0]]
            index_block = nup.vbib.index_buffers[0]
            material = nup.ms00[entry.material_id]
            vertex_dtype = material.construct_vertex_dtype()
            if entry.vertex_size != 0:
                assert vertex_dtype.itemsize == entry.vertex_size
            indices = unstripify(index_block.read_indices(strip.indices_offset, strip.indices_count))
            vertex_data = vertex_block.read_vertices(vertex_dtype, entry.vertex_count)
            del index_block, vertex_block
            print(f"Mat {entry.material_id:04}: {material.flags:032b}")

            custom_data["vertex_size"] = entry.vertex_size
            custom_data["unk_0"] = entry.unk_0
            custom_data["unk_1"] = entry.unk_1
            custom_data["transparency"] = (material.flags >> 0) & 1
            custom_data["b01"] = (material.flags >> 1) & 1
            custom_data["b02"] = (material.flags >> 2) & 1
            custom_data["b03"] = (material.flags >> 3) & 1
            custom_data["b04"] = (material.flags >> 4) & 1
            custom_data["b05"] = (material.flags >> 5) & 1
            custom_data["b06"] = (material.flags >> 6) & 1
            custom_data["b07"] = (material.flags >> 7) & 1
            custom_data["b08"] = (material.flags >> 8) & 1
            custom_data["b09"] = (material.flags >> 9) & 1
            custom_data["b10"] = (material.flags >> 10) & 1
            custom_data["b11"] = (material.flags >> 11) & 1
            custom_data["b12"] = (material.flags >> 12) & 1
            custom_data["b13"] = (material.flags >> 13) & 1
            custom_data["b14"] = (material.flags >> 14) & 1
            custom_data["b15"] = (material.flags >> 15) & 1
            custom_data["b16"] = (material.flags >> 16) & 1
            custom_data["vertex_lightmap0"] = (material.flags >> 17) & 1
            custom_data["vertex_lightmap1"] = (material.flags >> 18) & 1
            custom_data["b19"] = (material.flags >> 19) & 1
            custom_data["b20"] = (material.flags >> 20) & 1
            custom_data["b21"] = (material.flags >> 21) & 1
            custom_data["b22"] = (material.flags >> 22) & 1
            custom_data["b23"] = (material.flags >> 23) & 1
            custom_data["b24"] = (material.flags >> 24) & 1
            custom_data["b25"] = (material.flags >> 25) & 1
            custom_data["b26"] = (material.flags >> 26) & 1
            custom_data["b27"] = (material.flags >> 27) & 1
            custom_data["b28"] = (material.flags >> 28) & 1
            custom_data["b29"] = (material.flags >> 29) & 1
            custom_data["b30"] = (material.flags >> 30) & 1
            custom_data["b31"] = (material.flags >> 31) & 1
            custom_data["id"] = entry.material_id
            mesh_data.from_pydata(vertex_data["pos"], [], indices)
            mesh_data.update()

            vertex_indices = np.zeros((len(mesh_data.loops, )), dtype=np.uint32)
            mesh_data.loops.foreach_get('vertex_index', vertex_indices)

            if material.has_vcolors:
                vertex_colors = mesh_data.vertex_colors.new(name="col")
                vertex_colors_data = vertex_colors.data
                vertex_colors = np.asarray(vertex_data["color"].copy(), np.float32) / 127
                tmp = vertex_colors.copy()
                vertex_colors[:, 0] = tmp[:, 2]
                vertex_colors[:, 1] = tmp[:, 1]
                vertex_colors[:, 2] = tmp[:, 0]
                vertex_colors[:, 3] = tmp[:, 3]

                vertex_colors_data.foreach_set('color', vertex_colors[vertex_indices].ravel())
            if material.has_vcolors2:
                vertex_colors = mesh_data.vertex_colors.new(name="col1")
                vertex_colors_data = vertex_colors.data
                vertex_colors = np.asarray(vertex_data["color1"].copy(), np.float32) / 127
                tmp = vertex_colors.copy()
                vertex_colors[:, 0] = tmp[:, 2]
                vertex_colors[:, 1] = tmp[:, 1]
                vertex_colors[:, 2] = tmp[:, 0]
                vertex_colors[:, 3] = tmp[:, 3]

                vertex_colors_data.foreach_set('color', vertex_colors[vertex_indices].ravel())
            # if normal_format:
            #     norm_data = vertex_data["normal"]
            #     if normal_format == 2:
            #         norm_data = norm_data.astype(np.float32) / 255
            #     else:
            #         norm_data = norm_data
            #     mesh_data.polygons.foreach_set("use_smooth", np.ones(len(mesh_data.polygons), np.uint32))
            #     mesh_data.normals_split_custom_set_from_vertices(norm_data[:, :3])
            #     mesh_data.use_auto_smooth = True
            for uv_layer_id in range(material.uv_layer_count):
                uv_layer = mesh_data.uv_layers.new(name=f"UV{uv_layer_id}")
                uv_ = vertex_data[f"uv{uv_layer_id}"].copy()
                uv_[:, 1] = 1 - uv_[:, 1]
                uv_layer.data.foreach_set('uv', uv_[vertex_indices].flatten())
            if matrix is not None:
                mesh_obj.matrix_local = matrix
            mesh_obj["entity_data"] = {}
            mesh_obj["entity_data"]["entity"] = custom_data

            mat = add_material(f"material_{entry.material_id}", mesh_obj)
            build_material(nup, entry.material_id, mat, material, animated_texture_path)
        return objects
    return []


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

    for n, entry in enumerate(object_info.entries_v2):
        for j, (unk, unk1) in enumerate(zip(entry.unk_vec0, entry.unk_vec1)):
            obj2 = bpy.data.objects.new(f"{name}_{n}_{j}", None)
            obj2.location = unk
            obj2.parent = obj
            obj2.empty_display_type = 'IMAGE'
            material = nup.ms00[entry.material_id]
            animated_texture_info: AnimatedTexture = next(
                filter(lambda a: a.material_id == entry.material_id, nup.tas0), None)

            if animated_texture_info is not None and len(
                animated_texture_info.frames) >= 1 and material.texture_id1:
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
                obj2.data = bpy.data.images.get(f"tex_{material.texture_id1 - 1}")
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
              parent_object: Optional[bpy.types.Object] = None):
    if instance.mesh_id > len(nup.obj0):
        mesh_id = instance.mesh_id & 0x000FFFFF
    else:
        mesh_id = instance.mesh_id
    mesh_data = nup.obj0[mesh_id]
    if not (mesh_data.entries or mesh_data.entries_v2):
        print("Instance without geometry/billboard data")
        return []
    mesh_data = nup.obj0[mesh_id]
    matrix = Matrix(np.transpose(instance.matrix))
    custom_data = {"inst_flags": instance.flags,
                   "inst_unk0": instance.unk0,
                   "inst_unk1": instance.unk1, }
    if mesh_data.entries:
        objects = load_obj(nup, mesh_data, name, override_matrix or matrix, parent_object, custom_data,
                           texture_cache)
    elif mesh_data.entries_v2:
        objects = load_particle(nup, mesh_data, name, override_matrix or matrix, parent_object, custom_data,
                                texture_cache)
    else:
        print(f"Unsupported type of Instance: {instance}")
        return []
    if parent_collection:
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


def load_textures(nup: NupModel, cache_folder: Path):
    for i, tex in enumerate(nup.tst0):
        tex: Texture
        texture_name = f"tex_{i:04}.dds"
        with (cache_folder / texture_name).open("wb") as f:
            f.write(tex.data)

        image = bpy.data.images.load((cache_folder / texture_name).as_posix())
        image.use_fake_user = True
        image.alpha_mode = 'STRAIGHT'


def load_job(job: Job, parent_object: bpy.types.Object):
    if job is not None:
        spline_editor: Optional[SplineEditor] = next(filter(lambda a: a.name == "Splines", job.editors), None)
        if spline_editor is not None:
            for spline in spline_editor.splines.splines:
                curve_data = bpy.data.curves.new(f"{spline.name}_DATA", 'CURVE')
                curve_object = bpy.data.objects.new(spline.name, curve_data)
                curve_object.data.dimensions = '3D'
                props = {}
                for flag in InstFlags:
                    props[flag.name] = bool(spline.flags & flag.value)
                curve_object["entity_data"] = {}
                curve_object["entity_data"]["entity"] = props

                curve_object.parent = parent_object

                bpy.context.scene.collection.objects.link(curve_object)
                bezier = curve_data.splines.new('BEZIER')
                initial_point = spline.points.pop(0)
                bezier.bezier_points[0].co = initial_point[0]
                bezier.bezier_points[0].handle_left = initial_point[1]
                bezier.bezier_points[0].handle_right = initial_point[2]
                new = False
                counter = 0
                if initial_point[3] != 0:
                    bezier = curve_data.splines.new('BEZIER')
                    new = True
                    counter = 0
                for point_id, point in enumerate(spline.points):
                    if not new:
                        bezier.bezier_points.add(1)
                        counter += 1
                    else:
                        new = False
                    bezier.bezier_points[counter].co = point[0]
                    bezier.bezier_points[counter].handle_left = point[1]
                    bezier.bezier_points[counter].handle_right = point[2]
                    if point[3] != 0:
                        bezier = curve_data.splines.new('BEZIER')
                        new = True
                        counter = 0


def import_nup_from_path(nup_path: Path):
    job_path = nup_path.with_suffix(".job")
    tas_cache = (nup_path.parent / "TAS_CACHE")
    os.makedirs(tas_cache, exist_ok=True)
    if job_path.exists():
        job = Job.from_buffer(FileBuffer(job_path))
    else:
        job = None
    nup = NupModel.from_buffer(FileBuffer(nup_path))

    prepare_animated_textures(nup, tas_cache)
    load_textures(nup, tas_cache)

    root = bpy.data.objects.new("ROOT", None)
    root.rotation_mode = "XYZ"
    root.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.collection.objects.link(root)
    load_job(job, root)

    spec_collection = get_or_create_collection("SPEC", bpy.context.scene.collection)
    inst_collection = get_or_create_collection("INST", bpy.context.scene.collection)
    inst_to_spec_map = {spec.instance_id: spec for spec in nup.spec}
    for instance_id, instance in enumerate(nup.inst):
        spec: Optional[Spec] = inst_to_spec_map.get(instance_id)
        if spec is None:
            parent_collection = inst_collection
            if instance.flags & 1:
                parent_collection = get_or_create_collection("INST_HIDDEN", inst_collection)
            elif not instance.flags & 32:
                parent_collection = get_or_create_collection("INST_STATIC", inst_collection)
            load_inst(nup, instance, f"INSTANCE_{instance_id}", tas_cache, None, parent_collection, root)
        else:
            parent_collection = spec_collection
            if instance.flags & 1:
                parent_collection = get_or_create_collection("SPEC_HIDDEN", spec_collection)
            elif not instance.flags & 32:
                parent_collection = get_or_create_collection("SPEC_STATIC", spec_collection)
            matrix = Matrix(np.transpose(instance.matrix))
            load_inst(nup, instance, nup.ntbl[spec.name_offset], tas_cache, matrix, parent_collection, root)
