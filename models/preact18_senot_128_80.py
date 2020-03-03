# @Author: Liwen Zhang
# @Date: 2020/02/17
import os
import sys
BASE_DIR = os.path.dirname(__file__)
sys.path.append(BASE_DIR)
sys.path.append(os.path.join(BASE_DIR, 'utils'))
import tensorflow as tf
import numpy as np
import tf_util
import copy
import net_utils

def name_mapping(var_dict, debug=False):
    keys = var_dict.keys()
    mapped_dict = {}
    for k in keys:
        key = k.split(':0')[0]
        new_key = key
        if '/W' in key:
            new_key = key.replace('/W', '/weights')
        elif '/mean/EMA' in key:
            new_key = key.replace('/mean/EMA', '/moving_mean')
        elif '/variance/EMA' in key:
            new_key = key.replace('/variance/EMA', '/moving_variance')
        if 'bnlast' in new_key:
            new_key = new_key.replace('bnlast', 'block1/bnlast')
        mapped_dict[new_key] = var_dict[k]
    if debug:
        mapped_dict['fc/biases'] = var_dict['linear/b:0']
        mapped_dict['fc/weights'] = var_dict['linear/W:0']
    return mapped_dict

def convert_2d_3d(var_dict):
    keys = var_dict.keys()
    converted_dict = copy.deepcopy(var_dict)
    for k in keys:
        if 'weights' in k and 'conv' in k:
            W = var_dict[k]
            if len(W.shape) == 4:
                W = np.expand_dims(W, 0)
            converted_dict[k] = W
        if 'fc/weights' in k:
            W = var_dict[k]
            converted_dict[k] = W
    return converted_dict

def placeholder_inputs(batch_size, num_segs, freqbins, timebins, num_classes=10, mixup=False, evaluate=False):
    sequence_pl = tf.placeholder(tf.float32, shape=(batch_size, num_segs, freqbins, timebins, 3))
    if mixup:
        # for one-hot labels
        labels_pl = tf.placeholder(tf.float32, shape=(batch_size, num_classes))
    else:
        labels_pl = tf.placeholder(tf.int32, shape=(batch_size))
    return sequence_pl, labels_pl

def get_model(sequence, is_training, num_classes=10, bn_decay=0.999, weight_decay=0.0001, sn=4, pool_t=False, pool_first=False, freeze_bn=False):
    """ SeNot Net, input is BxTxHxWx3, output Bx10 """
    bsize = sequence.get_shape()[0].value
    end_points = {}

    channel_stride = [(64, 1), (128, 2), (256, 2), (512, 2)]
    # res block options
    num_blocks = [2, 2, 2, 2]
    topks = [None, sn, sn, None]
    shrink_ratios = [None, 2, None, None]

    net = tf_util.conv3d(sequence, 64, [1, 3, 3], stride=[1, 1, 1], bn=True, bn_decay=bn_decay, is_training=is_training, weight_decay=weight_decay, freeze_bn=freeze_bn, scope='conv0')
    net = tf_util.max_pool3d(net, [1, 3, 3], stride=[1, 2, 2], scope='pool0', padding='SAME')

    for gp, cs in enumerate(channel_stride):
        n_channels = cs[0]
        stride = cs[1]
        with tf.variable_scope('group{}'.format(gp)):
            for i in range(num_blocks[gp]):
                with tf.variable_scope('block{}'.format(i)):
                    end_points['res{}_{}_in'.format(gp, i)] = net
                    if i == 0:
                        net_bra = tf_util.conv3d(net, n_channels, [1, 3, 3], stride=[1, stride, stride], bn=True, bn_decay=bn_decay, \
                                is_training=is_training, weight_decay=weight_decay, freeze_bn=freeze_bn, scope='conv1')
                    else:
                        net_bra = tf_util.preact_bn_for_conv3d(net, is_training=is_training, bn_decay=bn_decay, \
                                                                scope='preact', freeze_bn=freeze_bn)
                        net_bra = tf_util.conv3d(net_bra, n_channels, [1, 3, 3], stride=[1, 1, 1], bn=True, bn_decay=bn_decay, \
                                is_training=is_training, weight_decay=weight_decay, freeze_bn=freeze_bn, scope='conv1')
                    net_bra = tf_util.conv3d(net_bra, n_channels, [1, 3, 3], stride=[1, 1, 1], bn=False, bn_decay=bn_decay, \
                            is_training=is_training, activation_fn=None, weight_decay=weight_decay, freeze_bn=freeze_bn, scope='conv2')
                    if net.get_shape()[-1].value != n_channels:
                        net = tf_util.conv3d(net, n_channels, [1, 1, 1], stride=[1, stride, stride], bn=False, bn_decay=bn_decay, \
                                is_training=is_training, activation_fn=None, weight_decay=weight_decay, freeze_bn=freeze_bn, scope='convshortcut')
                    net = net + net_bra
                    if i == 1:
                        net = tf_util.preact_bn_for_conv3d(net, is_training=is_training, bn_decay=bn_decay, \
                                                           scope='bnlast', freeze_bn=freeze_bn)
                    end_points['res{}_{}_mid'.format(gp, i)] = net
                    if topks[gp] is not None:
                        c = net.get_shape()[-1].value
                        net_pointnet, end_point = net_utils.senot_module(net, k=topks[gp], mlp=[c//4,c//2], scope='pointnet', is_training=is_training, bn_decay=bn_decay, \
                                weight_decay=weight_decay, distance='l2', activation_fn=None, freeze_bn=freeze_bn, shrink_ratio=shrink_ratios[gp])
                        net += net_pointnet
                        end_points['pointnet{}_{}'.format(gp, i)] = end_point
                        end_points['after_pointnet{}_{}'.format(gp, i)] = net
                    net = tf.nn.relu(net)
                    end_points['res{}_{}_out'.format(gp, i)] = net

    net = tf.reduce_mean(net, [1,2,3])
    net = tf_util.dropout(net, keep_prob=0.5, is_training=is_training, scope='dp')
    net = tf_util.fully_connected(net, num_classes, activation_fn=None, weight_decay=weight_decay, scope='fc')

    return net, end_points


def get_loss(pred, label, end_points):
    """ pred: B*NUM_CLASSES,
        label: B*NUM_CLASSES for one-hot, B, for normal labels"""
    # for one-hot labels
    if label.shape.ndims == 1:
        loss = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=pred, labels=label)
    else:
        single_label = tf.cast(tf.argmax(label, axis=1), tf.int32)
        '''loss = tf.losses.softmax_cross_entropy(
                label, pred, label_smoothing=0.,
                reduction=tf.losses.Reduction.NONE)'''
        loss = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=pred, labels=single_label)
    #loss = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=pred, labels=label)
    classify_loss = tf.reduce_mean(loss)
    tf.summary.scalar('classify loss', classify_loss)
    tf.add_to_collection('losses', classify_loss)
    return classify_loss


if __name__=='__main__':
    with tf.Graph().as_default():
        inputs = tf.zeros((16,8,128,80,3))
        net, _ = get_model(inputs, tf.constant(True))
        print(net)
