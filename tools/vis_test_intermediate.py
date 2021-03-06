import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def view_idx(file_name):
    # delta is empty in original geonet prediction
    depth = np.load(os.path.join(depth_path, file_name))
    delta = np.ones((1,128,416,12))
    
    tgt = np.load(os.path.join(tgt_path, file_name))
    src = np.load(os.path.join(src_path, file_name))
    
    bwd_rigid_error = np.load(os.path.join(bwd_rigid_error_path, file_name))
    fwd_rigid_error = np.load(os.path.join(fwd_rigid_error_path, file_name))

    bwd_rigid_warp = np.load(os.path.join(bwd_rigid_warp_path, file_name))
    fwd_rigid_warp = np.load(os.path.join(fwd_rigid_warp_path, file_name))
 
    plt.figure(figsize=(18,18))
    plt.subplot(6,3,1)
    plt.imshow((src[0,:,:,0:3]+1)/2)
    plt.title("src_1")

    plt.subplot(6,3,2)
    plt.imshow((tgt[0,:,:,:]+1)/2)
    plt.title("tgt")

    plt.subplot(6,3,3)
    plt.imshow((src[0,:,:,3:6]+1)/2)
    plt.title("src_2")

    # depth[tgt, src_1, src_2]
    plt.subplot(6,3,4)
    plt.imshow(1.0/depth[1,:,:,0], cmap="plasma")
    plt.title("src_1_depth")

    plt.subplot(6,3,5)
    plt.imshow(1.0/depth[0,:,:,0], cmap="plasma")
    plt.title("tgt_depth")

    plt.subplot(6,3,6)
    plt.imshow(1.0/depth[2,:,:,0], cmap="plasma")
    plt.title("src_2_depth")

    plt.subplot(6,3,7)
    plt.imshow((fwd_rigid_warp[0]+1)/2)
    plt.title("fwd warp: src_1->tgt")

    plt.subplot(6,3,8)
    plt.imshow((fwd_rigid_warp[1]+1)/2)
    plt.title("fwd warp: src_2->tgt")

    plt.subplot(6,3,9)
    plt.imshow(delta[0][:,:,0:3]*scale)
    plt.title("delta tgt->src_1")

    plt.subplot(6,3,10)
    plt.imshow((bwd_rigid_warp[0]+1)/2)
    plt.title("bwd warp: tgt->src_1")

    plt.subplot(6,3,11)
    plt.imshow((bwd_rigid_warp[1]+1)/2)
    plt.title("bwd warp: tgt->src_2")

    plt.subplot(6,3,12)
    plt.imshow(delta[0][:,:,3:6]*scale)
    plt.title("delta: tgt->src_2")

    plt.subplot(6,3,13)
    plt.imshow(fwd_rigid_error[0])
    plt.title("fwd err: src_1->tgt vs tgt")

    plt.subplot(6,3,14)
    plt.imshow(fwd_rigid_error[1])
    plt.title("fwd err: src_2->tgt vs tgt")

    plt.subplot(6,3,15)
    plt.imshow(delta[0][:,:,6:9]*scale)
    plt.title("delta: src_1->tgt")

    plt.subplot(6,3,16)
    plt.imshow(bwd_rigid_error[0])
    plt.title("bwd err: tgt->src_1 vs src_1")

    plt.subplot(6,3,17)
    plt.imshow(bwd_rigid_error[1])
    plt.title("bwd err: tgt->src_2 vs sr_2")

    plt.subplot(6,3,18)
    plt.imshow(delta[0][:,:,9:12]*scale)
    plt.title("delta: src_2->tgt")

    plt.show()

    plt.savefig(vis_save_path)

    plt.close()


def make_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


if __name__ == "__main__":
    base_path = "/userhome/34/h3567721/projects/Depth/GeoNet-ori/predictions/checkpoint_depth"

    tgt_path = os.path.join(base_path, "tgt_image") # 1
    src_path = os.path.join(base_path, "src_image_stack") # 2
    depth_path = os.path.join(base_path, "depth") # 3

    bwd_rigid_error_path = os.path.join(base_path, "bwd_rigid_error") # 2
    fwd_rigid_error_path = os.path.join(base_path, "fwd_rigid_error") # 2
    bwd_rigid_warp_path = os.path.join(base_path, "bwd_rigid_warp") # 2
    fwd_rigid_warp_path = os.path.join(base_path, "fwd_rigid_warp") # 2

    var_names = os.listdir(depth_path) 
    scale = 20

    make_dir(os.path.join(base_path, "plot"))

    for i in range(len(var_names)):
        vis_save_path = os.path.join(base_path, "plot", var_names[i].replace("npy", "png"))
        view_idx(var_names[i])