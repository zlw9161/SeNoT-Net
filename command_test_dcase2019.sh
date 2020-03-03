#!/bin/sh
set -x #echo on
export PYTHONPATH=$PYTHONPATH:$1

command_file=`basename "$0"`
script_file=test.py
gpu=0
data=/mnt/data/datasets/dcase2019/dev/task1a
model=resnet18_senot_128_80
model_path=/mnt/data/SeNoT-Net/log_dcase_resnet18_senot_128_80_8_train/model-100.ckpt
num_threads=6
num_segs=8
timebins=80
freqbins=128
num_classes=10
sn=4
fcn=0
dump_dir=log_dcase_resnet18_senot_128_80_8_sn${sn}_test
log_file=$dump_dir.txt


python3 $script_file \
    --gpu $gpu \
    --data $data \
    --model $model \
    --model_path $model_path \
    --num_threads $num_threads \
    --num_segs $num_segs \
    --timebins $timebins \
    --freqbins $freqbins \
    --num_classes $num_classes \
    --sn $sn \
    --dump_dir $dump_dir \
    --fcn $fcn \
    --command_file $command_file \
    > $log_file 2>&1 &
