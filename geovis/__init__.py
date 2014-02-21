# IMPORTS
#builtins
import sys, os, itertools, array, threading, random, math
import Tkinter as tk
#customized
custommodulepath = r"C:\Users\BIGKIMO\Desktop\vshapes"
sys.path.append(custommodulepath)
import messages
#third party modules
import shapefile_fork as pyshp
import colour

# GLOBAL VARS
NULL = 0
POINT = 1
POLYLINE = 3
POLYGON = 5
MULTIPOINT = 8
POINTZ = 11
POLYLINEZ = 13
POLYGONZ = 15
MULTIPOINTZ = 18
POINTM = 21
POLYLINEM = 23
POLYGONM = 25
MULTIPOINTM = 28
MULTIPATCH = 31

PYSHPTYPE_AS_TEXT = {\
    NULL:"Null",
    POINT:"Point",
    POINTZ:"PointZ",
    POINTM:"PointM",
    POLYLINE:"PolyLine",
    POLYLINEZ:"PolyLineZ",
    POLYLINEM:"PolyLineM",
    POLYGON:"Polygon",
    POLYGONZ:"PolygonZ",
    POLYGONM:"PolygonM",
    MULTIPOINT:"MultiPoint",
    MULTIPOINTZ:"MultiPointZ",
    MULTIPOINTM:"MultiPointM",
    MULTIPATCH:"MultiPatch"}

try:
    import numpy
    NUMPYSPEED = True
except:
    NUMPYSPEED = False
REDUCEVECTORS = True

SHOWPROGRESS = True
#some map stuff
MAPBACKGROUND = None
RENDERER = "aggdraw"
#set mapdims to window size
mapdimstest = tk.Tk()
MAPWIDTH = int(mapdimstest.winfo_screenwidth())
MAPHEIGHT = int(mapdimstest.winfo_screenheight())
mapdimstest.destroy()
del mapdimstest

def _UpdateMapDims():
    if NUMPYSPEED:
        global ZOOMDIM, OFFSET, TRANSLATION, RENDERAREA, SCALING
        ZOOMDIM = numpy.array([360.0,180.0])
        OFFSET = numpy.array([0.0,0.0])*-1 #move x or y by normal +- coordinates (not compat with zoom yet
        TRANSLATION = numpy.array([180.0, -90.0]) + OFFSET
        RENDERAREA = numpy.array([MAPWIDTH, -MAPHEIGHT])
        SCALING = RENDERAREA / ZOOMDIM
    else:
        global XOFFSET, YOFFSET, XWIDTH, YHEIGHT
        XOFFSET = 180
        YOFFSET = 90
        XWIDTH = 360
        YHEIGHT = 180
_UpdateMapDims()

COLORSTYLES = dict([("strong", dict( [("intensity",1), ("brightness",0.5)]) ),
                    ("dark", dict( [("intensity",0.8), ("brightness",0.2)]) ),
                    ("matte", dict( [("intensity",0.4), ("brightness",0.2)]) ),
                ("bright", dict( [("intensity",0.8), ("brightness",0.7)] ) ),
                ("pastelle", dict( [("intensity",0.5), ("brightness",0.6)] ) )
                    ])


# INTERNAL CLASSES
class _PyShpShape:
    def __init__(self, coords, shapetype):
        self.coords = coords
        self.type = shapetype
    def to_tkinter(self):
        convertedcoords = self._MapCoords(self.coords)
        formattedcoords = convertedcoords
        return formattedcoords
    def to_PIL(self):
        convertedcoords = self._MapCoords(self.coords)
        formattedcoords = convertedcoords
        return array.array("f",formattedcoords)
    def to_aggdraw(self):
        convertedcoords = self._MapCoords(self.coords)
        formattedcoords = convertedcoords
        return array.array("f",formattedcoords)
    def to_pycairo(self):
        convertedcoords = self._MapCoords(self.coords)
        formattedcoords = self.__pairwise(convertedcoords)
        return formattedcoords
    #internal use only
    def __pairwise(self, coords, batchsize=2):
        return [pair for pair in itertools.izip(*[iter(coords)] * batchsize)]
    def _MapCoords(self, incoords):
        if NUMPYSPEED:
            converted = (incoords + TRANSLATION) * SCALING
            #for smoother drawings comment out the rint and vstack commands below
            if REDUCEVECTORS:
                converted = numpy.rint(converted).astype(int)
                converted = numpy.vstack((converted[0], converted[1:][numpy.any(converted[1:]!=converted[:-1], axis=1)]))
            aslist = converted.flatten()
            return aslist
        else:
            outcoords = []
            previous = None
            for point in incoords:
                inx, iny = point
                newx = (XOFFSET+inx)/XWIDTH*MAPWIDTH
                newy = MAPHEIGHT-(YOFFSET+iny)/YHEIGHT*MAPHEIGHT
                if REDUCEVECTORS:
                    newpoint = (int(newx),int(newy))
                    if newpoint != previous:
                        outcoords.extend(newpoint)
                        previous = newpoint
                else:
                    newpoint = [newx,newy]
                    outcoords.extend(newpoint)
            return outcoords
        

class _IterShapefile:
    #builtins
    def __init__(self, shapefilepath):
        self.shapefile = pyshp.Reader(shapefilepath)
        name = ".".join(shapefilepath.split(".")[:-1])
        name = name.split("\\")[-1]
        self.filename = name
    def __len__(self):
        return self.shapefile.numRecords
    def __iter__(self):
        if NUMPYSPEED:
            for shape in self.shapefile.iterShapes(numpyspeed=NUMPYSPEED):
                SHAPEFILELOOP.Increment()
                shapetype = PYSHPTYPE_AS_TEXT[shape.shapeType].lower()
                if "polygon" in shapetype:
                    if not numpy.any(shape.parts):
                        yield _PyShpShape(shape.points, shapetype)
                    else:
                        for each in numpy.split(shape.points, shape.parts[1:]):
                            yield _PyShpShape(each, "polygon")
                elif "line" in shapetype:
                    if not numpy.any(shape.parts):
                        yield _PyShpShape(shape.points, shapetype)
                    else:
                        for each in numpy.split(shape.points, shape.parts[1:]):
                            yield _PyShpShape(each, "line")
                elif "point" in shapetype:
                    if "multi" in shapetype:
                        for each in shape.points:
                            yield _PyShpShape(each, "point")
                    else:
                        yield _PyShpShape(shape.points, "point")
        else:
            for shape in self.shapefile.iterShapes(numpyspeed=NUMPYSPEED):
                SHAPEFILELOOP.Increment()
                #first set new shapetype to pass on
                shapetype = PYSHPTYPE_AS_TEXT[shape.shapeType].lower()
                if "polygon" in shapetype:
                    newshapetype = "polygon"
                if "line" in shapetype:
                    newshapetype = "line"
                if "point" in shapetype:
                    newshapetype = "point"
                #then serve up points universal for all shapetypes
                if "point" in shapetype:
                    yield _PyShpShape(shape.points, newshapetype)
                elif len(shape.parts) == 1:
                    yield _PyShpShape(shape.points, newshapetype)
                else:
                    shapeparts = list(shape.parts)
                    shapeparts.append(len(shape.points))
                    startindex = shapeparts[0]
                    for endindex in shapeparts[1:]:
                        eachmulti = shape.points[startindex:endindex]
                        startindex = endindex
                        yield _PyShpShape(eachmulti, newshapetype)

class _TkCanvas_Renderer:
    def __init__(self):
        pass
    def NewImage(self):
        """this must be called before doing any rendering.\
        Note: this replaces any previous image drawn on so be sure to
        retrieve the old image before calling it again to avoid losing work"""
        width = MAPWIDTH
        height = MAPHEIGHT
        background = MAPBACKGROUND
        self.img = None
        self.window = tk.Tk()
        self.window_frame = tk.Frame(self.window)
        self.window_frame.pack()
        screenwidth = self.window.winfo_screenwidth()
        if MAPWIDTH >= screenwidth:
            self.window.wm_state('zoomed')
        self.drawer = tk.Canvas(self.window_frame, width=width, height=height, bg="white")
        self.drawer.pack()
        #place the shadow
        if background:
            x0,y0,x1,y1 = ( -int(width/50.0), int(height/50.0), width-int(width/50.0), height+int(height/50.0) )
            self.drawer.create_rectangle(x0,y0,x1,y1, fill="Gray15", outline="")
        #place background
        x0,y0,x1,y1 = ( 0, 0, width, height )
        self.drawer.create_rectangle(x0,y0,x1,y1, fill=background, outline="")
        #make image pannable
        def mouseovermap(event):
            global mouseovermapvar
            self.window.config(cursor="fleur") #draft_large
            mouseovermapvar = True
        def mouseoutofmap(event):
            global mouseovermapvar
            self.window.config(cursor="")
            mouseovermapvar = False
        def activatedrag(event):
            global mouseclicked
            if mouseovermapvar == True:
                mouseclicked = True
        def deactivatedrag(event):
            global mouseclicked
            mouseclicked = False
        def mark(event):
            self.drawer.scan_mark(event.x, event.y)
        def dragto(event):
            try:
                if mouseclicked == True:
                    self.drawer.scan_dragto(event.x, event.y, 1)
            except:
                pass
        self.drawer.bind("<Enter>", mouseovermap, "+")
        self.drawer.bind("<Leave>", mouseoutofmap, "+")
        self.window.bind("<Button-1>", mark, "+")
        self.window.bind("<Motion>", dragto, "+")
        self.window.bind("<Button-1>", activatedrag, "+")
        self.window.bind("<ButtonRelease-1>", deactivatedrag, "+")
    def Render(self, shapeobj, options):
        "looks at instructions in options to decide which draw method to use"
        coords = shapeobj.to_tkinter()
        if shapeobj.type == "polygon":
            self._BasicPolygon(coords, options)
        elif shapeobj.type == "line":
            self._BasicLine(coords, options)
        elif shapeobj.type == "point":
            self._BasicCircle(coords, options)
    def RunTk(self):
        self.window.mainloop()

    #Internal use only
    def _BasicLine(self, coords, options):
        "draw basic lines with outline, but nothing at start and end"
        if len(coords) < 4:
            return
        #first draw outline line
        self.drawer.create_line(*coords, fill=options.get("outlinecolor"), width=int(options.get("fillsize")+(options.get("outlinewidth")*2)))
        #then draw fill line which is thinner
        self.drawer.create_line(*coords, fill=options.get("fillcolor"), width=int(options.get("fillsize")))
    def _BasicPolygon(self, coords, options):
        "draw polygon with color fill"
        if len(coords) > 6:
            self.drawer.create_polygon(*coords, fill=options["fillcolor"], outline=options["outlinecolor"])
    def _BasicCircle(self, coords, options):
        "draw points with a symbol path representing a circle"
        size = int(options["fillsize"]/2.0)
        x,y = coords
        circlecoords = (x-size, y-size, x+size, y+size)
        self.drawer.create_oval(circlecoords, fill=options["fillcolor"], outline=options["outlinecolor"])

class _PIL_Renderer:
    "this class can be called on to draw each feature with PIL as long as \
    it is given instructions via a color/size/options dictionary"
    #NEED TO RECEIVE GENERATOR OF TRANSFORMED COORDS FROM MAPCANVAS
    #ALSO NEEDS THE Aggdraw.Draw(img) OBJECT
    def __init__(self):
        global PIL
        import PIL, PIL.Image, PIL.ImageDraw, PIL.ImageTk
    def NewImage(self):
        """this must be called before doing any rendering.\
        Note: this replaces any previous image drawn on so be sure to
        retrieve the old image before calling it again to avoid losing work"""
        #first mode
        mode = "RGBA"
        #then other specs
        width = MAPWIDTH
        height = MAPHEIGHT
        background = MAPBACKGROUND
        dimensions = (width, height)
        self.img = PIL.Image.new(mode, dimensions, background)
        self.drawer = PIL.ImageDraw.Draw(self.img)
    def Render(self, shapeobj, options):
        "looks at instructions in options to decide which draw method to use"
        #possibly use an options filterer here to enure all needed options
        #are given, otherwise snap to default
        #............
        coords = shapeobj.to_PIL()
        if shapeobj.type == "polygon":
            self._BasicPolygon(coords, options)
        elif shapeobj.type == "line":
            self._BasicLine(coords, options)
        elif shapeobj.type == "point":
            self._BasicCircle(coords, options)
    def GetImage(self):
        del self.drawer
        return PIL.ImageTk.PhotoImage(self.img)
    def SaveImage(self, savepath):
        del self.drawer
        self.img.save(savepath)

    #Internal use only
    def _BasicLine(self, coords, options):
        "draw basic lines with outline, but nothing at start and end"
        #first draw outline line
        self.drawer.line(coords, fill=options.get("outlinecolor"), width=int(options.get("fillsize")+(options.get("outlinewidth")*2)))
        #then draw fill line which is thinner
        self.drawer.line(coords, fill=options.get("fillcolor"), width=int(options.get("fillsize")))
    def _BasicPolygon(self, coords, options):
        "draw polygon with color fill"
        if len(coords) > 6:
            self.drawer.polygon(coords, fill=options["fillcolor"], outline=options["outlinecolor"])
    def _BasicCircle(self, coords, options):
        "draw points with a symbol path representing a circle"
        size = int(options["fillsize"]/2.0)
        x,y = coords
        circlecoords = (x-size, y-size, x+size, y+size)
        self.drawer.ellipse(circlecoords, fill=options["fillcolor"], outline=options["outlinecolor"])
    def _Dot(self, coords):
        self.drawer.point(coords, "black")

class _Aggdraw_Renderer:
    "this class can be called on to draw each feature with aggdraw as long as \
    it is given instructions via a color/size/options dictionary"
    #NEED TO RECEIVE GENERATOR OF TRANSFORMED COORDS FROM MAPCANVAS
    #ALSO NEEDS THE Aggdraw.Draw(img) OBJECT
    def __init__(self):
        global aggdraw, PIL
        import aggdraw, PIL, PIL.Image, PIL.ImageDraw, PIL.ImageTk
    def NewImage(self):
        """this must be called before doing any rendering.\
        Note: this replaces any previous image drawn on so be sure to
        retrieve the old image before calling it again to avoid losing work"""
        #first mode
        mode = "RGBA"
        #then other specs
        width = MAPWIDTH
        height = MAPHEIGHT
        background = MAPBACKGROUND
        dimensions = (width, height)
        self.img = PIL.Image.new(mode, dimensions, background)
        self.drawer = aggdraw.Draw(self.img)
    def Render(self, shapeobj, options):
        "looks at instructions in options to decide which draw method to use"
        coords = shapeobj.to_aggdraw()
        if shapeobj.type == "polygon":
            self._BasicPolygon(coords, options)
        elif shapeobj.type == "line":
            self._BasicLine(coords, options)
        elif shapeobj.type == "point":
            self._BasicCircle(coords, options)
    def GetImage(self):
        self.drawer.flush()
        return PIL.ImageTk.PhotoImage(self.img)
    def SaveImage(self, savepath):
        self.drawer.flush()
        self.img.save(savepath)

    #Internal use only
    def _BasicLine(self, coords, options):
        "draw basic lines with outline, but nothing at start and end"
        #first draw outline line
        outlinepen = aggdraw.Pen(options["outlinecolor"], options["fillsize"]+options["outlinewidth"])
        self.drawer.line(coords, outlinepen)
        #then draw fill line which is thinner
        fillpen = aggdraw.Pen(options["fillcolor"], options["fillsize"])
        self.drawer.line(coords, fillpen)
    def _BasicPolygon(self, coords, options):
        "draw polygon with color fill"
        outlinepen = aggdraw.Pen(options["outlinecolor"], options["outlinewidth"])
        fillbrush = aggdraw.Brush(options["fillcolor"])
        self.drawer.polygon(coords, fillbrush, outlinepen)
        pass
    def _BasicCircle(self, coords, options):
        "draw points with a symbol path representing a circle"
        #build circle
        size = int(options["fillsize"]/2.0)
        x,y = coords
        circlecoords = (x-size, y-size, x+size, y+size)
        #set symbol options
        outlinepen = aggdraw.Pen(options["outlinecolor"], options["outlinewidth"])
        fillbrush = aggdraw.Brush(options["fillcolor"])
        #draw
        self.drawer.ellipse(circlecoords, fillbrush, outlinepen)

class _PyCairo_Renderer:
    "this class can be called on to draw each feature with PIL as long as \
    it is given instructions via a color/size/options dictionary"
    #NEED TO RECEIVE GENERATOR OF TRANSFORMED COORDS FROM MAPCANVAS
    #ALSO NEEDS THE Aggdraw.Draw(img) OBJECT
    def __init__(self):
        global cairo
        import cairo
    def NewImage(self):
        """this must be called before doing any rendering.\
        Note: this replaces any previous image drawn on so be sure to
        retrieve the old image before calling it again to avoid losing work"""
        #first mode
        mode = cairo.FORMAT_ARGB32
        #then other specs
        width = MAPWIDTH
        height = MAPHEIGHT
        background = MAPBACKGROUND
        self.img = cairo.ImageSurface(mode, int(MAPWIDTH), int(MAPHEIGHT))
        self.drawer = cairo.Context(self.img)
        if background:
            backgroundcolor = self.__hex_to_rgb(background)
            self.drawer.set_source_rgb(*backgroundcolor)
            self.drawer.rectangle(0,0,MAPWIDTH,MAPHEIGHT)
            self.drawer.fill()
    def Render(self, shapeobj, options):
        "looks at instructions in options to decide which draw method to use"
        #possibly use an options filterer here to enure all needed options
        #are given, otherwise snap to default
        #............
        coords = shapeobj.to_pycairo()
        if shapeobj.type == "polygon":
            self._BasicPolygon(coords, options)
        elif shapeobj.type == "line":
            self._BasicLine(coords, options)
        elif shapeobj.type == "point":
            self._BasicCircle(coords, options)
    def GetImage(self):
        self.img.write_to_gif("tempgif.gif")
        gifimg = tk.PhotoImage("tempgif.gif")
        os.remove("tempgif.gif")
        return gifimg
    def SaveImage(self, savepath):
        if savepath.endswith(".png"):
            self.img.write_to_png(savepath)

    #Internal use only
    def __hex_to_rgb(self, hexcolor):
        return colour.Color(hexcolor).rgb
    def _BasicLine(self, coords, options):
        "draw basic lines with outline, but nothing at start and end"
        if len(coords) >= 2:
            #outline symbolics
            outlinecolor = self.__hex_to_rgb(options["outlinecolor"])
            self.drawer.set_source_rgb(*outlinecolor) # Solid color
            self.drawer.set_line_width(options.get("fillsize")+(options.get("outlinewidth")*2))
            #draw outline
            xy = coords[0]
            self.drawer.move_to(*xy)
            for xy in coords[1:]:
                self.drawer.line_to(*xy)
            self.drawer.stroke_preserve()
            #fill symbolics
            outlinecolor = self.__hex_to_rgb(options["fillcolor"])
            self.drawer.set_source_rgb(*outlinecolor) # Solid color
            self.drawer.set_line_width(options.get("fillsize"))
            #then draw fill line which is thinner
            xy = coords[0]
            self.drawer.move_to(*xy)
            for xy in coords[1:]:
                self.drawer.line_to(*xy)
            self.drawer.stroke_preserve()
    def _BasicPolygon(self, coords, options):
        "draw polygon with color fill"
        if len(coords) >= 6:
            #define outline symbolics
            outlinecolor = self.__hex_to_rgb(options["outlinecolor"])
            self.drawer.set_source_rgb(*outlinecolor) # Solid color
            self.drawer.set_line_width(options["outlinewidth"])
            #...self.drawer.set_line_join(cairo.LINE_JOIN_ROUND)
            #first starting point
            xy = coords[0]
            self.drawer.move_to(*xy)
            #then add path for each new vertex
            for xy in coords[1:]:
                self.drawer.line_to(*xy)
            self.drawer.close_path()
            self.drawer.stroke_preserve()
            #then fill insides
            fillcolor = self.__hex_to_rgb(options["fillcolor"])
            self.drawer.set_source_rgb(*fillcolor)
            self.drawer.fill()
    def _BasicCircle(self, coords, options):
        "draw points with a symbol path representing a circle"
        #define outline symbolics
        outlinecolor = self.__hex_to_rgb(options["outlinecolor"])
        self.drawer.set_source_rgb(*outlinecolor) # Solid color
        self.drawer.set_line_width(options["outlinewidth"])
        #draw circle
        size = int(options["fillsize"]/2.0)
        x,y = coords[0] #0 necessary bc pycairo receives a list of coordinate pairs, and with points there is only one pair
        self.drawer.arc(x, y, size, 0, 2*math.pi)
        self.drawer.stroke_preserve()
        #fill circle
        fillcolor = self.__hex_to_rgb(options["fillcolor"])
        self.drawer.set_source_rgb(*fillcolor)
        self.drawer.fill()

class _Renderer:
    #builtins
    def __init__(self):
        if RENDERER == "tkinter":
            self.renderer = _TkCanvas_Renderer()
        elif RENDERER == "PIL":
            self.renderer = _PIL_Renderer()
        elif RENDERER == "aggdraw":
            self.renderer = _Aggdraw_Renderer()
        elif RENDERER == "pycairo":
            self.renderer = _PyCairo_Renderer()
        #automatically create blank image
        self.NewImage()
    #custom methods
    def NewImage(self):
        self.renderer.NewImage()
    def ViewShapefile(self, shapefilepath, customoptions):
        self._RenderShapefile(shapefilepath, customoptions)
        self._ViewRenderedShapefile()
    def SaveShapefileImage(self, shapefilepath, savepath, customoptions):
        self._RenderShapefile(shapefilepath, customoptions)
        self._SaveRenderedShapefile(savepath)
    #internal use only
    def _RenderShapefile(self, shapefilepath, customoptions):
        #create shapefile generator
        shapefile = _IterShapefile(shapefilepath)
        #prepare progressreporting
        if SHOWPROGRESS:
            shellreport = "progressbar"
        else:
            shellreport = None
        global SHAPEFILELOOP
        SHAPEFILELOOP = messages.ProgressReport(shapefile, text="rendering "+shapefile.filename, shellreport=shellreport, countmethod="manual")
        #then iterate through shapes and render each
        for eachshape in SHAPEFILELOOP:
            #then send to be rendered
            self.renderer.Render(eachshape, customoptions)
    def _ViewRenderedShapefile(self):
        #finally open image in tkinter
        if RENDERER == "tkinter":
            #if tkinter is the renderer then all that is needed is to run the mainloop
            self.renderer.RunTk()
        else:
            def ViewInTkinter():
                #setup GUI
                window = tk.Tk()
                window.wm_title("Static MapCanvas Viewer")
                window_frame = tk.Frame(window)
                window_frame.pack()
                screenwidth = window.winfo_screenwidth()
                if MAPWIDTH >= screenwidth:
                    window.wm_state('zoomed')
                #embed image in a canvas
                tkimg = self.renderer.GetImage()
                canvas = tk.Canvas(window_frame, width=MAPWIDTH, height=MAPHEIGHT, bg="white")
                canvas.pack()
                x0,y0,x1,y1 = ( -int(MAPWIDTH/50.0), int(MAPHEIGHT/50.0), MAPWIDTH-int(MAPWIDTH/50.0), MAPHEIGHT+int(MAPHEIGHT/50.0) )
                if MAPBACKGROUND:
                    canvas.create_rectangle(x0,y0,x1,y1, fill="Gray15", outline="") #this is the shadow
                canvas.create_image(0,0, anchor="nw", image=tkimg)
                #make image pannable
                def mouseovermap(event):
                    global mouseovermapvar
                    window.config(cursor="fleur") #draft_large
                    mouseovermapvar = True
                def mouseoutofmap(event):
                    global mouseovermapvar
                    window.config(cursor="")
                    mouseovermapvar = False
                def activatedrag(event):
                    global mouseclicked
                    if mouseovermapvar == True:
                        mouseclicked = True
                def deactivatedrag(event):
                    global mouseclicked
                    mouseclicked = False
                def mark(event):
                    canvas.scan_mark(event.x, event.y)
                def dragto(event):
                    try:
                        if mouseclicked == True:
                            canvas.scan_dragto(event.x, event.y, 1)
                    except:
                        pass
                canvas.bind("<Enter>", mouseovermap, "+")
                canvas.bind("<Leave>", mouseoutofmap, "+")
                window.bind("<Button-1>", mark, "+")
                window.bind("<Motion>", dragto, "+")
                window.bind("<Button-1>", activatedrag, "+")
                window.bind("<ButtonRelease-1>", deactivatedrag, "+")
                #place save button to enable saving map image
                import tkFileDialog
                def imagesavefiledialog():
                    savepath = tkFileDialog.asksaveasfilename()
                    self._SaveRenderedShapefile(savepath)
                savebutton = tk.Button(window_frame, text="Save Image", command=imagesavefiledialog)
                savebutton.place(x=5, y=5, anchor="nw")
                #open window
                window.mainloop()
            tkthread = threading.Thread(target=ViewInTkinter)
            tkthread.start()
    def _SaveRenderedShapefile(self, savepath):
        if RENDERER == "tkinter":
            raise AttributeError("The Tkinter map renderer does not have a function to save the map as an image \
due to the limited options of the Tkinter Canvas. If possible try using any of the other renderers instead")
        else:
            self.renderer.SaveImage(savepath)







############## FINALLY, DEFINE FRONT-END USER FUNCTIONS

#GENERAL UTILITIES
def _FolderLoop(folder, filetype=""):
    "a generator that iterates through all files in a folder tree, either in a for loop or by using next() on it.\
    Filetype can be set to only grab files that have the specified file-extension. If filetype is a tuple then grabs all filetypes listed within it."
    alldirs = os.walk(folder)
    # loop through and run unzip function
    for eachdirinfo in alldirs:
        eachdir = eachdirinfo[0]+"\\"
        dirfiles = eachdirinfo[2]
        for eachfile in dirfiles:
            if eachfile.endswith(filetype):
                eachfilename = ".".join(eachfile.split(".")[:-1])
                eachfiletype = "." + eachfile.split(".")[-1]
                yield (eachdir, eachfilename, eachfiletype)
def ShapefileFolder(folder):
    "Returns a generator that will loop through a folder and all its subfolder and return information of every shapefile it finds. Information returned is a tuple with the following elements (string name of current subfolder, string name of shapefile found, string of the shapefile's file extension(will always be '.shp'))\
    -folder is a path string of the folder to check for shapefiles."
    for eachfolder, eachshapefile, eachfiletype in _FolderLoop(folder, filetype=".shp"):
        yield (eachfolder, eachshapefile, eachfiletype)
        
#RENDERING OPTIONS
def SetRenderingOptions(**renderoptions):
    "Sets certain rendering options that apply to all visualizations or map images.\
    -renderer is a string describing which Python module will be used for rendering. This means you need to have the specified module installed. Valid renderer values are 'tkinter', 'PIL', 'aggdraw', 'pycairo'. Notes: If you have no renderers installed, then use Tkinter which comes with all Python installations, although it is significantly slow, memory-limited, and cannot be used to save images. Currently PyCairo is not very well optimized, and is particularly slow to render line shapefiles. \
    -numpyspeed specifies whether to use numpy to speed up shapefile reading and coordinate-to-pixel conversion. Must be True or False.\
    -reducevectors specifies whether to reduce the number of vectors to be rendered. This can speed up rendering time, but may lower the quality of the rendered image, especially for line shapefiles. " 
    if renderoptions.get("renderer", "not found") != "not found":
        global RENDERER
        RENDERER = renderoptions["renderer"]
    if renderoptions.get("numpyspeed", "not found") != "not found":
        global NUMPYSPEED
        NUMPYSPEED = renderoptions["numpyspeed"]
        _UpdateMapDims() #this bc map dimensions have to be recalculated to/from numpyspeed format
    if renderoptions.get("reducevectors", "not found") != "not found":
        global REDUCEVECTORS
        REDUCEVECTORS = renderoptions["reducevectors"]
        
#STYLE CUSTOMIZING
DEFAULTCOLOR = dict([("basecolor","random"),
                       ("intensity","random"),
                       ("brightness","random"),
                       ("style",None)
                       ])
def SetMapColors(**optionstochange):
    "Sets the default style options that will be used to visualize shapefiles. These default options will only be used for those options of a shapefile that the user has not already specified.\
    -customoptions is any series of named arguments of how to style the shapefile visualization (optional)"
    for eachoption, newvalue in optionstochange.iteritems():
        DEFAULTOPTIONS[eachoption] = newvalue
def Color(basecolor="random", intensity="random", brightness="random", style=None):
    "Returns a hex color string of the color options specified. \
    -basecolor is the human-like name of a color.\
    -intensity of how strong the color should be. Must be a float between 0 and 1.\
    -brightness of how light or dark the color should be. Must be a float between 0 and 1."
    #first check on intens/bright
    if style:
        #style overrides manual intensity and brightness options
        intensity = COLORSTYLES[style]["intensity"]
        brightness = COLORSTYLES[style]["brightness"]
    else:
        #maybe get random
        if intensity == "random":
            intensity = random.randrange(20,80)/100.0
        if brightness == "random" and basecolor not in ("black","white","gray"):
            brightness = random.randrange(20,80)/100.0
    if basecolor in ("black","white","gray"):
        #special black,white,gray mode, bc random intens/bright starts creating colors,
        #and so have to be ignored
        if brightness == "random":
            return colour.Color(color=basecolor).hex
        else:
            #only listen to brightness if was specified by user (nonrandom)
            return colour.Color(color=basecolor, luminance=brightness).hex
    elif basecolor == "random":
        basecolor = random.randrange(100)
        return colour.Color(pick_for=basecolor, saturation=intensity, luminance=brightness).hex
    else:
        return colour.Color(color=basecolor, saturation=intensity, luminance=brightness).hex

def ColorFeeder(**coloroptions):
    """Returns an infinite generator of colors of a specified style. To generate a new color of the specified color options use the generator as an argument to the next() method or loop through it.\
    -coloroptions is any series of named arguments to specify aspects of a color style. See the Color object documentation."""
    while True:
        value = Color(**coloroptions)
        yield value

DEFAULTOPTIONS = dict([("fillcolor",Color()),
                       ("fillsize",3),
                       ("outlinecolor",Color()),
                       ("outlinewidth",1.5)
                       ])
def SetMapSymbols(**optionstochange):
    "Sets the default style options that will be used to visualize shapefiles. These default options will only be used for those options of a shapefile that the user has not already specified.\
    -customoptions is any series of named arguments of how to style the shapefile visualization (optional)"
    for eachoption, newvalue in optionstochange.iteritems():
        DEFAULTOPTIONS[eachoption] = newvalue
def _CheckOptions(customoptions):
    if not customoptions.get("fillcolor"):
        customoptions["fillcolor"] = DEFAULTOPTIONS["fillcolor"]
    if not customoptions.get("fillsize"):
        customoptions["fillsize"] = DEFAULTOPTIONS["fillsize"]
    if not customoptions.get("outlinecolor"):
        customoptions["outlinecolor"] = DEFAULTOPTIONS["outlinecolor"]
    if not customoptions.get("outlinewidth"):
        customoptions["outlinewidth"] = DEFAULTOPTIONS["outlinewidth"]
    return customoptions

#QUICK TASKS
def ViewShapefile(shapefilepath, **customoptions):
    "Quick task to visualize a shapefile and show it in a Tkinter window.\
    -shapefilepath is the path string of the shapefile.\
    -customoptions is any series of named arguments of how to style the shapefile visualization (optional)"
    customoptions = _CheckOptions(customoptions)
    renderer = _Renderer()
    renderer.ViewShapefile(shapefilepath, customoptions)
def SaveShapefileImage(shapefilepath, savepath, **customoptions):
    "Quick task to save a shapefile to an image.\
    -shapefilepath is the path string of the shapefile.\
    -savepath is the path string of where to save the image, including the image type extension.\
    -customoptions is any series of named arguments of how to style the shapefile visualization (optional)"
    customoptions = _CheckOptions(customoptions)
    renderer = _Renderer()
    renderer.SaveShapefileImage(shapefilepath, savepath, customoptions)

#MAP BUILDING
class NewMap:
    "Creates and returns a new map based on previously defined mapsettings."
    def __init__(self):
        self.renderer = _Renderer()
    def AddToMap(self, shapefilepath, **customoptions):
        "Add a shapefile to the map.\
        -shapefilepath is the path string of the shapefile to add."
        customoptions = _CheckOptions(customoptions)
        self.renderer._RenderShapefile(shapefilepath, customoptions)
    def ViewMap(self):
        "View the created map in a Tkinter window"
        self.renderer._ViewRenderedShapefile()
    def SaveMap(self, savepath):
        "Save the map to an image file.\
        -savepath is the string path for where you wish to save the map image. Image type extension must be specified ('.png','.gif',...)"
        self.renderer._SaveRenderedShapefile(savepath)

#MAP SPECS  
def SetMapDimensions(width, height):
    "Sets the width and height of the next map. At startup the width and height are set to the dimensions of the window screen.\
    -width/height must be integers."
    global MAPWIDTH, MAPHEIGHT
    MAPWIDTH = width
    MAPHEIGHT = height
    _UpdateMapDims()
def SetMapBackground(mapbackground):
    "Sets the mapbackground of the next map to be made. At startup the mapbackground is transparent (None).\
    -mapbackground takes a hex color string, as can be created with the Color function. It can also be None for a transparent background."
    global MAPBACKGROUND
    MAPBACKGROUND = mapbackground
def SetZoomExtent():
    "Not yet in use, and will not still create entire image..."
    if NUMPYSPEED:
        pass
    else:
        pass
    _UpdateMapDims()


### END OF SCRIPT ###
