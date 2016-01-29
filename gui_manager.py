__author__ = 'Michael'

from my_globals import *
import tree_manipulator as trman
import sfld_view
import view_classes
import controller
import wx
import os.path
import skimage.io
import skimage.transform
import skimage.draw
import numpy as np

class MyApp(wx.App):
    def OnInit(self):
        self.mainframe = gui_manager(None)
        self.SetTopWindow(self.mainframe)
        self.mainframe.Show()

        return True



class gui_manager(sfld_view.ctrlFrame):
    '''
    top level frame for this application
    '''
    tree_file=None
    annotation_file=None
    def __init__(self,parent):
        sfld_view.ctrlFrame.__init__(self,parent)

        self.c=controller.Controller()

        self.working_folder=None
        self.cold_initialize()

        self.initial_checks()
        self.add_value_pickers()
        self.populate_annotation_fields()

        #TODO: This is just for the verstion where we want to do a cold initialize, otherwise have to make the image frame
        #    decide whether to show itself, etc...

        self.image_frame=image_manager(self)
        self.c.set_ImageFrame_referenece(self.image_frame)
        self.c.circle_size=self.m_slider1.GetValue()
        self.image_frame.Show()

    def cold_initialize(self):
        self.set_file()
        self.set_annotation_file()
        self.import_tree()
        self.import_annotation()

    def populate_annotation_fields(self):
        # ONLY EXECUTE THIS ONCE THE ANNOTATION HAS BEEN LOADED
        flds=self.c.annotation_fields
        self.m_ComboSelectedField.Clear()
        self.m_ComboSelectedField.AppendItems(flds)

        if 'subgroup_id' in flds:
            self.m_ComboSelectedField.SetValue('subgroup_id')
            self.populate_annotation_values()

    def populate_annotation_values(self,event=None):
        fld = self.m_ComboSelectedField.GetValue()
        self.c.apm.annotation_level=fld
        unqs = self.c.apm.annotation.uniques[fld]
        # print unqs

        self.value_picker.set_values(unqs)
        self.m_panel5.Layout()
        self.value_picker.Fit(self.m_panel5)
        self.m_panel4.Layout()
        self.c.set_ValuePickerCtrl_reference(self.value_picker)


    def add_value_pickers(self):
        self.value_picker=view_classes.ValuePickerControl(self.m_panel5, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.SUNKEN_BORDER)
        # self.value_picker.set_values(['180'])


        self.m_panel5.SetSizer( self.value_picker)

        self.m_panel5.Layout()
        self.value_picker.Fit(self.m_panel5)
        self.m_panel4.Layout()
        self.Layout()

    def initial_checks(self):
        if self.m_FilePicker_tree.GetTextCtrlValue()<>'':
            self.set_file(filepath=self.m_FilePicker_tree.GetTextCtrlValue())
        if self.m_FilePicker_annotation.GetTextCtrlValue()<>'':
            self.annotation_file=self.m_FilePicker_annotation.GetTextCtrlValue()

    def set_file( self, event=None, filepath=None):
        fo=''
        self.tree_file=self.m_FilePicker_tree.GetPath()
        try:
            fo, fi = os.path.split(self.tree_file)
        except:
            pass
        self.working_folder=fo
        self.txt_workingFolder.SetValue(fo)

    def set_annotation_file( self, event=None, filepath=None):
        self.annotation_file=self.m_FilePicker_annotation.GetPath()

    def SaveCurrentImage(self,event):
        tgt_file=self.m_textImageSaveTarget.GetValue()
        tgt_path=os.path.join(self.working_folder,tgt_file)
        self.image_frame.save_dc_to_bitmap(tgt_path)

    # def process_annotationvalue_check(self,event):
    #     checked=[]
    #     for i in self.value_picker.value_pickers:
    #         if i.m_checkBox1.IsChecked()==True:
    #             checked=(i.value, i.clr)
    #
    #     print checked

    def import_tree( self, event=None ):
        self.c.import_tree(self.tree_file)

    def import_annotation( self, event=None ):
        self.c.import_annotation(self.annotation_file)
        self.c.get_relevent_data_from_model()

    def trigger_redraw(self,event=None):
        self.c.circle_size=int(self.m_slider1.GetValue())
        self.c.trigger_refresh()



#
#   Utility Function:
#
def convert_coordinates(xyrange,disprange,xycoords):
    '''
    Converts coordinates from the x-y plan based on the range "xyrange" (xmin, xmax, ymin, ymax) to the display coordinates

    :param xyrange: (xmin, xmax, ymin, ymax)
    :param disprange: (w , h) (indexed at 0, so max output will be (w-1, h-1)
    :param xycoords: (x,y)
    :return: display coords (on numpy scale) or None if it's out of the display range
    '''
    xnew = round((disprange[0]-1)*(xycoords[0]-xyrange[0])/(xyrange[1]-xyrange[0]), 0)
    ynew = disprange[1]-1 - round((disprange[1]-1)*(xycoords[1]-xyrange[2])/(xyrange[3]-xyrange[2]), 0)
    if xnew > disprange[0]-1 or xnew < 0 or ynew < 0 or ynew > disprange[1]-1:
        return None
    else:
        return (xnew,ynew)



class image_manager(sfld_view.imgFrame):

    def __init__(self,parent):
        sfld_view.imgFrame.__init__(self,parent)
        self.Bind(wx.EVT_PAINT,self.OnPaint)

        self.c=controller.Controller()


        print 'opening tree file & making phylogram'
        # self.rp=trman.Radial_Phylogram(test_tp) #TODO: fix these to refer to textboxes
        # self.rp.get_max_dims()
        # self.rp.get_segments()
        self.oldrange=self.c.max_data_dims
        self.current_bitmap=None

        print 'getting annotation data'
        # self.ann_data=trman.SfldAnnotationData(test_annotation) #TODO: same as earlier
        self.eid_hash=None

    def save_dc_to_bitmap(self,tgt_path):
        # self.current_bitmap.SaveFile(test_folder + '/wx_output_bitmap.jpg',wx.BITMAP_TYPE_JPEG)
        self.current_bitmap.SaveFile(tgt_path,wx.BITMAP_TYPE_JPEG)

    def OnImgPaint(self,event):
        self.pdc=wx.PaintDC(self.img_panel)
        w=self.pdc.GetSize()[0]
        h=self.pdc.GetSize()[1]
        #TODO: Uncomment this
        self.get_current_tree_image(w,h)
        self.draw_circles(w,h)

        if self.current_bitmap<>None:
            # print 'bitmap set to None'
            self.pdc.DrawBitmap(self.current_bitmap,0,0)

    def get_current_tree_image(self,w,h):
        self.current_bitmap=wx.EmptyBitmap(w,h)
        self.memdc=wx.MemoryDC(self.current_bitmap)
        self.memdc.Clear()

        sz=(w,h)

        for i in self.c.apm.segments:
            x1=convert_coordinates(self.oldrange,sz,i[0])
            x2=convert_coordinates(self.oldrange,sz,i[1])
            if x1 is not None and x2 is not None:
                self.memdc.DrawLine(x1[0],x1[1],x2[0],x2[1])

        self.memdc.SelectObject(wx.NullBitmap)

    def draw_circles(self,w,h,header_field=None,value=None):
        # if header_field is None:
        #     header_field='subgroup_id'
        # if value is None:
        #     value='180'
        #
        sz=(w,h)
        circ_size=self.c.circle_size
        list_of_circles=self.c.get_circle_sets_by_color()
        # self.eid_hash=self.ann_data.get_EFDIDs_grouped_by(header_field)
        # eids=self.eid_hash[value]
        # print "eids have length %s" % str(len(eids))
        # circles=self.rp.get_selected(eids)


        self.memdc.SelectObject(self.current_bitmap)
        curr_brush=self.memdc.GetBrush()
        for i in list_of_circles:
            self.memdc.SetBrush(wx.Brush(wx.Colour(i[0],i[1],i[2]),wx.SOLID))
            for j in list_of_circles[i]:
                x=convert_coordinates(self.oldrange,sz,j)
                self.memdc.DrawCirclePoint(wx.Point(x[0],x[1]),circ_size)

        self.memdc.SetBrush(curr_brush)
        self.memdc.SelectObject(wx.NullBitmap)


    # def testimage(self):
    #     ti=skimage.io.imread(test_image)
    #     h=int(ti.shape[0])
    #     w=int(ti.shape[1])
    #     print h
    #     print w
    #     wxi=wx.ImageFromBuffer(w,h,np.getbuffer(ti))
    #     wxb=wxi.ConvertToBitmap()
    #     return wxb



