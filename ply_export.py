import bpy, struct, heapq
from bpy.app.translations import pgettext_tip as tip_
from os import path
from pathlib import Path

pack_B = struct.Struct('B').pack
pack_BBBB = struct.Struct('BBBB').pack
pack_H = struct.Struct('H').pack
pack_HHH = struct.Struct('HHH').pack
pack_I = struct.Struct('I').pack
pack_f = struct.Struct('f').pack
pack_ff = struct.Struct('ff').pack
pack_fff = struct.Struct('fff').pack

# Direct3D Flags
D3DFVF_XYZ = 0x02
D3DFVF_XYZB2 = 0x08
D3DFVF_NORMAL = 0x10
D3DFVF_TEX1 = 0x0100
D3DFVF_LASTBETA_UBYTE4 = 0x1000

MESH_FLAG_LIGHT     = 0b100
MESH_FLAG_SKINNED   = 0b10000
MESH_FLAG_MATERIAL  = 0b10000000000
MESH_FLAG_SUBSKIN   = 0b100000000000

def add_ext(name, ext):
    return name + (ext if not name.endswith(ext) else '')

def export(dir, operator, apply_unit_scale, use_mirror):
    unit_scale = 1
    if apply_unit_scale:
        if bpy.context.scene.unit_settings.system == 'METRIC':
            unit_scale = bpy.context.scene.unit_settings.scale_length * 20
        elif bpy.context.scene.unit_settings.system == 'IMPERIAL':
            unit_scale = bpy.context.scene.unit_settings.scale_length * 6.096

    objects = []

    with open(path.join(dir,add_ext(bpy.context.scene.name, '.txt')), 'w') as f:
        f.write('{Skeleton\n')
        def get_children(obj, level=1):
            f.write('\t'*level+f'{{bone "{obj.name}"\n')
            matrix = obj.matrix_basis.transposed()
            f.write('\t'*(level+1)+f'{{Matrix34\n')
            for i in range(4):
                f.write('\t'*(level+2)+f'{matrix[i][0]}\t{matrix[i][1]}\t{matrix[i][2]}\n')
            f.write('\t'*(level+1)+f'}}\n')
            if obj.data:
                if obj.data.id_type == 'MESH' and (not 'volume' in obj.data.keys()):
                    f.write('\t'*(level+1)+f'{{VolumeView "{add_ext(obj.data.name, ".ply")}"}}\n')
            objects.append(obj)
            for child in obj.children:
                get_children(child, level+1)
            f.write('\t'*level+f'}}\n')

        for obj in bpy.context.scene.objects:
            if obj.parent is None:
                get_children(obj)
        f.write('}')
    
    mesh_to_obj = {obj.data: obj for obj in objects}

    for mesh in bpy.data.meshes:
        try:
            if not mesh.users:
                continue
            mesh.calc_loop_triangles()

            loop_tris = mesh.loop_triangles
            edges_count = len(loop_tris)*3
            if edges_count > 0xffffffff: raise Exception(f"Mesh '{mesh.name}'s edges count ({edges_count}) exceeds the limit {0xffffffff}")
            vertices = mesh.vertices
            coords = [vertex.co * unit_scale for vertex in vertices]

            if 'volume' in mesh.keys():

                vertices_count = len(vertices)
                if vertices_count > 0xffffffff: raise Exception(f"Mesh '{mesh.name}''s vertices count ({vertices_count}) exceeds the limit {0xffffffff}")

                with open(path.join(dir,add_ext(mesh.name, '.vol')), 'w+b') as f:
                    f.write(b'EVLM')
                    f.write(b'VERT')
                    f.write(pack_I(vertices_count))
                    for co in coords:
                        f.write(pack_fff(co))

                    f.write(b'INDX')
                    f.write(pack_I(edges_count))
                    for tri in loop_tris:
                        f.write(pack_HHH(*tri.vertices))

                    f.write(b'SIDE')
                    f.write(pack_I(edges_count//3))
                    for tri in loop_tris:
                        f.write(pack_B(tri.material_index+1))

            else:

                loops_count = len(mesh.loops)
                if loops_count > 0xffffffff: raise Exception(f"Mesh '{mesh.name}'s loops/UVs count ({loops_count}) exceeds the limit {0xffffffff}")
                if not mesh.materials: raise Exception(f"Mesh '{mesh.name}' has no materials")
                
                obj = mesh_to_obj.get(mesh)
                has_skin = any(m.type == 'ARMATURE' for m in obj.modifiers)
                bones_count = len(obj.vertex_groups)
                if bones_count > 0xfe: raise Exception(f"Mesh '{mesh.name}'s vertex groups count ({bones_count}) exceeds the limit {0xfe}")

                with open(path.join(dir, add_ext(mesh.name, '.ply')), 'w+b') as f:
                    f.write(b'EPLY')

                    f.write(b'BNDS')
                    f.write(pack_fff(*obj.bound_box[0]))
                    f.write(pack_fff(*obj.bound_box[6]))

                    weights_count = 0
                    if has_skin:
                        f.write(b'SKIN')
                        weights_count = 2
                        f.write(pack_I(bones_count))
                        for bone in obj.vertex_groups:
                            f.write(pack_B(len(bone.name)))
                            f.write(bone.name.encode())

                    tri_start = 0
                    tris_by_mat_list = [[] for _ in mesh.materials]
                    for tri in loop_tris:
                        tris_by_mat_list[tri.material_index].append(tri)

                    for i in range(len(tris_by_mat_list)):
                        f.write(b'MESH')
                        f.write(pack_I(D3DFVF_NORMAL | D3DFVF_TEX1 | ((D3DFVF_XYZB2 | D3DFVF_LASTBETA_UBYTE4) if has_skin else D3DFVF_XYZ)))
                        f.write(pack_I(tri_start))
                        tri_count = len(tris_by_mat_list[i])
                        f.write(pack_I(tri_count))
                        tri_start += tri_count
                        f.write(pack_I(MESH_FLAG_LIGHT | MESH_FLAG_MATERIAL | (MESH_FLAG_SKINNED | MESH_FLAG_SUBSKIN if weights_count else 0)))
                        try:
                            material_name = mesh.materials[i].name
                        except:
                            material_name = ''
                        material_name = material_name + ('.mtl' if not material_name.endswith('.mtl') else '')
                        f.write(pack_B(len(material_name)))
                        f.write((material_name).encode())
                        if has_skin:
                            f.write(pack_H(bones_count+1))
                            f.write(struct.pack('B'*bones_count, *(i+1 for i in range(bones_count))))

                    f.write(b'VERT')
                    f.write(pack_I(loops_count))
                    f.write(pack_H(32+8*has_skin)) # 3*4 for position + 3*4 for normal + 2*4 for uv
                    f.write(b'\x07\x00') # don't know what is this
                    loops = mesh.loops
                    uvs = [uv.uv for uv in mesh.uv_layers.active.data]
                    if has_skin:
                        vertex_weights = [
                            [(g.weight, g.group+1) for g in heapq.nlargest(2, vertex.groups, key=lambda g: g.weight)]
                            for vertex in vertices
                        ]

                    for loop in loops:
                        f.write(pack_fff(*(coords[loop.vertex_index])))
                        if has_skin:
                            weights_list = vertex_weights[loop.vertex_index]
                            weights_list.extend([(0, 0)] * (4 - len(weights_list)))
                            try:
                                inv = 1 / (weights_list[0][0] + weights_list[1][0])
                            except:
                                inv = 1
                                print(weights_list)
                            f.write(pack_f(weights_list[0][0]*inv))
                            f.write(pack_BBBB(*(weight[1] for weight in weights_list)))
                        f.write(pack_fff(*loop.normal))
                        uv = uvs[loop.index]
                        #f.write(pack_ff(mesh.uv_layers[0].uv[loop.index].vector[0], 1-mesh.uv_layers[0].uv[loop.index].vector[1]))
                        f.write(pack_ff(uv[0], 1-uv[1]))

                    f.write(b'INDX')
                    f.write(pack_I(edges_count))
                    for tri_list in tris_by_mat_list:
                        for tri in tri_list:
                            if use_mirror:
                                f.write(pack_HHH(*tuple(tri.loops)[::-1]))
                            else:
                                f.write(pack_HHH(*tri.loops))

        except Exception as e:
            import traceback
            traceback.print_exc()
            operator.report({'ERROR'}, tip_(f"{e}"))
            return {'CANCELLED'}

    return {'FINISHED'}
