import bpy, struct
from bpy.app.translations import pgettext_tip as tip_
from os import path
from pathlib import Path

# Direct3D Flags
D3DFVF_XYZ = 0x02
D3DFVF_NORMAL = 0x10
D3DFVF_TEX1 = 0x0100

MESH_FLAG_LIGHT     = 0b100
MESH_FLAG_MATERIAL  = 0b10000000000

unit_scale = 1
if bpy.context.scene.unit_settings.system == 'METRIC':
    unit_scale = bpy.context.scene.unit_settings.scale_length * 20
elif bpy.context.scene.unit_settings.system == 'IMPERIAL':
    unit_scale = bpy.context.scene.unit_settings.scale_length * 6.096

def multiply_scale(x):
    return x*unit_scale

def export(dir, operator):
    for mesh in bpy.data.meshes:
        try:
            if not mesh.users:
                continue
            mesh.calc_loop_triangles()
            if 'volume' in mesh.keys():
                with open(path.join(dir,Path(mesh.name).with_suffix('.vol')), 'w+b') as f:
                    f.write(b'EVLM')
                    f.write(b'VERT')
                    f.write(struct.pack('I', len(mesh.vertices)))
                    for vertex in mesh.vertices:
                        f.write(struct.pack('fff', *map(multiply_scale, (vertex.co))))

                    f.write(b'INDX')
                    edges_count = len(mesh.loop_triangles)*3
                    f.write(struct.pack('I', edges_count))
                    for tri in mesh.loop_triangles:
                        f.write(struct.pack('HHH', *tri.vertices))

                    f.write(b'SIDE')
                    f.write(struct.pack('I', len(mesh.loop_triangles)))
                    for tri in mesh.loop_triangles:
                        f.write(struct.pack('B', tri.material_index+1))

            else:
                with open(path.join(dir,Path(mesh.name).with_suffix('.ply')), 'w+b') as f:
                    f.write(b'EPLY')
                    f.write(b'BNDS')
                    f.write(struct.pack('ffffff', *map(multiply_scale, (
                        min(vertex.co.x for vertex in mesh.vertices),
                        min(vertex.co.y for vertex in mesh.vertices),
                        min(vertex.co.z for vertex in mesh.vertices),
                        max(vertex.co.x for vertex in mesh.vertices),
                        max(vertex.co.y for vertex in mesh.vertices),
                        max(vertex.co.z for vertex in mesh.vertices),
                    ))))

                    if not mesh.materials:
                        material = bpy.data.materials.new('Material')
                        mesh.materials.append(material)

                    tri_start = 0
                    for i, material in enumerate(mesh.materials):
                        f.write(b'MESH')
                        f.write(struct.pack('I', D3DFVF_XYZ | D3DFVF_NORMAL | D3DFVF_TEX1))
                        f.write(struct.pack('I', tri_start))
                        tri_count = len(tuple(1 for tri in mesh.loop_triangles if tri.material_index == i))
                        f.write(struct.pack('I', tri_count))
                        tri_start += tri_count
                        f.write(struct.pack('I', MESH_FLAG_LIGHT | MESH_FLAG_MATERIAL))
                        f.write(struct.pack('B', len(f"{material.name}.mtl")))
                        f.write(f"{material.name}.mtl".encode())

                    f.write(b'VERT')
                    f.write(struct.pack('I', len(mesh.loops)))
                    f.write(struct.pack('H', 32)) # 3*4 for position + 3*4 for normal + 2*4 for uv
                    f.write(struct.pack('H', 7))
                    for loop in mesh.loops:
                        f.write(struct.pack('fff', *map(multiply_scale, (mesh.vertices[loop.vertex_index].co))))
                        f.write(struct.pack('fff', *loop.normal))
                        f.write(struct.pack('ff', mesh.uv_layers[0].uv[loop.index].vector[0], 1-mesh.uv_layers[0].uv[loop.index].vector[1]))

                    f.write(b'INDX')
                    edges_count = len(mesh.loop_triangles)*3
                    f.write(struct.pack('I', edges_count))
                    for i in range(len(mesh.materials)):
                        for tri in mesh.loop_triangles:
                            if tri.material_index == i:
                                f.write(struct.pack('HHH', *tri.loops))

        except Exception as e:
            import traceback
            traceback.print_exc()
            operator.report({'ERROR'}, tip_(f"{e}"))
            return {'CANCELLED'}

    return {'FINISHED'}