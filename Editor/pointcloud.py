import torch.nn as nn
import sys
import os
import pathlib
import argparse
import open3d as o3d
import torch.cuda
from plyfile import PlyData, PlyElement
import numpy as np
#np.set_printoptions(suppress=True)  # 取消默认科学计数法，open3d无法读取科学计数法表示
sys.path.append(os.path.join(pathlib.Path(__file__).parent.absolute(), '..'))
import cv2
from tqdm import tqdm


class Base_pointcloud:
    def __init__(self, opt):
        self.opt = opt
        self.edit_dir = os.path.join(opt.checkpoints_root, 'edit')
        if 'edit' not in os.listdir(opt.checkpoints_root):
            os.makedirs(os.path.join(self.edit_dir))
        self.xyz = []
        self.color = []
    def load_pointcloud(self):
        raise NotImplementedError()
    def save_pointcloud(self):
        raise NotImplementedError()
    def __len__(self):
        return len(self.xyz)

class Neural_pointcloud(Base_pointcloud):
    def __init__(self,opt):
        super().__init__(opt)
        self.embeding = []
        self.conf = []
        self.dir = []
        self.dirAux = []
        self.label = []
    '''
    checkpoints:从pth网络模型中读取
    ply:读取ply形式的点云信息，完备的
    meshlabfile:虽然也是ply形式的，但是失去了自定义的feature信息，需要人为的对其
    '''
    def load_from_checkpoints(self,points_xyz,points_embeding,points_conf,points_dirx,points_diry,points_dirz,points_color,points_label):
        self.xyz = points_xyz
        self.embeding = points_embeding
        self.conf = points_conf
        self.dirx = points_dirx
        self.diry = points_diry
        self.dirz = points_dirz
        self.color = points_color
        self.label = points_label
    def load_from_var(self,points_xyz,points_embeding,points_conf,points_dirx,points_diry,points_dirz,points_color,points_label):
        self.xyz = points_xyz
        self.embeding = points_embeding
        self.conf = points_conf
        self.dirx = points_dirx
        self.diry = points_diry
        self.dirz = points_dirz
        self.color = points_color
        self.label = points_label
    def load_from_ply(self,name='origin'):
        points_path = os.path.join(self.edit_dir,name+'_neuralpcd.ply')
        assert os.path.exists(points_path),'Load file doesn`t exist ,check!'
        print('loading neural point cloud from ply....')
        plydata = PlyData.read(points_path)

        r, g, b = np.array(plydata.elements[0].data["red"].astype(np.float32)), np.array(
            plydata.elements[0].data["green"].astype(np.float32)), np.array(
            plydata.elements[0].data["blue"].astype(np.float32))
        self.color = np.concatenate([r[..., np.newaxis], g[..., np.newaxis], b[..., np.newaxis]], axis=-1)
        x, y, z = np.array(plydata.elements[0].data["x"].astype(np.float32)), np.array(
            plydata.elements[0].data["y"].astype(np.float32)), np.array(
            plydata.elements[0].data["z"].astype(np.float32))
        self.xyz = np.concatenate([x[..., np.newaxis], y[..., np.newaxis], z[..., np.newaxis]], axis=-1)
        dirx0, dirx1, dirx2 = np.array(plydata.elements[0].data["dirx0"].astype(np.float32)), np.array(
            plydata.elements[0].data["dirx1"].astype(np.float32)), np.array(
            plydata.elements[0].data["dirx2"].astype(np.float32))
        self.dirx = np.concatenate([dirx0[..., np.newaxis], dirx1[..., np.newaxis], dirx2[..., np.newaxis]], axis=-1)
        diry0, diry1, diry2 = np.array(plydata.elements[0].data["diry0"].astype(np.float32)), np.array(
            plydata.elements[0].data["diry1"].astype(np.float32)), np.array(
            plydata.elements[0].data["diry2"].astype(np.float32))
        self.diry = np.concatenate([diry0[..., np.newaxis], diry1[..., np.newaxis], diry2[..., np.newaxis]], axis=-1)
        dirz0, dirz1, dirz2 = np.array(plydata.elements[0].data["dirz0"].astype(np.float32)), np.array(
            plydata.elements[0].data["dirz1"].astype(np.float32)), np.array(
            plydata.elements[0].data["dirz2"].astype(np.float32))
        self.dirz = np.concatenate([dirz0[..., np.newaxis], dirz1[..., np.newaxis], dirz2[..., np.newaxis]], axis=-1)
        self.conf = np.array(plydata.elements[0].data["conf"].astype(np.float32))
        self.label = np.array(plydata.elements[0].data["label"].astype(np.int32))
        embedding = []
        for i in range(56):
            embedding.append(np.array(plydata.elements[0].data["embeding"+str(i)].astype(np.float32))[...,np.newaxis])
        self.embeding =np.concatenate([embedding[0],embedding[1],embedding[2],embedding[3],embedding[4],embedding[5],embedding[6],embedding[7],embedding[8],embedding[9],embedding[10],embedding[11],embedding[12],embedding[13],embedding[14],embedding[15],embedding[16],embedding[17],embedding[18],embedding[19],embedding[20],embedding[21],embedding[22],embedding[23],embedding[24],embedding[25],embedding[26],embedding[27],embedding[28],embedding[29],embedding[30],embedding[31],embedding[32],embedding[33],embedding[34],embedding[35],embedding[36],embedding[37],embedding[38],embedding[39],embedding[40],embedding[41],embedding[42],embedding[43],embedding[44],embedding[45],embedding[46],embedding[47],embedding[48],embedding[49],embedding[50],embedding[51],embedding[52],embedding[53],embedding[54],embedding[55]],axis = -1)
        print('loading done. Scale of neural point cloud:',self.embeding.shape[0])
    def save_as_ply(self,name='origin_save'):
        assert self.xyz is not None, '[ERROR]Save before load,check it!'
        vertex = []
        print('Saving neural point cloud as ply...', self.xyz.shape)
        sv_xyz = self.xyz
        sv_color = self.color
        sv_embeding = self.embeding
        sv_conf = self.conf
        sv_dirx = self.dirx
        sv_diry = self.diry
        sv_dirz = self.dirz
        sv_label = self.label
        sv_dirAux = self.dirAux
        # sv_dir = self.points_dir.cpu().numpy()
        for i in tqdm(range(sv_xyz.shape[0])):
            vertex.append((
                sv_xyz[i][0],  # x
                sv_xyz[i][1],  # y
                sv_xyz[i][2],  # z
                sv_color[i][0],  # red
                sv_color[i][1],  # green
                sv_color[i][2],  # blue
                sv_conf[i],
                sv_dirx[i][0],
                sv_dirx[i][1],
                sv_dirx[i][2],
                sv_diry[i][0],
                sv_diry[i][1],
                sv_diry[i][2],
                sv_dirz[i][0],
                sv_dirz[i][1],
                sv_dirz[i][2],
                sv_embeding[i][0],
                sv_embeding[i][1],
                sv_embeding[i][2],
                sv_embeding[i][3],
                sv_embeding[i][4],
                sv_embeding[i][5],
                sv_embeding[i][6],
                sv_embeding[i][7],
                sv_embeding[i][8],
                sv_embeding[i][9],
                sv_embeding[i][10],
                sv_embeding[i][11],
                sv_embeding[i][12],
                sv_embeding[i][13],
                sv_embeding[i][14],
                sv_embeding[i][15],
                sv_embeding[i][16],
                sv_embeding[i][17],
                sv_embeding[i][18],
                sv_embeding[i][19],
                sv_embeding[i][20],
                sv_embeding[i][21],
                sv_embeding[i][22],
                sv_embeding[i][23],
                sv_embeding[i][24],
                sv_embeding[i][25],
                sv_embeding[i][26],
                sv_embeding[i][27],
                sv_embeding[i][28],
                sv_embeding[i][29],
                sv_embeding[i][30],
                sv_embeding[i][31],
                sv_embeding[i][32],
                sv_embeding[i][33],
                sv_embeding[i][34],
                sv_embeding[i][35],
                sv_embeding[i][36],
                sv_embeding[i][37],
                sv_embeding[i][38],
                sv_embeding[i][39],
                sv_embeding[i][40],
                sv_embeding[i][41],
                sv_embeding[i][42],
                sv_embeding[i][43],
                sv_embeding[i][44],
                sv_embeding[i][45],
                sv_embeding[i][46],
                sv_embeding[i][47],
                sv_embeding[i][48],
                sv_embeding[i][49],
                sv_embeding[i][50],
                sv_embeding[i][51],
                sv_embeding[i][52],
                sv_embeding[i][53],
                sv_embeding[i][54],
                sv_embeding[i][55],
                sv_label[i]
            ))
        #ply的格式，没写循环、增加可读性
        vertex = np.array(
            vertex,
            dtype=[
                ("x", np.dtype("float32")),
                ("y", np.dtype("float32")),
                ("z", np.dtype("float32")),
                ("red", np.dtype("float32")),
                ("green", np.dtype("float32")),
                ("blue", np.dtype("float32")),
                ("conf", np.dtype("float32")),
                ("dirx0", np.dtype("float32")),
                ("dirx1", np.dtype("float32")),
                ("dirx2", np.dtype("float32")),
                ("diry0", np.dtype("float32")),
                ("diry1", np.dtype("float32")),
                ("diry2", np.dtype("float32")),
                ("dirz0", np.dtype("float32")),
                ("dirz1", np.dtype("float32")),
                ("dirz2", np.dtype("float32")),
                ("embeding0", np.dtype("float32")),
                ("embeding1", np.dtype("float32")),
                ("embeding2", np.dtype("float32")),
                ("embeding3", np.dtype("float32")),
                ("embeding4", np.dtype("float32")),
                ("embeding5", np.dtype("float32")),
                ("embeding6", np.dtype("float32")),
                ("embeding7", np.dtype("float32")),
                ("embeding8", np.dtype("float32")),
                ("embeding9", np.dtype("float32")),
                ("embeding10", np.dtype("float32")),
                ("embeding11", np.dtype("float32")),
                ("embeding12", np.dtype("float32")),
                ("embeding13", np.dtype("float32")),
                ("embeding14", np.dtype("float32")),
                ("embeding15", np.dtype("float32")),
                ("embeding16", np.dtype("float32")),
                ("embeding17", np.dtype("float32")),
                ("embeding18", np.dtype("float32")),
                ("embeding19", np.dtype("float32")),
                ("embeding20", np.dtype("float32")),
                ("embeding21", np.dtype("float32")),
                ("embeding22", np.dtype("float32")),
                ("embeding23", np.dtype("float32")),
                ("embeding24", np.dtype("float32")),
                ("embeding25", np.dtype("float32")),
                ("embeding26", np.dtype("float32")),
                ("embeding27", np.dtype("float32")),
                ("embeding28", np.dtype("float32")),
                ("embeding29", np.dtype("float32")),
                ("embeding30", np.dtype("float32")),
                ("embeding31", np.dtype("float32")),
                ("embeding32", np.dtype("float32")),
                ("embeding33", np.dtype("float32")),
                ("embeding34", np.dtype("float32")),
                ("embeding35", np.dtype("float32")),
                ("embeding36", np.dtype("float32")),
                ("embeding37", np.dtype("float32")),
                ("embeding38", np.dtype("float32")),
                ("embeding39", np.dtype("float32")),
                ("embeding40", np.dtype("float32")),
                ("embeding41", np.dtype("float32")),
                ("embeding42", np.dtype("float32")),
                ("embeding43", np.dtype("float32")),
                ("embeding44", np.dtype("float32")),
                ("embeding45", np.dtype("float32")),
                ("embeding46", np.dtype("float32")),
                ("embeding47", np.dtype("float32")),
                ("embeding48", np.dtype("float32")),
                ("embeding49", np.dtype("float32")),
                ("embeding50", np.dtype("float32")),
                ("embeding51", np.dtype("float32")),
                ("embeding52", np.dtype("float32")),
                ("embeding53", np.dtype("float32")),
                ("embeding54", np.dtype("float32")),
                ("embeding55", np.dtype("float32")),
                ("label",np.dtype("uint8"))
            ]
        )
        ply_pc = PlyElement.describe(vertex, "vertex")
        ply_pc = PlyData([ply_pc])
        ply_pc.write(os.path.join(self.edit_dir, name+'_neuralpcd.ply'))
        print('Save done')
    def neuralpcd2meshlabpcd(self):
        '''
        just use meshlab gui to generate...
        '''
        raise NotImplementedError()

class Meshlab_pointcloud(Base_pointcloud):
    def __init__(self,opt):
        super().__init__(opt)

    def load_from_meshlabfile(self,name):
        points_path = os.path.join(self.edit_dir,name+'_meshlabpcd.ply')
        assert os.path.exists(points_path), 'Load file doesn`t exist ,check!'
        print('loading neural point cloud from ply....')
        plydata = PlyData.read(points_path)
        x, y, z = np.array(plydata.elements[0].data["x"].astype(np.float32)), np.array(
            plydata.elements[0].data["y"].astype(np.float32)), np.array(
            plydata.elements[0].data["z"].astype(np.float32))
        self.xyz = np.concatenate([x[..., np.newaxis], y[..., np.newaxis], z[..., np.newaxis]], axis=-1)
        # r, g, b = np.array(plydata.elements[0].data["red"].astype(np.float32)), np.array(
        #     plydata.elements[0].data["green"].astype(np.float32)), np.array(
        #     plydata.elements[0].data["blue"].astype(np.float32))
        # self.color = np.concatenate([r[..., np.newaxis], g[..., np.newaxis], b[..., np.newaxis]], axis=-1)
    def meshlabpcd2neuralpcd(self,scene_neural_pcd):
        '''
        Actually i dont know how to do that...
        I use every point in meshlabpcd to find the nearest pcd in neural_pcd
        '''
        # TODO: use cuda to reimplementation
        npc = Neural_pointcloud(self.opt)
        pointsize =self.xyz.shape[0]

        neural_xyz = np.empty([pointsize,3])
        neural_color = np.empty([pointsize,3])
        neural_embeding = np.empty([pointsize,56])
        neural_conf = np.empty([pointsize])
        neural_dirx = np.empty([pointsize,3])
        neural_diry = np.empty([pointsize,3])
        neural_dirz = np.empty([pointsize, 3])
        neural_label = np.empty([pointsize])
        print('Scale of neural point cloud :',len(scene_neural_pcd))
        print('Scale of meshlab point cloud:',pointsize)
        idx = 0
        for i in tqdm(range(scene_neural_pcd.xyz.shape[0])):
            neuralptr_xyz = scene_neural_pcd.xyz[i]
            dis = np.sqrt(np.sum(np.square(neuralptr_xyz-self.xyz),axis = -1))
            if  (dis < 1e-6).any():
                neural_xyz[idx] = scene_neural_pcd.xyz[i]
                neural_color[idx] = scene_neural_pcd.color[i]
                neural_embeding[idx] = scene_neural_pcd.embeding[i]
                neural_conf[idx] = scene_neural_pcd.conf[i]
                neural_dirx[idx] = scene_neural_pcd.dirx[i]
                neural_diry[idx] = scene_neural_pcd.diry[i]
                neural_dirz[idx] = scene_neural_pcd.dirz[i]
                neural_label[idx] = scene_neural_pcd.label[i]
                idx+=1
        print('\ncvt done...neural point cloud scale:',idx)
        npc.load_from_var(neural_xyz,neural_embeding,neural_conf,neural_dirx,neural_diry,neural_dirz,neural_color,neural_label)
        return npc



