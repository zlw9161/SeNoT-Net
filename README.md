# SeNoT-Net
Learning temporal relations from semantic neighbors for DCASE2018/2019 ASC Task

If you find our work useful in your research, please cite:

        @article{Zhang:2020:senot-net,
          title={Learning temporal relations from semantic neighbors for Acoustic Scene Classification},
          author={Liwen Zhang, Jiqing Han and Ziqiang Shi},
          journal={submitted to IEEE Signal Processing Letters on Mar. 10, 2020},
          year={2020}
        }

## Setup
1. tensorflow > 1.9.0
2. dataflow --> tensorpack 
link: https://github.com/tensorpack

## Description

### 1. Training/testing/evaluating sh scripts:
usage: sh command_train(evaluate/test)_dcase2019.sh

### 2. Data preparation:
Use sequence_generation.py to produce Log-Mel spec sequence for each audio wav data.
The ./utils/dataloader.py script is used to load the generated sequence into the network. It is implemented by using the interface "datasets" of tensorpack. The dataset class declarition is in ./utils/datasets/SpecAudioDataset.py.

### 3. Pretrained models:
The pretrained models are in the ./pretrained_models. We modified the example of ResNet for ImageNet in https://github.com/tensorpack/tensorpack/tree/master/examples/ResNet to get the pretrained 2D ResNet-18 and PreAct-18.

### 4. Transform ResNet-18 into SeNoT-Net:
The SeNoT-Net definition is in ./models/resnet18_senot_128_80.py, which will load the pre-trained models and transform them into SeNoT-Nets by calling the methods in ./tf_utils.py.

### 5. SeNoT module:
The Semantic Neighbor Selector (SeNS) is worked as an operation in the SeNoT-Net. The codes are in the ./tf_ops.
This operation is modified from the CPNet in https://github.com/xingyul/cpnet.

### 6. Train/test the model:
Use ./train.py and ./test.py to train and test the model.

### 7. References
* <a href="https://ieeexplore.ieee.org/document/8960462" target="_blank">Pyramidal Temporal Pooling With Discriminative Mapping for Audio Classification
</a> by Zhang et al. (IEEE Trans. ASLP). Code and data released in <a href="https://github.com/zlw9161/PyramidalTemporalPooling">GitHub</a>.
* <a href="http://arxiv.org/abs/1905.07853" target="_blank">Learning Video Representations from Correspondence Proposals
</a> by Liu et al. (CVPR 2019). Code and data released in <a href="https://github.com/xingyul/cpnet">GitHub</a>.
* <a href="http://stanford.edu/~rqi/pointnet" target="_blank">PointNet: Deep Learning on Point Sets for 3D Classification and Segmentation</a> by Qi et al. (CVPR 2017 Oral Presentation). Code and data released in <a href="https://github.com/charlesq34/pointnet">GitHub</a>.
