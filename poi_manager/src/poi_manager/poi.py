#!/usr/bin/env python


from rcomponent.rcomponent import *

#!/usr/bin/env python

import rospy
import yaml
import rospkg
import tf
import os
from poi_manager_msgs.msg import *
from poi_manager_msgs.srv import *

from geometry_msgs.msg import Pose
from std_msgs.msg import Empty
from visualization_msgs.msg import MarkerArray, Marker



class PoiManager(RComponent):

    def __init__(self):

        self.pose_list = []
        self.pose_dict = {'environements':{}}

        RComponent.__init__(self)



    def ros_read_params(self):
        """Gets params from param server"""
        RComponent.ros_read_params(self)

        rospack = rospkg.RosPack()
        self.filename = rospy.get_param('~filename', 'test')
        self.folder = rospy.get_param('~folder', os.path.join(rospack.get_path('poi_manager'), 'config'))
        self.yaml_path = self.folder + '/' + self.filename+'.yaml'

        self.publish_markers = rospy.get_param('~publish_markers', False)
        self.frame_id = rospy.get_param('~frame_id', 'map')

        rospy.loginfo('%s::_init_: config file path: %s', self._node_name, self.yaml_path)

    def ros_setup(self):
        """Creates and inits ROS components"""
        RComponent.ros_setup(self)

        self.service_read_yaml = rospy.Service('~read_pois', ReadPOIs, self.handle_labeled_pose_list)
        self.service_write_data = rospy.Service('~update_pois', UpdatePOIs, self.handle_updated_list)
        self.service_get_poi = rospy.Service('~get_poi', GetPOI, self.get_poi_cb)
        self.service_get_poi_list = rospy.Service('~get_poi_list', GetPOIs, self.get_poi_list_cb)
        self.service_add_poi = rospy.Service('~add_poi', AddPOI, self.add_poi_cb)
        self.service_add_poi = rospy.Service('~add_poi_by_params', AddPOI_params, self.add_poi_by_params_cb)
        if self.publish_markers:
            self.marker_array = MarkerArray()

            self.marker_array_publisher = rospy.Publisher('~markers', MarkerArray, queue_size=10)

    def ros_publish(self):
        '''
                Publish topics at standard frequency
        '''

        if self.publish_markers:
            self.marker_array_publisher.publish(self.marker_array)

    def parse_yaml(self):
        try:
            f = open(self.yaml_path, 'r')
            self.pose_dict = {}
            self.pose_dict = yaml.safe_load(f)
            if self.pose_dict is None:
                self.pose_dict = {}
            f.close()
            return True,"OK"
        except (IOError, yaml.YAMLError) as e:
            rospy.logerr(e)
            return False , "Error reading yaml: %s" % e

    def manage_read_data(self):
        self.pose_list = []       
        envir_n = 0
        points_n = 0  
        msg =""  
        try:
            for key,value in self.pose_dict.items():
                # Dictionaries of point list
                for key_list,value_list in value.items():
                    # Dictionary of point list
                    envir_n = envir_n + 1
                    for point_list_key,value_point_list in value_list.items():
                        if point_list_key=='points':
                            for name_point_key,values_point in value_point_list.items():                
                                points_n = points_n + 1
                                labeled_point = LabeledPose()
                                labeled_point.name = name_point_key
                                labeled_point.environement = key_list
                                for point_params_key,value_params in values_point.items():                                                              
                                    if (point_params_key=='frame_id'):
                                        labeled_point.frame_id = value_params
                                    if (point_params_key=='name'):
                                        labeled_point.name = value_params
                                    if (point_params_key=='params'):
                                        labeled_point.params = value_params
                                    if (point_params_key=='position'):
                                        labeled_point.pose.position.x=value_params[0]
                                        labeled_point.pose.position.y=value_params[1]
                                        labeled_point.pose.position.z=value_params[2]
                                    if (point_params_key=='orientation'):
                                        labeled_point.pose.orientation.x=value_params[0]
                                        labeled_point.pose.orientation.y=value_params[1]
                                        labeled_point.pose.orientation.z=value_params[2]
                                        labeled_point.pose.orientation.w=value_params[3]

                                self.pose_list.append(labeled_point)  
                        else:
                            rospy.loginfo("%s::Found other property in point list: %s", rospy.get_name(),point_list_key)
        except Exception as identifier:
            msg = "%s::Error reading yaml file: %s" % (rospy.get_name(),identifier)
            rospy.logerror(msg)  
            return False,msg  
        msg = " Read %d environements and %d points" % (envir_n,points_n)
        
        if self.publish_markers:
            self.update_marker_array()

        return True,msg

    #def ready_state(self):
        
        #if self.publish_markers:
        #    self.update_marker_array()

    def update_yaml(self, req):
        yaml_file = file(self.yaml_path, 'w')
        pose_list = req.pose_list
        self.pose_dict = {}
        for elem in pose_list:
            self.pose_dict[elem.label] = [elem.pose.x, elem.pose.y, elem.pose.theta]
        yaml.dump(self.pose_dict, yaml_file)
        
        if self.publish_markers:
            self.update_marker_array()

    def update_marker_array(self):
        marker_array = MarkerArray()
        for item in self.pose_list:
            # Two markers are created for each item
            # The first one shows the pose
            marker_arrow = self.create_marker(item, 'arrow')
            # The second one shows the label
            marker_text = self.create_marker(item, 'text')
            
            marker_array.markers.append(marker_arrow)
            marker_array.markers.append(marker_text)
        self.marker_array = marker_array
        self.marker_array_publisher.publish(self.marker_array)

    def ready_state(self):
        if self.publish_markers:
            self.update_marker_array()

    def create_marker(self, point, marker_type):

        marker = Marker()
        marker.header.frame_id = point.frame_id
        marker.header.stamp = rospy.Time()
        marker.ns = point.name + "_" + point.environement
        marker.action = Marker.ADD
        marker.pose.position.x = point.pose.position.x
        marker.pose.position.y = point.pose.position.y
        #quaternion = tf.transformations.quaternion_from_euler(0, 0, data[1][2])
        marker.pose.orientation.x = point.pose.orientation.x
        marker.pose.orientation.y = point.pose.orientation.y
        marker.pose.orientation.z = point.pose.orientation.z
        marker.pose.orientation.w = point.pose.orientation.w
        
        # TODO: parameterize arrow color
        marker.color.a = 1.0
        marker.color.g = 1.0
        marker.lifetime = rospy.Duration(1)
        if marker_type == 'arrow':
            marker.scale.x = 1.0
            marker.scale.y = 0.5
            marker.scale.z = 0.5
            marker.id = 0
            marker.type = Marker.ARROW
        else:
            marker.scale.z = 0.5
            marker.id = 1
            marker.type = Marker.TEXT_VIEW_FACING
            marker.text = point.name + "_" + point.environement
            marker.pose.position.z = 0.5
            marker.color.r = 1.0
            marker.color.b = 1.0
        return marker

    def handle_labeled_pose_list(self, req):
        success,msg = self.parse_yaml()        
        if (success==False):
            return ReadPOIsResponse(success,msg,self.pose_list)    
        success,msg = self.manage_read_data()
        rospy.loginfo("%s::handle_labeled_pose_list: read_pois service done", self._node_name)
        return ReadPOIsResponse(success,msg,self.pose_list)

    def handle_updated_list(self, req):
        self.update_yaml(req)
        rospy.loginfo("%s::handle_updated_list: update_pois service done", self._node_name)
        return UpdatePOIsResponse()

    def get_poi_cb(self, req):
        response = GetPOIResponse()
        if len(self.pose_list) > 0:            
            for poi in self.pose_list:                
                if poi.name == req.name and poi.environement == req.environement:
                    response.success = True
                    response.message = " Poi %s/%s found" % (req.name,req.environement)
                    response.p = poi
                    return response
        else:
            response.success = False
            response.message = " Poi %s/%s Not found, empty list" % (req.name,req.environement)
            return response
        response.success = False
        response.message = " Poi %s/%s Not found" % (req.name,req.environement)
        return response

    def get_poi_list_cb(self, req):
        response = GetPOIsResponse()
        num = 0
        if len(self.pose_list) > 0:   
            for poi in self.pose_list: 
                if poi.environement == req.environement:         
                    response.p_list.append(poi)
                    num = num + 1
            if num>0:
                response.success = True
                response.message = "  Found %d POIs from %s " % (num,req.environement)
            else:
                response.success = False
                response.message = "  Found %d POIs from %s " % (num,req.environement)
        else:
            response.success = False
            response.message = " Pois from %s Not found, empty list" % (req.environement)
        return response

    def try_create_env(self,dict_name,new_env):
        try:
            if len(dict_name['environements'][new_env])==0:
                return 
        except:
           dict_name['environements'][new_env] = {}
           dict_name['environements'][new_env]['points'] = {} 
        return

    def try_create_point(self,dict_name,new_env,point_name):
        try:
            if len(dict_name['environements'][new_env]['points'][point_name])==0:
                return 
        except:
           dict_name['environements'][new_env]['points'][point_name] = {} 
        return

    def add_poi_by_params_cb(self,req):
        p = LabeledPose()
        p.name = req.name
        p.frame_id = req.frame_id
        p.environement = req.environement
        p.params = req.params

        quaternion = tf.transformations.quaternion_from_euler(req.roll,req.pitch,req.yaw)
        p.pose.position.x=req.x
        p.pose.position.y=req.y
        p.pose.position.z=req.z
        p.pose.orientation.x = quaternion[0]
        p.pose.orientation.y = quaternion[1]
        p.pose.orientation.z = quaternion[2]
        p.pose.orientation.w = quaternion[3]
        
        req_add_poi = AddPOIRequest()
        req_add_poi.p = p

        ret = self.add_poi_cb(req_add_poi)

        response = AddPOI_paramsResponse()

        response.success = ret.success
        response.message = ret.message

        return response
    
    def add_poi_cb(self,req):
        response = AddPOIResponse()
        print (req)
        try:
            self.try_create_env(self.pose_dict,req.p.environement)
            self.try_create_point(self.pose_dict,req.p.environement,req.p.name)
            point  = {'position':[req.p.pose.position.x,
                                req.p.pose.position.y,
                                req.p.pose.position.z],
                    'orientation':[req.p.pose.orientation.x,
                                    req.p.pose.orientation.y,
                                    req.p.pose.orientation.z,
                                    req.p.pose.orientation.w],
                    'frame_id':req.p.frame_id,
                    'params':req.p.params} 
            self.pose_dict['environements'][req.p.environement]['points'][req.p.name] = point
            success,msg=self.manage_read_data()
            if (success==False):
                response.success = False    
                response.message = "point %s from environement %s Not created/modified ERROR adding to pose list" % (req.p.name,req.p.environement )    
            response.success = True    
            response.message = "point %s from environement %s created/modified" % (req.p.name,req.p.environement )
            

        except Exception as identifier:
            msg = "%s::Error adding point %s from environement %s. Error msg:%s" % (rospy.get_name(),req.p.name,req.p.environement,identifier)
            response.success = True    
            response.message = msg  
        
        return response

