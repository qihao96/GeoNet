# Mostly based on the code written by Tinghui Zhou & Clement Godard:
# https://github.com/tinghuiz/SfMLearner/blob/master/data_loader.py
# https://github.com/mrharicot/monodepth/blob/master/monodepth_dataloader.py
from __future__ import division
import os
import random
import tensorflow as tf


class DataLoader(object):
    def __init__(self, opt=None):
        self.opt = opt

    # function called by main
    def load_train_val_batch(self, mode="train"):
        """Load a batch of training or validation instances.
        """
        opt = self.opt

        # Load the list of training files into queues
        file_list = self.format_file_list(opt.dataset_dir, opt.semantic_dataset_dir, split="train")

        # file_list['image_file_list']
        # '/userhome/34/h3567721/dataset/kitti/kitti_raw_eigen/2011_09_30_drive_0034_sync_03/0000000558.jpg'

        # file_list['sem_file_list']
        # '/userhome/34/h3567721/dataset/kitti/kitti_raw_eigen_seg/mask/2011_09_30_drive_0034_sync_03/0000000558.jpg'

        # file_list['cam_file_list']
        # '/userhome/34/h3567721/dataset/kitti/kitti_raw_eigen/2011_09_30_drive_0034_sync_03/0000000558_cam.txt'

        image_paths_queue = tf.train.string_input_producer(file_list['image_file_list'], shuffle=False)
        sem_paths_queue = tf.train.string_input_producer(file_list['sem_file_list'], shuffle=False)
        cam_paths_queue = tf.train.string_input_producer(file_list['cam_file_list'], shuffle=False)

        # ------------------------------------------------------
        # Load images
        img_reader = tf.WholeFileReader()
        _, image_contents = img_reader.read(image_paths_queue)
        image_seq = tf.image.decode_jpeg(image_contents)

        # Load sem
        sem_reader = tf.WholeFileReader()
        _, sem_contents = sem_reader.read(sem_paths_queue)
        # binary mask is grayscale data, but to make it smaple
        # by reusing RGB image's processing function.
        # to make it 3 channels, same value in each channel
        sem_seq = tf.image.decode_jpeg(sem_contents, channels=3)
        
        # ------------------------------------------------------
        # tgt_image: (128, 416, 3)
        # src_image_stack: (128, 416, 6)
        tgt_image, src_image_stack = self.unpack_image_sequence(
            image_seq, opt.img_height, opt.img_width, opt.num_source)

        # same unpack function, from 1248x128 -> (128,416,3) + (128,416,6)
        tgt_sem, src_sem_stack = self.unpack_image_sequence(
            sem_seq, opt.img_height, opt.img_width, opt.num_source)

        # ------------------------------------------------------
        # Load camera intrinsics
        cam_reader = tf.TextLineReader()
        _, raw_cam_contents = cam_reader.read(cam_paths_queue)

        rec_def = []
        for i in range(9):
            rec_def.append([1.])

        # rec_def: [[1.0], [1.0], [1.0], [1.0], [1.0], [1.0], [1.0], [1.0], [1.0]]

        raw_cam_vec = tf.io.decode_csv(raw_cam_contents,
                                    record_defaults=rec_def)
        raw_cam_vec = tf.stack(raw_cam_vec)
        intrinsics = tf.reshape(raw_cam_vec, [3, 3])

        # ------------------------------------------------------

        # Form training batches
        seed = random.randint(0, 2**31 - 1)

        min_after_dequeue = 2048
        # 2048 * 32 * 4 = 262144
        capacity = min_after_dequeue + opt.num_threads * opt.batch_size

        # src_image_stack: (4,128,416,6)
        # tgt_image: (4,128,416,3)
        # intrinsics: (4,3,3)

        if mode == "train":
            src_image_stack, tgt_image, src_sem_stack, tgt_sem, intrinsics = \
                tf.train.shuffle_batch([src_image_stack, tgt_image, src_sem_stack, tgt_sem, intrinsics], opt.batch_size,
                                    capacity, min_after_dequeue, opt.num_threads, seed)
        else:
            src_image_stack, tgt_image, intrinsics = \
                tf.train.batch([src_image_stack, tgt_image, intrinsics], opt.batch_size,
                                opt.num_threads,capacity)

        if mode == "train":
            # Data augmentation
            print("load_train_val_batch: Doing data augmentation")
            # NOTE: Enhance same data augmentation except random coloring
            image_all = tf.concat([tgt_image, src_image_stack, tgt_sem, src_sem_stack], axis=3)

            color_img, sem_img, intrinsics = self.data_augmentation(
                image_all, intrinsics, opt.img_height, opt.img_width)

            tgt_image = color_img[:, :, :, :3]  # (4,128,416,3)
            src_image_stack = color_img[:, :, :, 3:]  # (4,128,416,6)
            tgt_sem = sem_img[:, :, :, :3] # (4,128,416,3)
            src_sem_stack = sem_img[:, :, :, 3:] # (4,128,416,6)

            # intrinsics_mscale (4,4,3,3)
            intrinsics = self.get_multi_scale_intrinsics(
                intrinsics, opt.num_scales)
        else:
            print("load_train_val_batch: No augmentation in evalution")
            pass

        return tgt_image, src_image_stack, tgt_sem, src_sem_stack, intrinsics

    def format_file_list(self, data_root, sem_root, split):
        with open(data_root + '/%s.txt' % split, 'r') as f:
            frames = f.readlines()

        subfolders = [x.split(' ')[0] for x in frames]
        frame_ids = [x.split(' ')[1][:-1] for x in frames]

        image_file_list = [os.path.join(data_root, subfolders[i],
                                        frame_ids[i] + '.jpg') for i in range(len(frames))]

        sem_file_list = [os.path.join(sem_root, subfolders[i],
                                        frame_ids[i] + '.jpg') for i in range(len(frames))]

        cam_file_list = [os.path.join(data_root, subfolders[i],
                                      frame_ids[i] + '_cam.txt') for i in range(len(frames))]

        all_list = {}
        all_list['image_file_list'] = image_file_list
        all_list['sem_file_list'] = sem_file_list
        all_list['cam_file_list'] = cam_file_list

        return all_list

    def unpack_image_sequence(self, image_seq, img_height, img_width, num_source):
        # Assuming the center image is the target frame
        tgt_start_idx = int(img_width * (num_source//2))
        tgt_image = tf.slice(image_seq,
                             [0, tgt_start_idx, 0],
                             [-1, img_width, -1])

        # Source frames before the target frame
        src_image_1 = tf.slice(image_seq,
                               [0, 0, 0],
                               [-1, int(img_width * (num_source//2)), -1])

        # Source frames after the target frame
        src_image_2 = tf.slice(image_seq,
                               [0, int(tgt_start_idx + img_width), 0],
                               [-1, int(img_width * (num_source//2)), -1])

        src_image_seq = tf.concat([src_image_1, src_image_2], axis=1)

        # Stack source frames along the color channels (i.e. [H, W, N*3])
        src_image_stack = tf.concat([tf.slice(src_image_seq,
                                              [0, i*img_width, 0],
                                              [-1, img_width, -1])
                                     for i in range(num_source)], axis=2)

        src_image_stack.set_shape([img_height,
                                   img_width,
                                   num_source * 3])

        tgt_image.set_shape([img_height, img_width, 3])

        return tgt_image, src_image_stack

    def get_multi_scale_intrinsics(self, intrinsics, num_scales):
        # num_scales = 4
        intrinsics_mscale = []
        # Scale the intrinsics accordingly for each scale
        # 2**0=1, 2**1=2, 2**3=8, 2**4=16
        for s in range(num_scales):
            fx = intrinsics[:, 0, 0]/(2 ** s)
            fy = intrinsics[:, 1, 1]/(2 ** s)
            cx = intrinsics[:, 0, 2]/(2 ** s)
            cy = intrinsics[:, 1, 2]/(2 ** s)
            intrinsics_mscale.append(
                self.make_intrinsics_matrix(fx, fy, cx, cy))

        intrinsics_mscale = tf.stack(intrinsics_mscale, axis=1)

        return intrinsics_mscale

    def make_intrinsics_matrix(self, fx, fy, cx, cy):
        # Assumes batch input
        batch_size = fx.get_shape().as_list()[0]  # 4
        zeros = tf.zeros_like(fx)
        r1 = tf.stack([fx, zeros, cx], axis=1)
        r2 = tf.stack([zeros, fy, cy], axis=1)
        r3 = tf.constant([0., 0., 1.], shape=[1, 3])
        r3 = tf.tile(r3, [batch_size, 1])
        intrinsics = tf.stack([r1, r2, r3], axis=1)  # (4,3,3)

        return intrinsics

    def data_augmentation(self, im, intrinsics, out_h, out_w):
        # Random scaling
        def random_scaling(im, intrinsics):
            batch_size, in_h, in_w, _ = im.get_shape().as_list()
            scaling = tf.random.uniform([2], 1, 1.15)
            x_scaling = scaling[0]
            y_scaling = scaling[1]
            out_h = tf.cast(in_h * y_scaling, dtype=tf.int32)
            out_w = tf.cast(in_w * x_scaling, dtype=tf.int32)
            im = tf.compat.v1.image.resize_area(im, [out_h, out_w])
            fx = intrinsics[:, 0, 0] * x_scaling
            fy = intrinsics[:, 1, 1] * y_scaling
            cx = intrinsics[:, 0, 2] * x_scaling
            cy = intrinsics[:, 1, 2] * y_scaling
            intrinsics = self.make_intrinsics_matrix(fx, fy, cx, cy)

            return im, intrinsics

        # Random cropping
        def random_cropping(im, intrinsics, out_h, out_w):
            # batch_size, in_h, in_w, _ = im.get_shape().as_list()
            batch_size, in_h, in_w, _ = tf.unstack(tf.shape(im))
            offset_y = tf.random.uniform(
                [1], 0, in_h - out_h + 1, dtype=tf.int32)[0]
            offset_x = tf.random.uniform(
                [1], 0, in_w - out_w + 1, dtype=tf.int32)[0]
            im = tf.image.crop_to_bounding_box(
                im, offset_y, offset_x, out_h, out_w)
            fx = intrinsics[:, 0, 0]
            fy = intrinsics[:, 1, 1]
            cx = intrinsics[:, 0, 2] - tf.cast(offset_x, dtype=tf.float32)
            cy = intrinsics[:, 1, 2] - tf.cast(offset_y, dtype=tf.float32)
            intrinsics = self.make_intrinsics_matrix(fx, fy, cx, cy)

            return im, intrinsics

        # Random coloring
        def random_coloring(im):
            batch_size, in_h, in_w, in_c = im.get_shape().as_list()
            im_f = tf.image.convert_image_dtype(im, tf.float32)

            # randomly shift gamma
            random_gamma = tf.random.uniform([], 0.8, 1.2)
            im_aug = im_f ** random_gamma

            # randomly shift brightness
            random_brightness = tf.random.uniform([], 0.5, 2.0)
            im_aug = im_aug * random_brightness

            # randomly shift color
            random_colors = tf.random.uniform([in_c], 0.8, 1.2)
            white = tf.ones([batch_size, in_h, in_w])
            color_image = tf.stack([white * random_colors[i]
                                    for i in range(in_c)], axis=3)
            im_aug *= color_image

            # saturate
            im_aug = tf.clip_by_value(im_aug,  0, 1)

            im_aug = tf.image.convert_image_dtype(im_aug, tf.uint8)

            return im_aug

        im, intrinsics = random_scaling(im, intrinsics)
        im, intrinsics = random_cropping(im, intrinsics, out_h, out_w)
        im = tf.cast(im, dtype=tf.uint8)

        do_augment = tf.random.uniform([], 0, 1)
        color_img = im[:, :, :, :9] # (tgt_image, src_image_stack)
        color_img = tf.cond(do_augment > 0.5, lambda: random_coloring(color_img), lambda: color_img)

        # NOTE: No random_coloring for sem
        sem_img = im[:, :, :, 9:] # (tgt_sem, src_sem_stack)

        return color_img, sem_img, intrinsics