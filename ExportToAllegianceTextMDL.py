import bpy
import operator
import shutil

bl_info = {
    "name": "ALLEGIANCE MDL",
    "description": "Allegiance MDL Exporter (.mdl)",
    "author": "Austin Harris",
    "version": (0, 8, 0),
    "blender": (2, 6, 3),
    "location": "File > Export > Allegiance (.mdl)",
    "warning": "", # used for warning icon and text in addons panel
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.5/Py/"
                "Scripts/My_Script",
    "tracker_url": "http://projects.blender.org/tracker/index.php?"
                   "func=detail&aid=<number>",
    "category": "Import-Export"}

def adduvdata(indicies,vertidx,uvsdic,obverticies,verticies,uvpoint):
	# if we have already stored this vert, then
	# we have an additonal UV data for it
	# we will need to make a copy of it so we can
	# store the UV with it
	# which means we will also have to mess with the indicies
    if vertidx in uvsdic:  
        # copy the vertex, and update the uv to reference it
        copy = ', '.join([', '.join(map('{:20.20f}'.format,obverticies[vertidx].co)) , ', '.join(map('{:20.20f}'.format,obverticies[vertidx].normal)) ]) 
        verticies.append( copy) # copy
        vertidx = verticies.index(copy) # determine new idx
    verticies[vertidx] =', '.join([ verticies[vertidx] ,', '.join( map('{:20.20f}'.format,  [uvpoint[0],1-uvpoint[1]]))]) # 1-uvpoint[1] invert the UV-Y component
    uvsdic[vertidx] = 1
    indicies += [vertidx]

def textureGeo(ob,filename): # returns str
    strs = []
    strs.append('TextureGeo(\n')
    strs.append('MeshGeo([') #Format: x,y,z,nx,ny,nz,uvx,uvy
        # uvx, uvy
    idx = []
    verticies = []
    lines = []
    uvsdic = {}
    for vertidx, vert in enumerate(ob.vertices):
        newvert = ', '.join([', '.join(map('{:20.20f}'.format,vert.co)) , ', '.join(map('{:20.20f}'.format,vert.normal)) ])
        verticies.append( newvert )# , ', '.join(map(str,uvsdic[vertidx]))
    for face in ob.polygons:
        indicies = []
       
        for loop_index in range(face.loop_start, face.loop_start + face.loop_total):
            vertidx = ob.loops[loop_index].vertex_index
            adduvdata(indicies,vertidx,uvsdic,ob.vertices,verticies,ob.uv_layers.active.data[loop_index].uv)

        # invert indicies order for left handed system
        idx += map(str,[indicies[2],indicies[1],indicies[0]])

    for vidx, vert in enumerate(verticies):
        lines += [vert]
        
    strs.append('\n\t\t '+ '\n\t\t, '.join(lines) + '\n') #+ nx,ny,nz
    strs.append(']\n,[')

    strs.append(','.join(map(str,idx))) 

    strs.append('])\n')
    if ob.uv_texture_clone:
        # Get the texture pathshu
        texturepath = bpy.path.abspath(ob.uv_textures[0].data[0].image.filepath)
        texturefolder = bpy.utils._os.path.dirname(texturepath)
        tmp = texturepath
        texturename = tmp.replace(texturefolder+'\\','')
        # get the output folder
        outputfolder = bpy.utils._os.path.dirname(filename)
        outputfile = outputfolder + '\\' + texturename
        # copy the file
        if texturepath != outputfile:
            shutil.copyfile(texturepath,outputfile)
        # write to MDL
        strs.append(',ImportImageFromFile("'+texturename+'",false))\n') # link to the texture
    else:
        strs.append(',emptyImage)\n')                     # link to the empty texture
        
    return ''.join(strs)

def printColor(c):
        #format Color(r,g,b)
        #eg Color(1,0.012,1)
    return 'Color('+','.join(map(str,c))+')'

def printVector(v):
        #format Vector(x,y,z)
        #eg     Vector(1.1,2.2,3.2)
    return 'Vector('+','.join(map('{:20.20f}'.format,v))+')'

def printLight(lamp):
            #format (color,vector,m_period,m_phase,m_rampUp,m_hold,m_rampDown)
            #eg (Color(1, 1, 1),Vector(-0.021303,-15.5763035,4.931641),1,1.25,0,0.1,0.05)
    return '('+printColor(lamp.color)+','+printVector(bpy.data.objects[lamp.name].location)+',1,1.25,0,0.1,0.05)'

#ZString strName     = GetString(ppair->GetNth(0));
#            Vector  vecPosition = GetVector(ppair->GetNth(1));
#            Vector  vecForward  = GetVector(ppair->GetNth(2));
#            Vector  vecUp       = GetVector(ppair->GetLastNth(3));
def boneRotation(bone):
    up = bpy.data.objects[bone.name].up_axis
    if up == 'Z':
        up_vector = [0,0,1]
    if up == 'Y':
        up_vector = [0,1,0]
    if up == 'X':
        up_vector = [1,0,0]                
    return up_vector   
    
def frameData(bone): # returns string
    strs = []
    strs.append('(')
    strs.append('"'+bone.name+'", ')
    strs.append(printVector(bone.head)+', ')
    strs.append(printVector(bone.vector)+', ') # direction of the tail
    strs.append(printVector(boneRotation(bone))+')') # bones dont seem to have an up vector
    return ''.join(strs)
    
def write_some_data(context, filename, use_some_setting):
    out = open(filename, 'w')
    meshes= bpy.data.meshes
    out.write('use "model";\n')
    out.write('use "effect";\n\n')
    out.write('frame = ModifiableNumber(1);\n\n')
    
    # Export Lights
    if len(bpy.data.lamps) > 0:
        out.write('lights = LightsGeo([\n\t' + ',\n\t'.join(map(printLight,bpy.data.lamps)) +']);\n\n')
    
    # need to add handling for frames here... includes all hardpoints and garages
    if len(bpy.data.armatures) > 0:
        frames = []
        for idx, arm in enumerate(bpy.data.armatures):
            frames.append(',\n\t'.join(map(frameData,arm.bones)))
        out.write('frames = FrameData([\n\t' + ',\n\t'.join(frames) +']);\n\n')
    
    # finally dump out the model data    
    # if only one mesh, then just return a texturegeo
    if len(meshes) == 1:
        out.write('object = ' + textureGeo(meshes[0],filename) + ';')    
    # else multi meshes, we need a groupgeo with a collection of textureGeos in it    
    else: 
        texturegeos = []
        for ob in meshes:
            if ob.name != 'Convex Hull':
                if ob.name != 'CVH':
                    texturegeos.append('('+textureGeo(ob,filename)+')')
        out.write('object = GroupGeo([' + ', '.join(texturegeos) + ']);')
        
    out.close()
    #shutil.copyfile(filename,filename.replace(".mdl","_.mdl"))

    return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ExportSomeData(Operator, ExportHelper):
    '''This appears in the tooltip of the operator and in the generated docs'''
    bl_idname = "export_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export for Allegiance"

    # ExportHelper mixin class uses this
    filename_ext = ".mdl"

    filter_glob = StringProperty(
            default="*.mdl",
            options={'HIDDEN'},
            )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_exportTexture = BoolProperty(
            name="Export Texture",
            description="Use if you have bound a texture to your model",
            default=True,
            )

    use_exportCVH = BoolProperty(
            name="Export Convex Hull",
            description="Use if you have created a convex hull for your model",
            default=True,
            )
            
    user_exportHartpoints = BoolProperty(
            name="Export Hardpoints",
            description="Use if you have created hardpoints for your model",
            default=True,
            )        

#    type = EnumProperty(
#            name="Example Enum",
#            description="Choose between two items",
#            items=(('OPT_A', "First Option", "Description one"),
#                   ('OPT_B', "Second Option", "Description two")),
#            default='OPT_A',
#            )

    def execute(self, context):
        return write_some_data(context, self.filepath, self.use_exportTexture)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportSomeData.bl_idname, text="Allegiance MDL")


def register():
    bpy.utils.register_class(ExportSomeData)
    bpy.types.INFO_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportSomeData)
    bpy.types.INFO_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.export_test.some_data('INVOKE_DEFAULT')