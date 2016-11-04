__author__ = 'Michael'

import math
import dendropy
from view import *
from utilities import rotate

# class Singleton(type):
#     def __init__(cls, name, bases, dict):
#         super(Singleton, cls).__init__(name, bases, dict)
#         cls.instance = None
#
#     def __call__(cls, *args, **kw):
#         if not cls.instance:
#             # Not created or has been Destroyed
#             obj = super(Singleton, cls).__call__(*args, **kw)
#             cls.instance = obj
#         return cls.instance

class AnnotatedPhylogramModel():
    tree_file = None
    annotation_file = None

    def __init__(self):
        #state information
        self.state_tree_loaded=False
        self.state_node_annotation_loaded=False
        self.rp = None

        #picture information
        self.node_annotation = None
        self.segments=[]
        self.node_coordinates={}
        self.node_annotation_level=None
        self.checked=[]

    def initialize_tree(self,tp=None):

        if tp<> None:
            self.tree_file=tp
        self.rp=Radial_Phylogram(self.tree_file)
        self.rp.get_segments()
        self.segments=self.rp.segments
        self.state_tree_loaded=True

    def unload_tree(self):
        self.rp=None
        self.rp.segments=[]
        self.state_tree_loaded=False

    def initialize_annotation(self,ann_path):
        self.annotation_file=ann_path
        self.node_annotation=SfldAnnotationData(self.annotation_file)
        self.state_node_annotation_loaded=True


    pass

class Radial_Phylogram():
    '''
    Right now it requires the tree to have labels equal to the "efd_id" field from the node_annotation
    '''
    max_dims=None

    def __init__(self,tp=None):
        self.treepath=''
        self.myt=None
        self.node_labels={}
        self.segments=[]
        self.selected=[]
        self.leaf_node_coords={}
        self.selected_color=None
        self.rotation=0
        if tp is not None:
            self.set_treepath(tp)
        # self.print_right_angles()

    # def set_rotation(self,rotation):
    #     '''
    #
    #     :param rotation: rotation given in degrees
    #     :return:
    #     '''
    #     self.rotation=rotation/360 * 2 * math.pi
    #     tp = self.treepath
    #     self.set_treepath(tp)
        # self.get_radial_phylogram()
        # self.get_segments()
        # self.get_max_dims()

    def spacefill_get_space_filling_phylogram(self):
        '''
        This function will populate the dendropy tree with a set of properties on each edge and node that
        define a 2D tree layout that approximately fills the rectangular viewing area optimally.

        The properties are 'deflect_angle' on each edge, a 'location' on each node and an 'aspect_ratio'
        on the tree object. The layout is defined by a root-edge, the aspect ratio and the deflect angles (
        positive = clockwise). Default aspect ratio is 1.6 (w/h)
        :return:
        '''
        if self.myt.aspect_ratio is None:
            self.myt.aspect_ratio = 1.6
        to = 0
        for i in self.myt.postorder_edge_iter():
            if i.length is None:
                i.length = 0.0
            to += i.length

        self.myt.calc_node_ages(ultrametricity_precision=False,is_force_max_age=True)
        self.myt.calc_node_root_distances(False)

        first = True
        for i in self.myt.postorder_edge_iter():
            current_opposite_dist=0
            if first==True:
                root_childs= i.head_node.child_nodes()
                root_child_dists = [(j.age+j.edge_length) for j in root_childs]
                root_opposite_dists = [(max(root_child_dists[:ind]+root_child_dists[(ind+1):])) for ind in range(len(root_childs))]
                first = False
            else:
                if i.head_node in root_childs:
                    ind = root_childs.index(i)
                    current_opposite_dist = root_opposite_dists[ind]

            if i.head_node.is_leaf() == True:
                i.head_mass = 0
                i.tail_mass = to - i.length
                # i.head_width = -1
                i.head_len = i.length
                i.tail_len = i.head_node.parent.root_distance + current_opposite_dist
                # i.tail_width =
            else:
                cn = i.head_node.child_nodes()
                i.head_mass = sum([(k.edge.head_mass + k.edge.length) for k in cn])
                i.tail_mass = to - i.length - i.head_mass
                i.head_len = i.length+i.age
                i.tail_len = i.head_node.parent.root_distance + current_opposite_dist

        self.cent_edge = self.spacefill_get_centroid_edge()
        self.cent_child_nodes = []
        for e in self.cent_edge.adjacent_edges:
            if e.head_node==self.cent_edge.head_node:
                self.cent_child_nodes.append(e.tail_node)
            else:
                self.cent_child_nodes.append(e.head_node)

        self.myt.reroot_at_edge(self.cent_edge)
        for i in self.myt.preorder_node_iter():
            if i.length is None:
                i.length = 0.

        self.myt.calc_node_ages(ultrametricity_precision=False,is_force_max_age=True)
        self.myt.calc_node_root_distances(False)

        d = self.cent_edge.length

        for i in self.cent_child_nodes:
            ages=[(j.age + j.edge_length) for j in i.child_nodes()]
            # TODO: continue here

    def spacefill_get_centroid_edge(self):
        '''
        finds the edge with the minimal squared deviation from a (1/4, 1/4, 1/4, 1/4) split based
        on the 'age' attribute of the four child nodes (plus lengths)
        :return:
        '''
        m_sse = 9999999.0
        cent_edge = None
        for i in self.myt.preorder_edge_iter():
            eds = i.adjacent_edges
            hn = i.head_node
            tn = i.tail_node
            if len(eds)>=4:
                heads= [(e.head_node==hn or e.head_node==tn) for e in eds]
                k = len(heads)
                lens = [0.]*k
                for ind in range(k):
                    if heads[ind]==True:
                        lens[ind]=eds[ind].length+eds[ind].tail_len
                    else:
                        lens[ind]=eds[ind].length+eds[ind].head_len
                all_lens = sum(lens)
                sse=sum([(j/all_lens-1.0/float(k))**2 for j in lens])
                if sse < m_sse:
                    m_sse = sse
                    cent_edge = i
        return cent_edge

    def dump_all(self):
        del self.myt
        self.myt=None
        del self.segments
        self.segments=None

    def set_treepath(self,tp):
        self.treepath=tp
        self.myt=dendropy.Tree.get(file=open(self.treepath,'r'),schema="newick",preserve_underscores=True)
        self.get_radial_phylogram()
        self.get_max_dims()
        self.get_leaf_node_coords()
        self.get_segments()


    def get_radial_phylogram(self):
        # myt=set_treepath(tp)
        # theta_vals=[]
        # theta_vals2=[]
        # theta_vals3=[]
        self.prepare_tree()
        for i in self.myt.postorder_node_iter():
            if i.is_leaf()==True:
                self.node_labels[i.label]['l']=1
            else:
                child_l=0
                for j in i.child_node_iter():
                    child_l+=self.node_labels[j.label]['l']
                self.node_labels[i.label]['l']=child_l
        pr=self.myt.preorder_node_iter()
        r=pr.next()

        self.node_labels[r.label]['x']=(0.0,0.0)
        r.location = (0.0,0.0)
        r.deflect_angle = 0.
        r.wedge_angle = 2*math.pi
        r.edge_segment_angle = 0.
        r.right_wedge_border = 0.
        self.node_labels[r.label]['w']=2*math.pi
        self.node_labels[r.label]['t']=0.0
        self.node_labels[r.label]['nu']=0.0
        leafct=len(r.leaf_nodes())

        # k=0
        for i in pr:
            # k+=1
            # print k
            # if i.edge_length is None:
            # i.edge_length = 0.001 # debug
            ww=float(len(i.leaf_nodes()))/leafct*2*math.pi
            self.node_labels[i.label]['w']=ww   # wedge angle
            i.wedge_angle=ww
            i.right_wedge_border =self.node_labels[i.parent_node.label]['nu']
            self.node_labels[i.label]['t']=i.right_wedge_border # angle of right wedge border
            # theta_vals.append(self.node_labels[i.label]['t'])
            self.node_labels[i.label]['nu']=self.node_labels[i.label]['t']
            thetav=self.node_labels[i.parent_node.label]['nu']+ww/2
            i.edge_segment_angle=thetav
            self.node_labels[i.label]['theta']=thetav
            # theta_vals2.append(i.label)
            self.node_labels[i.parent_node.label]['nu']+=ww
            xu=self.node_labels[i.parent_node.label]['x']
            delta=i.edge_length
            try:
                x1=xu[0]+delta*math.cos(thetav)
                x2=xu[1]+delta*math.sin(thetav)
            except:
                print 'thetav is %d' % thetav
                x1=xu[0]
                x2=xu[1]
            i.location = (x1,x2)
            i.deflect_angle = thetav - self.node_labels[i.parent_node.label]['theta']
            # theta_vals3.append(self.node_labels[i.label]['t'])
            # x1_orig = xu[0] + delta * math.cos(thetav)
            # x2_orig = xu[1] + delta * math.sin(thetav)
            # x1 = x1_orig*math.cos(self.rotation)-x2_orig*math.sin(self.rotation)
            # x2 = x1_orig*math.sin(self.rotation)+x2_orig*math.cos(self.rotation)
            self.node_labels[i.label]['x']=(x1,x2)

        for i in self.myt.preorder_internal_node_iter():
            w = i.wedge_angle
            for j in i.child_node_iter():
                j.percent_of_parent_wedge=j.wedge_angle/w

    def relocate_subtree_by_deflect_angle(self,node):
        '''
        runs a preorder node iteration and uses the current deflection angles of each node to replace
        its current location with a new location.
        :param node:
        :return:
        '''
        for i in node.preorder_iter():
            t0 = i.parent_node.edge_segment_angle
            x0 = i.parent_node.location
            t1 = i.deflect_angle + t0
            x1x = x0[0]+i.edge_length*math.cos(t1)
            x1y = x0[1]+i.edge_length*math.sin(t1)
            i.location = (x1x,x1y)

    def relocate_subtree_by_wedge_properties(self,node):
        preo = node.preorder_iter()
        nd = preo.next()
        temp_nu={}
        temp_nu[nd.id]=nd.right_wedge_border
        for i in preo:
            i.wedge_angle = i.percent_of_parent_wedge*i.parent_node.wedge_angle
            i.right_wedge_border = temp_nu[i.parent_node.id]
            temp_nu[i.parent_node.id]+=i.wedge_angle
            temp_nu[i.id]=i.right_wedge_border
            i.edge_segment_angle = i.right_wedge_border + i.wedge_angle/2

            xu = i.parent_node.location
            delta = i.edge_length
            x1 = xu[0] + delta * math.cos(i.edge_segment_angle)
            x2 = xu[1] + delta * math.sin(i.edge_segment_angle)
            i.location=(x1,x2)
            i.deflect_angle = i.edge_segment_angle-i.parent_node.edge_segment_angle


    def get_de_facto_spread_angle(self,node):
        start = node.parent_node.location
        angles = []
        for i in node.leaf_iter():
            xi = i.location
            ang = math.atan2(xi[1]-start[1],xi[0]-start[0])
            if ang < 0:
                ang = 2*math.pi - ang
            angles.append(ang)
        return min(angles), max(angles)

    def angle_spread_extension(self):
        pass

    def get_max_dims(self):
        xma=float(0)
        xmi=float(0)
        yma=float(0)
        ymi=float(0)

        for i in self.node_labels.keys():
            x=self.node_labels[i]['x'][0]
            y=self.node_labels[i]['x'][1]
            if x>xma and x is not None:
                xma=x
            if x<xmi and x is not None:
                xmi=x
            if y>yma and y is not None:
                yma=y
            if y<ymi and y is not None:
                ymi=y
        self.max_dims=(xmi-.0001,xma+.0001,ymi-.0001,yma+.0001)
        return (xmi-.0001,xma+.0001,ymi-.0001,yma+.0001)

    def get_segments(self):
        '''
        sets the 'segments' property to be a list of tuples of tuples [((x11,y11),(x12,y12)),...]
        '''

        self.segments=[]
        view_segments={}

        for i in self.myt.preorder_node_iter():
            if i.parent_node is not None:
                i.edge.viewer_edge=None
                i.viewer_node=None
                x1 = self.node_labels[i.parent_node.label]['x']
                x2 = self.node_labels[i.label]['x']
                # x1_orig=self.node_labels[i.parent_node.label]['x']
                # x2_orig=self.node_labels[i.label]['x']
                # x1=rotate(x1_orig,self.rotation)
                # x2=rotate(x2_orig,self.rotation)

                old_label=self.node_labels[i.label]['old_label']
                try:
                    bootstrap=float(old_label)
                except:
                    bootstrap=None
                ed = ViewerEdge(x1,x2,None,None,i.edge.label,bootstrap,i.edge)
                i.edge.viewer_edge=ed
                nd=ViewerNode(x2,node_ref=i,theta=self.node_labels[i.label]['t'])
                i.viewer_node=nd
                self.segments.append((x1,x2))
                view_segments[i.edge.label]=ed
            else:
                i.edge.viewer_edge=None
                i.viewer_node=None
        return view_segments

    def prepare_tree(self):
        # print self.myt.internal_edges()[1].length
        rooted = False
        for i in self.myt.preorder_edge_iter():
            if i.length==None:
                rooted=True
                break
        if rooted==False:
            self.myt.reroot_at_edge(self.myt.internal_edges()[1])

        lab=1
        for i in self.myt.preorder_edge_iter():
            i.label='edge'+str(lab)
            lab+=1

        lab=1
        alllabs=set([])
        ct = 0
        for i in self.myt.postorder_node_iter():
            oldlab=i.label
            i.id = ct
            ct+=1
            # i.label='label' + str(lab)
            # lab+=1
            # if i.is_leaf()==True:
            #     taxname=i.taxon.label
            # else:
            #     taxname=''
            # self.node_labels[i.label]={'x':None, 'l':None, 'w':None, 't':None, 'nu':None, 'theta':0, 'old_label':oldlab, 'taxon_label':taxname}
            if i.taxon == None:
                if i.label == None or i.label in alllabs:
                    # print i.__dict__
                    i.label='label' + str(lab)
                    lab+=1
                    if i.is_leaf()==True:
                        taxname=i.taxon.label
                    else:
                        taxname=''
                else:
                    taxname=i.label
            else:
                i.label=i.taxon.label
                taxname=i.label
            alllabs.add(oldlab)
            self.node_labels[i.label]={'x':None, 'l':None, 'w':None, 't':None, 'nu':None, 'theta':0, 'old_label':oldlab, 'taxon_label':taxname}


    def get_selected(self,tx):
        #TODO: Make sure this is deprecated
        # print 'getting x coords for selected taxa'
        settx=set(tx)
        self.selected=[]
        # ct = 0
        for i in self.myt.leaf_node_iter():
            # ct +=1
            # if ct % 1000==0:
            #     print str(i.taxon.label) + ' - ' + type(i.taxon.label)
            if str(i.taxon.label) in settx:
                self.selected.append(self.node_labels[i.label]['x'])
        return self.selected

    def get_leaf_node_coords(self):
        '''
        Just makse a dictionary of all the leaf node descriptions along with their coordaintes and a refernce to the
            node object that stores them
        '''
        self.leaf_node_coords={}
        for i in self.myt.leaf_node_iter():
            args={'x':self.node_labels[i.label]['x'],'node_ref':i}
            args['drawn']=False
            args['color']=None
            args['node_annotation']=None
            self.leaf_node_coords[i.taxon.label]=args.copy()
            del args

    def get_view_nodes(self):
        view_nodes={}
        for i in self.myt.preorder_node_iter():
            vn=ViewerNode(x=self.node_labels[i.label]['x'],node_ref=i,theta=self.node_labels[i.label]['theta'])
            view_nodes[i.label] = vn
        return view_nodes

    def refresh_all(self):
        self.get_radial_phylogram()
        self.get_segments()
        self.get_max_dims()

    # def deform_clade_by_wedge_and_radians_dummy(self, myedge, width_radians, right_edge_radians):
    #     pass

    def deform_clade_by_wedge_and_radians(self,myedge,width_radians, right_edge_radians):
        nd = myedge.head_node
        init_ww = self.node_labels[nd.label]['w']
        init_t = self.node_labels[nd.label]['t']


        pr = nd.preorder_iter()
        a=pr.next()
        self.node_labels[a.label]['w']=width_radians
        self.node_labels[a.label]['t']=right_edge_radians
        self.node_labels[a.label]['nu']=right_edge_radians
        ref_ct = float(len(a.leaf_nodes()))
        # a=nd
        # self.node_labels[a.label]['w']=width_radians
        # self.node_labels[a.label]['t']=right_edge_radians
        # self.node_labels[a.label]['nu']=right_edge_radians
        # ref_ct = float(len(a.leaf_nodes()))

        for i in pr:
            # k+=1
            # print k
            ww=float(len(i.leaf_nodes()))/ref_ct*width_radians
            self.node_labels[i.label]['w']=ww   # wedge angle
            self.node_labels[i.label]['t']=self.node_labels[i.parent_node.label]['nu'] # angle of right wedge border
            self.node_labels[i.label]['nu']=self.node_labels[i.label]['t']
            thetav=self.node_labels[i.parent_node.label]['nu']+ww/2
            self.node_labels[i.label]['theta']=thetav
            self.node_labels[i.parent_node.label]['nu']+=ww
            xu=self.node_labels[i.parent_node.label]['x']
            delta=i.edge_length
            x1=xu[0]+delta*math.cos(thetav)
            x2=xu[1]+delta*math.sin(thetav)
            # x1_orig = xu[0] + delta * math.cos(thetav)
            # x2_orig = xu[1] + delta * math.sin(thetav)
            # x1 = x1_orig*math.cos(self.rotation)-x2_orig*math.sin(self.rotation)
            # x2 = x1_orig*math.sin(self.rotation)+x2_orig*math.cos(self.rotation)
            self.node_labels[i.label]['x']=(x1,x2)

        self.get_segments()
        self.get_max_dims()

class AnnotationData():

    def __init__(self,filepath,filter_vals = None):
        self.path = filepath
        self.import_data(filter_vals)
        self.filter1_field=None
        self.filter1_options=set([])
        self.filter1_values=set([])
        self.filter2_field = None
        self.filter2_options = set([])
        self.filter2_values = set([])

        self.selected_annotation_field=None
        self.active_unique_annotation_values=set([])

    def import_data(self,filter_vals = None):
        f=open(self.path,'r')
        self.headers = f.readline().strip().split('\t')
        self.data = {}
        if filter_vals is None:
            for i in f:
                a=i.strip().split('\t')
                self.data[a[0]]=tuple(a)
        else:
            for i in f:
                a=i.strip().split('\t')
                if a[0] in filter_vals:
                    self.data[a[0]]=tuple(a)
        f.close()

    def load_filter1(self,header):
        f1_vals=[]

        self.filter1_field=header
        if self.filter1_field=='(none)':
            self.filter1_options = set([])
            self.filter1_values = set([])
        else:
            f1_col = self.headers.index(header)
            for i in self.data.values():
                f1_vals.append(i[f1_col])

        self.filter1_options=set(f1_vals)
        return self.filter1_options

    def load_filter2(self, header):
        f2_vals = []
        print "getting values for header %s" % header
        self.filter2_field = header
        if self.filter2_field == '(none)':
            self.filter2_options = set([])
            self.filter2_values = set([])
        else:
            f2_col = self.headers.index(header)
            f1_col = self.headers.index(self.filter1_field)
            for i in self.data.values():
                if len(self.filter1_values) == 0 or i[f1_col] in self.filter1_values:
                    f2_vals.append(i[f2_col])

        self.filter2_options = set(f2_vals)
        return self.filter2_options

    def process_filter2(self, selections):
        if len(selections) == 0:
            self.filter2_values = set([])
        else:
            self.filter2_values = set(selections)

    def process_filter1(self, selections):
        if len(selections) == 0:
            self.filter1_values = set([])
        else:
            self.filter1_values = set(selections)

    def get_active_unique_annotation_values(self):
        # print self.selected_annotation_field
        if self.selected_annotation_field is None or self.selected_annotation_field == '':
            return None
        if self.active_unique_annotation_values is not None:
            del self.active_unique_annotation_values
        uav = []
        ann_col = self.headers.index(self.selected_annotation_field)
        # print ann_col
        if self.filter1_field is not None:
            f1_col = self.headers.index(self.filter1_field)
        if self.filter2_field is not None:
            f2_col = self.headers.index(self.filter2_field)

        self.grouped={}
        setuav=set([])
        for i in self.data.keys():
            keep = True
            if self.filter1_field is not None and len(self.filter1_values) > 0 and self.data[i][f1_col] not in self.filter1_values:
                keep = False
            elif self.filter2_field is not None and len(self.filter2_values) > 0 and self.data[i][f2_col] not in self.filter2_values:
                keep = False
            if keep == True:
                # uav.append(self.data[i][ann_col])
                ann_col_val = self.data[i][ann_col]
                if ann_col_val in setuav:
                    self.grouped[ann_col_val].append(i)
                else:
                    # print self.data[i]
                    # print "%s - %s" % (ann_col_val,str(setuav))
                    setuav.update(set([self.data[i][ann_col]]))
                    self.grouped[ann_col_val]=[i]

        self.active_unique_annotation_values = setuav
        # print setuav
        return setuav

    def get_EFDIDs_grouped_by(self,header_field):
        self.get_active_unique_annotation_values()
        return self.grouped

class SfldAnnotationData():
    '''
    must be tab-separated values
    must have one of the header fields called "efd_id"
    '''

    def __init__(self, filepath,key_field='Observation ID'):
        self.f=open(filepath,'r')
        self.data={}
        self.uniques={}
        # key_field='seqname'
        key_field='seqnum'

        #get field names
        self.fieldnames=self.f.readline().strip().split('\t')
        try:
            # self.efdid_index=self.fieldnames.index('efd_id')
            self.efdid_index=self.fieldnames.index(key_field)
            self.annotation_fields=self.fieldnames[:self.efdid_index] + self.fieldnames[(self.efdid_index+1):]
            self.import_data()
        except:
            print 'No column called %s in the node_annotation file %s' % (key_field,filepath)
            self.efdid_index=None
            self.annotation_fields=None

    def import_data(self):
        '''
        method run at inititalization to import all the data
        :return:
        '''
        uniques_lists={}
        for i in range(len(self.fieldnames)):
            if i != self.efdid_index:
                uniques_lists[self.fieldnames[i]]=[]

        for i in self.f:
            a=i.strip().split('\t')
            args={}
            id = a[self.efdid_index]
            for i in range(len(self.fieldnames)):
                if i != self.efdid_index:
                    args[self.fieldnames[i]]=a[i]
                    uniques_lists[self.fieldnames[i]].append(a[i])
            self.data[id]=args.copy()
            del args

        for i in uniques_lists.keys():
            self.uniques[i]=list(set(uniques_lists[i]))

        del uniques_lists

    def get_EFDIDs_grouped_by(self,header_field):
        # try:
        assert header_field in self.fieldnames
        # except:
        #     print "get_EFIDs_grouped_by called with missing header field"
        #     return {}

        grouped={}
        for i in self.data:
            a=self.data[i][header_field]
            if a in grouped.keys():
                grouped[a].append(i)
            else:
                grouped[a]=[i]

        for i in grouped:
            grouped[i]=set(grouped[i])

        # print grouped
        return grouped
