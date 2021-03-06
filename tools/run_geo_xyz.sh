# depth xyz
export CUDA_VISIBLE_DEVICES=0
user_path="/userhome/34/h3567721"

python geonet_main.py \
    --mode=train_rigid \
    --dataset_dir=$user_path"/dataset/kitti/kitti_raw_eigen" \
    --checkpoint_dir=$user_path"/projects/Depth/GeoNet/checkpoint/depth_geo_delta_sigmoid_minus_0.5_scale_5" \
    --learning_rate=0.0002 \
    --seq_length=3 \
    --batch_size=4 \
    --max_steps=350001 \
    --delta_mode \
    --max_to_keep=40

# ---------------------------------------------------------------------------------------------------------------------------

python geonet_main_semantic.py \
    --mode=train_rigid \
    --dataset_dir=$user_path"/dataset/kitti/kitti_raw_eigen" \
    --semantic_dataset_dir=$user_path"/dataset/kitti/kitti_raw_eigen_seg/mask" \
    --checkpoint_dir=$user_path"/projects/Depth/GeoNet/checkpoint/depth_geo_delta_sigmoid_minus_0.5_scale_5_semantic" \
    --learning_rate=0.0002 \
    --seq_length=3 \
    --batch_size=4 \
    --max_steps=350001 \
    --delta_mode \
    --max_to_keep=40
