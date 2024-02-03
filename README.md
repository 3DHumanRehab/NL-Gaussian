# NormLightGaussian: 3D Gaussian Splatting for Real lighting scene and Specular Object Reflection


## conda env
```
source activate
conda deactivate
conda activate gaussian_splatting
cd /root/NormLightGaussian

work_dir=/root
data_dir=$work_dir/NormLightGaussian/truck
model_dir=$work_dir/NormLightGaussian/model_out

```

## baseline model:

### only train (save model)
```
    python train.py -s $data_dir -m $model_dir --is_debug 1
```

### train with eval (don't save model)
```
    python train.py -s $data_dir -m $model_dir --eval --is_debug 1
```

### render and metric
```
python render.py -s $data_dir -m $model_dir
python metrics.py -m $model_dir
```


## model only with normal mlp:
```
    python train.py -s $data_dir -m $model_dir  \
        --use_norm_mlp 1 --is_debug 1
    python train.py -s $data_dir -m $model_dir --eval \
        --use_norm_mlp 1 --is_debug 1
    python render.py -s $data_dir -m $model_dir --use_norm_mlp 1
    python metrics.py -m $model_dir

```

## model only with densification:
```
    python train.py -s $data_dir -m $model_dir \
        --use_hierarchical 1 --densification_iter 15000 --densify_grad_scaling 0.25 0.5 1 2 4 \
        --use_hierarchical_split 1 --densify_split_N 2  --is_debug 1
    
    python render.py -s $data_dir -m $model_dir
```

## model with norm mlp and densification by norm grad:
```
    python train.py -s $data_dir -m $model_dir \
        --use_hierarchical 1 --densification_iter 15000 --densify_grad_scaling 0.25 0.5 1 2 4 \
        --use_hierarchical_split 1 --densify_split_N 2  \
        --use_norm_grads 1 --norm_grads_weight 0.1 --is_debug 1

    python render.py -s $data_dir -m $model_dir --use_norm_mlp 1
```



## evaluate pipeline :

```
    python evaluate_pipeline.py -s $data_dir -m $model_dir --eval \
        --eval_norm_mlp 1 \
        --eval_densification 1\
        --eval_norm_grads_weight 1
```





