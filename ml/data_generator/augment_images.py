import random
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from . import config

def apply_blur(img: np.ndarray, intensity: float = 1.0) -> np.ndarray:
    """Gaussian blur with kernel size based on intensity."""
    ksize = int(5 * intensity)
    if ksize % 2 == 0:
        ksize += 1
    return cv2.GaussianBlur(img, (ksize, ksize), 0)

def apply_rotation(img: np.ndarray, max_angle: float = 5.0) -> np.ndarray:
    """Small random rotation ±max_angle degrees."""
    angle = random.uniform(-max_angle, max_angle)
    h, w = img.shape[:2]
    center = (w / 2, h / 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), borderValue=(255, 255, 255))

def apply_brightness_up(img: np.ndarray, factor: float = 1.3) -> np.ndarray:
    """Increase brightness."""
    img_float = img.astype(np.float32) * factor
    return np.clip(img_float, 0, 255).astype(np.uint8)

def apply_brightness_down(img: np.ndarray, factor: float = 0.7) -> np.ndarray:
    """Decrease brightness."""
    img_float = img.astype(np.float32) * factor
    return np.clip(img_float, 0, 255).astype(np.uint8)

def apply_noise(img: np.ndarray, sigma: float = 15.0) -> np.ndarray:
    """Add Gaussian noise."""
    noise = np.random.normal(0, sigma, img.shape)
    img_noisy = img.astype(np.float32) + noise
    return np.clip(img_noisy, 0, 255).astype(np.uint8)

def apply_jpeg_compression(img: np.ndarray, quality: int = 30) -> np.ndarray:
    """Simulate JPEG compression artifacts."""
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    result, encimg = cv2.imencode('.jpg', img, encode_param)
    if result:
        return cv2.imdecode(encimg, 1)
    return img

def apply_perspective_distortion(img: np.ndarray, magnitude: float = 0.02) -> np.ndarray:
    """Apply slight perspective warp."""
    h, w = img.shape[:2]
    pts1 = np.float32([[0, 0], [w, 0], [0, h], [w, h]])
    
    # Random offsets for the 4 corners
    dx1, dy1 = random.uniform(-magnitude, magnitude) * w, random.uniform(-magnitude, magnitude) * h
    dx2, dy2 = random.uniform(-magnitude, magnitude) * w, random.uniform(-magnitude, magnitude) * h
    dx3, dy3 = random.uniform(-magnitude, magnitude) * w, random.uniform(-magnitude, magnitude) * h
    dx4, dy4 = random.uniform(-magnitude, magnitude) * w, random.uniform(-magnitude, magnitude) * h
    
    pts2 = np.float32([
        [0 + dx1, 0 + dy1],
        [w + dx2, 0 + dy2],
        [0 + dx3, h + dy3],
        [w + dx4, h + dy4]
    ])
    
    M = cv2.getPerspectiveTransform(pts1, pts2)
    return cv2.warpPerspective(img, M, (w, h), borderValue=(255, 255, 255))

def augment_image(img: np.ndarray, augmentation_type: str) -> np.ndarray:
    """Apply a single named augmentation."""
    if augmentation_type == 'blur':
        return apply_blur(img)
    elif augmentation_type == 'rotation':
        return apply_rotation(img)
    elif augmentation_type == 'brightness_up':
        return apply_brightness_up(img)
    elif augmentation_type == 'brightness_down':
        return apply_brightness_down(img)
    elif augmentation_type == 'noise':
        return apply_noise(img)
    elif augmentation_type == 'jpeg_compression':
        return apply_jpeg_compression(img)
    elif augmentation_type == 'perspective':
        return apply_perspective_distortion(img)
    else:
        return img

def augment_all_images(
    source_dir: Path,
    output_dir: Path,
    augmentations_per_image: int = config.AUGMENTATIONS_PER_IMAGE,
    seed: int = config.DEFAULT_SEED,
) -> list[dict]:
    """Find all PNG images in source_dir (recursively), apply random augmentations."""
    random.seed(seed)
    np.random.seed(seed)
    
    metadata = []
    
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)
    
    for img_path in source_dir.rglob('*.png'):
        rel_path = img_path.relative_to(source_dir)
        
        # Load image with PIL (RGB) and convert to cv2 (BGR)
        pil_img = Image.open(img_path).convert('RGB')
        img_bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        
        chosen_augs = random.sample(config.AUGMENTATION_TYPES, min(augmentations_per_image, len(config.AUGMENTATION_TYPES)))
        
        for aug_type in chosen_augs:
            aug_bgr = augment_image(img_bgr, aug_type)
            
            # Convert back to PIL (RGB)
            aug_rgb = cv2.cvtColor(aug_bgr, cv2.COLOR_BGR2RGB)
            aug_pil = Image.fromarray(aug_rgb)
            
            # Formulate output path
            out_filename = f"{img_path.stem}_aug_{aug_type}.png"
            out_rel_dir = rel_path.parent
            out_full_dir = output_dir / out_rel_dir
            out_full_dir.mkdir(parents=True, exist_ok=True)
            
            out_path = out_full_dir / out_filename
            aug_pil.save(out_path)
            
            metadata.append({
                "source_image": str(img_path),
                "augmented_image": str(out_path),
                "augmentation_type": aug_type
            })
            
    return metadata
