import tkinter as tk
from tkinter import filedialog
import bpy
import os
class FbxImporter:
    def __init__(self, master):
        self.master = master
        self.master.title("FBX Importer")
        # Select Model Button
        self.model_button = tk.Button(master, text="Select Model", command=self.select_model)
        self.model_button.pack()      
        # Import Model Button
        self.import_button = tk.Button(master, text="Import Model", command=self.import_model)
        self.import_button.pack()
        # Set default file paths
        self.model_path = ""        
    def select_model(self):
        self.model_path = filedialog.askopenfilename(filetypes=[("FBX Files", "*.fbx")])
    def import_model(self):
        if self.model_path :
            new_scene = bpy.data.scenes.new("My New Scene")
            bpy.context.window.scene = new_scene
            # Clear the scene
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete()
            # Import model
            bpy.ops.import_scene.fbx(filepath=self.model_path)
            # Select the imported object and make it active
            imported_objects = bpy.context.selected_objects
            if len(imported_objects) > 0:
                bpy.context.view_layer.objects.active = imported_objects[0]
            # Apply WeightedNormal
            bpy.ops.object.shade_smooth()
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
            bpy.ops.mesh.customdata_custom_splitnormals_clear()            
            # Set Auto Smooth
            bpy.context.object.data.use_auto_smooth = True
            bpy.context.object.data.auto_smooth_angle = 1.15192  # 66 degrees in radians           
            # Rename object
            obj_name = os.path.splitext(os.path.basename(self.model_path))[0]
            bpy.context.active_object.name = obj_name + "_high"
            high_obj = bpy.context.active_object
            high_obj.name = obj_name + "_high"
            high_obj_name = obj_name + "_high"
            # Duplicate object
            bpy.ops.object.duplicate()
            low_obj_name = obj_name + "_low"
            low_obj = bpy.context.active_object
            low_obj.name = low_obj_name
            ## Apply Remesh modifier                       
            remesh_mod = low_obj.modifiers.new(name="Remesh", type='REMESH')
            remesh_mod.mode= 'VOXEL'
            remesh_mod.voxel_size =0.05                                    
            remesh_mod.use_smooth_shade = True # Add this line to enable smooth shading
            bpy.ops.object.modifier_apply(modifier="Remesh")
            # 創建 Decimate Modifier            
            low_obj = bpy.context.active_object                    
            target_faces = 10000        
            original_faces = len(low_obj.data.polygons) 
            print("Original faces:", original_faces)                        
            ratio = target_faces  / original_faces            
            decimate_mod = low_obj.modifiers.new("Decimate", 'DECIMATE')
            decimate_mod.decimate_type = 'COLLAPSE'
            # 設置簡化比例
            decimate_mod.ratio = ratio         
            print("Decimate modifier created with ratio:", decimate_mod.ratio)        
            bpy.ops.object.modifier_apply(modifier=decimate_mod.name)
            # Smart UV project
            bpy.ops.object.select_all(action='DESELECT')
            low_obj.select_set(True)
            bpy.ops.object.mode_set(mode='EDIT')                       
            bpy.ops.uv.smart_project(angle_limit=66, island_margin=0,correct_aspect=True)
            bpy.ops.uv.select_all(action='SELECT') 
            bpy.ops.uv.smart_project(angle_limit=66, island_margin=0,correct_aspect=True)           
            bpy.ops.object.mode_set(mode='OBJECT')
            low_obj = bpy.data.objects[low_obj_name]            
            
            bpy.context.scene.render.engine = 'CYCLES'          
            # 新建一个材质球并赋予 low_obj。
            low_mat = bpy.data.materials.new(name='low_mat')
            low_obj.data.materials.clear() # 删除模型的所有材质
            low_obj.data.materials.append(low_mat) # 将 low_mat 赋值给模型的唯一材质
            low_mat.use_nodes = True
            low_tree = low_mat.node_tree
            nodes = low_tree.nodes        
            principled_node = nodes.new('ShaderNodeBsdfPrincipled')            
            principled_node.location = (-300, 0)           
            links = low_tree.links
            output_node = nodes.get('Material Output')
            bsdf_input = output_node.inputs['Surface']
            links.new(principled_node.outputs['BSDF'], bsdf_input)
            
            

            # 添加 Normal 贴图节点
            norm_map_name = obj_name + "_normal"
            normal_map_node = nodes.new(type='ShaderNodeNormalMap')
            normal_map_node.label = 'Normal'
            normal_img_node = nodes.new(type='ShaderNodeTexImage')
            normal_img_node.image = bpy.data.images.new(norm_map_name, width=1024, height=1024)
            normal_img_node.label = 'Normal Map'
            links.new(normal_img_node.outputs['Color'], normal_map_node.inputs['Color'])            
            links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])          
            uv_node = nodes.new(type='ShaderNodeUVMap')
            uv_node.uv_map = "UVMap"
            links.new(uv_node.outputs['UV'], normal_img_node.inputs['Vector'])
            links.new(normal_img_node.outputs['Color'], normal_map_node.inputs['Color'])
            links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])
            
            # 选择要烘焙的高模和低模
            high_obj = bpy.data.objects[high_obj_name]
            low_obj = bpy.data.objects[low_obj_name]
            
            # 选择 high_obj 并同时选择 low_obj
            bpy.context.view_layer.objects.active = low_obj
            bpy.ops.object.select_all(action='DESELECT')
            high_obj.select_set(True)
            low_obj.select_set(True)

            #要選擇 low_mat 材質球中的 normal_img_node.image 
            low_mat = bpy.data.materials["low_mat"]
            normal_img_node = low_mat.node_tree.nodes.get("Normal Map").inputs['Color'].links[0].from_node

           # Set up bake settings
            print("Baking NORMAL...")
            bpy.context.scene.cycles.bake_type = ('NORMAL')
            bpy.context.scene.render.use_file_extension = True
            bpy.context.scene.render.bake.use_selected_to_active = True
            bpy.context.scene.render.bake_margin = 16
            bpy.context.scene.render.bake.use_cage = False
            bpy.context.scene.render.bake.cage_extrusion = 0.25       
            
            
            
            # Start bake
            bpy.ops.object.bake(
                type='NORMAL',
                use_clear=True,
                use_selected_to_active=True,                
            )

            # Save  Normal Maps
            obj_name = os.path.splitext(os.path.basename(self.model_path))[0]
            norm_img_dir = os.path.dirname(self.model_path)
            norm_map_name = obj_name + "_normal.png"
            norm_map_path = os.path.join(norm_img_dir, norm_map_name)            
            normal_img_node.image.save_render(filepath=norm_map_path)
            print("save_NORMAL_map_OK...")

            #清除low_mat
            bpy.data.materials.remove(low_mat)
            low_mat = bpy.data.materials.new(name='low_mat')
            low_obj.data.materials.clear() # 删除模型的所有材质
            low_obj.data.materials.append(low_mat) # 将 low_mat 赋值给模型的唯一材质
            low_mat.use_nodes = True
            low_tree = low_mat.node_tree
            nodes = low_tree.nodes
                  
            principled_node = nodes.new('ShaderNodeBsdfPrincipled')            
            principled_node.location = (-300, 0)
            links = low_tree.links
            output_node = nodes.get('Material Output')
            bsdf_input = output_node.inputs['Surface']
            links.new(principled_node.outputs['BSDF'], bsdf_input)          
    
            # 添加 Diffuse 贴图节点                      
            diff_map_name = obj_name + "_diffuse"
            diffuse_tex = nodes.new(type='ShaderNodeTexImage')
            diffuse_tex.image = bpy.data.images.new(diff_map_name, width=1024, height=1024)            
            diffuse_tex.label = 'Diffuse Map'
            links.new(diffuse_tex.outputs['Color'], principled_node.inputs['Base Color'])     
            uv_node = nodes.new(type='ShaderNodeUVMap')
            uv_node.uv_map = "UVMap"
            links.new(uv_node.outputs['UV'], diffuse_tex.inputs['Vector'])         
            # 选择 high_obj 并同时选择 low_obj
            bpy.context.view_layer.objects.active = low_obj
            bpy.ops.object.select_all(action='DESELECT')
            high_obj.select_set(True)
            low_obj.select_set(True)            
            # 选择 low_mat 材质球中的 Diffuse Map            
            low_mat = bpy.data.materials["low_mat"]
            diffuse_tex = nodes.get("Diffuse Map")          
            # Set up bake settings
            print("Baking Diffuse...")
            bpy.context.scene.cycles.bake_type = ('DIFFUSE')
            bpy.context.scene.render.bake.use_pass_direct = False
            bpy.context.scene.render.bake.use_pass_indirect = False
            bpy.context.scene.render.bake.use_pass_color = True
            bpy.context.scene.render.use_file_extension = True
            bpy.context.scene.render.bake.use_selected_to_active = True
            bpy.context.scene.render.bake_margin = 16
            bpy.context.scene.render.bake.use_cage = False
            bpy.context.scene.render.bake.cage_extrusion = 0.25                                     
            # Start bake
            bpy.ops.object.bake(
                type='DIFFUSE',
                use_clear=True,
                use_selected_to_active=True,                
            )
            
            diffuse_img_dir = os.path.dirname(self.model_path)                       
            diffuse_map_name = obj_name + "_diffuse.png"
            diffuse_map_path = os.path.join(diffuse_img_dir, diffuse_map_name) 
            bpy.data.images[diff_map_name].save_render(diffuse_map_path)                      
            
            print("save_diffuse_map_OK...")
            #重新創建賦予normal+diffuse到low_mat
            #清除low_mat

            bpy.data.materials.remove(low_mat)
            low_mat = bpy.data.materials.new(name='low_mat')
            low_obj.data.materials.clear() # 删除模型的所有材质
            low_obj.data.materials.append(low_mat) # 将 low_mat 赋值给模型的唯一材质
            low_mat.use_nodes = True
            low_tree = low_mat.node_tree
            nodes = low_tree.nodes
            principled_node = nodes.new('ShaderNodeBsdfPrincipled')            
            principled_node.location = (-300, 0)

            # 连接Principled BSDF节点到Material Output节点
            links = low_tree.links
            output_node = nodes.get('Material Output')
            bsdf_input = output_node.inputs['Surface']
            links.new(principled_node.outputs['BSDF'], bsdf_input)

            norm_map_path = os.path.join(norm_img_dir, norm_map_name)
            normal_map_node = nodes.new(type='ShaderNodeNormalMap')
            normal_map_node.label = 'Normal'            
            normal_img_node = nodes.new(type='ShaderNodeTexImage')            
            normal_img_node.label = 'Normal Map'         
            links.new(normal_img_node.outputs['Color'], normal_map_node.inputs['Color'])            
            links.new(normal_map_node.outputs['Normal'], principled_node.inputs['Normal'])
            normal_img_node.image=bpy.data.images.load(norm_map_path)

            diffuse_map_path = os.path.join(diffuse_img_dir, diffuse_map_name) 
            diffuse_tex = nodes.new(type='ShaderNodeTexImage')
            diffuse_tex.label = 'Diffuse Map'
            links.new(diffuse_tex.outputs['Color'], principled_node.inputs['Base Color'])
            diffuse_tex.image = bpy.data.images.load(diffuse_map_path)       
            print("normal+diffuse_in_low_mat")
            bpy.context.view_layer.objects.active = low_obj
            low_obj_name = obj_name + "_low"
            low_obj = bpy.data.objects[low_obj_name]            
            fbx_output_path =os.path.dirname(self.model_path)
            fbx_output_file =low_obj_name+".fbx"
            fbx_output_full_path =os.path.join(fbx_output_path, fbx_output_file)
            bpy.ops.export_scene.fbx(filepath=fbx_output_full_path) 
            # Save blend file
            blender_file_path=os.path.dirname(self.model_path)
            blender_file_name =low_obj_name+".blend"
            blender_file_full_path =os.path.join(blender_file_path,blender_file_name)
            bpy.ops.wm.save_as_mainfile(filepath= blender_file_full_path)
            self.master.destroy()
        else:
            tk.messagebox.showerror("Error", "Please select a model.")

if __name__ == '__main__':
    root = tk.Tk()
    importer = FbxImporter(root)
    root.mainloop()
