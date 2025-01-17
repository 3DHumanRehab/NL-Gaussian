
import torch
import math
from diff_gaussian_rasterization import GaussianRasterizationSettings, GaussianRasterizer
from scene.gaussian_model import GaussianModel 
from utils.sh_utils import eval_sh 

def render(viewpoint_camera, pc : GaussianModel, pipe, bg_color : torch.Tensor,
           use_norm_mlp,use_cosine,use_specular, scaling_modifier = 1.0, override_color = None):
    """
    Render the scene. 
    
    Background tensor (bg_color) must be on GPU!
    """
 
    # Create zero tensor. We will use it to make pytorch return gradients of the 2D (screen-space) means
    screenspace_points = torch.zeros_like(pc.get_xyz, dtype=pc.get_xyz.dtype, requires_grad=True, device="cuda") + 0
    norm= None
    try:
        screenspace_points.retain_grad()
    except:
        pass

    # Set up rasterization configuration
    tanfovx = math.tan(viewpoint_camera.FoVx * 0.5)
    tanfovy = math.tan(viewpoint_camera.FoVy * 0.5)

    raster_settings = GaussianRasterizationSettings(
        image_height=int(viewpoint_camera.image_height),
        image_width=int(viewpoint_camera.image_width),
        tanfovx=tanfovx,
        tanfovy=tanfovy,
        bg=bg_color,
        scale_modifier=scaling_modifier,
        viewmatrix=viewpoint_camera.world_view_transform,
        projmatrix=viewpoint_camera.full_proj_transform,
        sh_degree=pc.active_sh_degree,
        campos=viewpoint_camera.camera_center,
        prefiltered=False,
        debug=pipe.debug
    )

    rasterizer = GaussianRasterizer(raster_settings=raster_settings)

    means3D = pc.get_xyz
    means2D = screenspace_points
    opacity = pc.get_opacity

    # If precomputed 3d covariance is provided, use it. If not, then it will be computed from
    # scaling / rotation by the rasterizer.
    scales = None
    rotations = None
    cov3D_precomp = None
    
    
    if pipe.compute_cov3D_python:
        cov3D_precomp = pc.get_covariance(scaling_modifier)
    else:
        scales = pc.get_scaling
        rotations = pc.get_rotation

    # If precomputed colors are provided, use them. Otherwise, if it is desired to precompute colors
    # from SHs in Python, do it. If not, then SH -> RGB conversion will be done by rasterizer.
    shs = None
    colors_precomp = None
    
    pipe.convert_SHs_python=False
    if use_norm_mlp:
        pipe.convert_SHs_python=True
    
    if override_color is None:
        if pipe.convert_SHs_python:
            
            if use_norm_mlp:
                xyz_normlized=pc.get_xyz/pc.get_xyz.norm(dim=1, keepdim=True)
                diffuse = eval_sh(pc.active_sh_degree, pc.get_features.transpose(1, 2).view(-1, 3, (pc.max_sh_degree+1)**2),xyz_normlized )
                wo = (pc.get_xyz - viewpoint_camera.camera_center.repeat(pc.get_features.shape[0], 1))
                wo_normalized = wo/wo.norm(dim=1, keepdim=True)
                norm = eval_sh(pc.active_sh_degree, pc.get_features_norm.transpose(1, 2).view(-1, 3, (pc.max_sh_degree+1)**2), wo_normalized)
                norm_normalized=norm/norm.norm(dim=1, keepdim=True)
                wi_normalized = -wo_normalized + 2 * torch.sum(torch.mul(norm_normalized,wo_normalized),dim=1).reshape([-1,1]) * norm_normalized
                rgb=diffuse
                if use_cosine:
                    cosine=torch.clamp_min(norm_normalized*wi_normalized,0.0)
                    rgb=rgb*cosine
                if use_specular:
                    inlight = eval_sh(pc.active_sh_degree, pc.get_features_inlight.transpose(1, 2).view(-1, 3, (pc.max_sh_degree+1)**2),wi_normalized)
                    rgb=(1-pc.get_specular_coef)*rgb+pc.get_specular_coef*inlight
            else:
                xyz_normlized=pc.get_xyz/pc.get_xyz.norm(dim=1, keepdim=True)
                dir_pp = (pc.get_xyz - viewpoint_camera.camera_center.repeat(pc.get_features.shape[0], 1))
                dir_pp_normalized = dir_pp/dir_pp.norm(dim=1, keepdim=True)
                rgb = eval_sh(pc.active_sh_degree, pc.get_features.transpose(1, 2).view(-1, 3, (pc.max_sh_degree+1)**2), dir_pp_normalized)

            colors_precomp = torch.clamp_min(rgb + 0.5, 0.0)
            
        else:
            shs = pc.get_features
    else:
        colors_precomp = override_color

    # Rasterize visible Gaussians to image, obtain their radii (on screen). 
    rendered_image, radii = rasterizer(
        means3D = means3D,
        means2D = means2D,
        shs = shs,
        colors_precomp = colors_precomp,
        opacities = opacity,
        scales = scales,
        rotations = rotations,
        cov3D_precomp = cov3D_precomp)

    # Those Gaussians that were frustum culled or had a radius of 0 were not visible.
    # They will be excluded from value updates used in the splitting criteria.
    return {"render": rendered_image,
            "viewspace_points": screenspace_points,
            "norm": norm ,
            "visibility_filter" : radii > 0,
            "radii": radii}
