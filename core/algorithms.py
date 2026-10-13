import numpy as np
from PIL import Image, ImageFilter

AVAILABLE_ALGORITHMS = {
    "scale2x": {
        "name": "Scale2x / EPX (Smart Pixel Art)",
        "factor": 2,
        "description": "Glättet stufenförmige Pixelkanten und Rundungen ohne Farbverfälschung oder Unschärfe."
    },
    "scale3x": {
        "name": "Scale3x / AdvMAME3x (Smart Pixel Art 3x)",
        "factor": 3,
        "description": "Dreifache Vergrößerung mit EPX3x Glättung für Pixel Art."
    },
    "scale4x": {
        "name": "Scale4x (Smart Pixel Art 4x)",
        "factor": 4,
        "description": "Vierfache Vergrößerung (zwei Durchläufe Scale2x) für 64x64 HD Texturen."
    },
    "nearest": {
        "name": "Nearest Neighbor (Pixel Perfect)",
        "factor": 2,
        "description": "Exakte 1:1 Beibehaltung der Pixel ohne jegliche Glättung."
    },
    "lanczos": {
        "name": "Lanczos (Glatt mit Unschärfemaske)",
        "factor": 2,
        "description": "Weiche bikubische Interpolation mit Kantenbetonung."
    },
    "bicubic": {
        "name": "Bicubic (Weich)",
        "factor": 2,
        "description": "Standardmäßige weiche Vergrößerung."
    }
}

def pixel_eq(p1: np.ndarray, p2: np.ndarray) -> np.ndarray:
    """
    Checks pixel equality taking transparency into account.
    Two transparent pixels (alpha == 0) are considered identical.
    Two visible pixels must match in all channels (RGBA).
    """
    if p1.shape[-1] == 4 and p2.shape[-1] == 4:
        trans1 = (p1[..., 3] == 0)
        trans2 = (p2[..., 3] == 0)
        both_trans = trans1 & trans2
        all_match = np.all(p1 == p2, axis=-1)
        return both_trans | all_match
    return np.all(p1 == p2, axis=-1)

def scale2x_epx(arr: np.ndarray) -> np.ndarray:
    """
    Vectorized Scale2x / EPX algorithm.
    Doubles resolution (2x).
    """
    H, W, C = arr.shape
    pad = np.pad(arr, ((1, 1), (1, 1), (0, 0)), mode='edge')
    P = arr
    A = pad[0:H, 1:W+1]
    B = pad[1:H+1, 2:W+2]
    C_pix = pad[1:H+1, 0:W]
    D = pad[2:H+2, 1:W+1]

    eq_CA = pixel_eq(C_pix, A)
    eq_CD = pixel_eq(C_pix, D)
    eq_AB = pixel_eq(A, B)
    eq_BD = pixel_eq(B, D)

    out = np.zeros((H * 2, W * 2, C), dtype=arr.dtype)
    cond1 = eq_CA & (~eq_CD) & (~eq_AB)
    cond2 = eq_AB & (~eq_CA) & (~eq_BD)
    cond3 = eq_CD & (~eq_BD) & (~eq_CA)
    cond4 = eq_BD & (~eq_AB) & (~eq_CD)

    out[0::2, 0::2] = np.where(cond1[..., None], A, P)
    out[0::2, 1::2] = np.where(cond2[..., None], B, P)
    out[1::2, 0::2] = np.where(cond3[..., None], C_pix, P)
    out[1::2, 1::2] = np.where(cond4[..., None], D, P)
    return out

def scale3x_epx(arr: np.ndarray) -> np.ndarray:
    """
    Vectorized Scale3x / AdvMAME3x algorithm.
    Triples resolution (3x).
    """
    H, W, C = arr.shape
    pad = np.pad(arr, ((1, 1), (1, 1), (0, 0)), mode='edge')
    A = pad[0:H, 0:W]
    B = pad[0:H, 1:W+1]
    C_p = pad[0:H, 2:W+2]
    D = pad[1:H+1, 0:W]
    E = arr
    F = pad[1:H+1, 2:W+2]
    G = pad[2:H+2, 0:W]
    H_p = pad[2:H+2, 1:W+1]
    I = pad[2:H+2, 2:W+2]

    DB = pixel_eq(D, B)
    DH = pixel_eq(D, H_p)
    BF = pixel_eq(B, F)
    HF = pixel_eq(H_p, F)

    out = np.zeros((H * 3, W * 3, C), dtype=arr.dtype)

    # E0
    c0 = DB & (~DH) & (~BF)
    out[0::3, 0::3] = np.where(c0[..., None], D, E)

    # E1
    c1 = (DB & (~DH) & (~BF) & (~pixel_eq(E, C_p))) | (BF & (~DB) & (~HF) & (~pixel_eq(E, A)))
    out[0::3, 1::3] = np.where(c1[..., None], B, E)

    # E2
    c2 = BF & (~DB) & (~HF)
    out[0::3, 2::3] = np.where(c2[..., None], F, E)

    # E3
    c3 = (DB & (~DH) & (~BF) & (~pixel_eq(E, G))) | (DH & (~DB) & (~HF) & (~pixel_eq(E, A)))
    out[1::3, 0::3] = np.where(c3[..., None], D, E)

    # E4
    out[1::3, 1::3] = E

    # E5
    c5 = (BF & (~DB) & (~HF) & (~pixel_eq(E, I))) | (HF & (~DH) & (~BF) & (~pixel_eq(E, C_p)))
    out[1::3, 2::3] = np.where(c5[..., None], F, E)

    # E6
    c6 = DH & (~DB) & (~HF)
    out[2::3, 0::3] = np.where(c6[..., None], D, E)

    # E7
    c7 = (DH & (~DB) & (~HF) & (~pixel_eq(E, I))) | (HF & (~DH) & (~BF) & (~pixel_eq(E, G)))
    out[2::3, 1::3] = np.where(c7[..., None], H_p, E)

    # E8
    c8 = HF & (~DH) & (~BF)
    out[2::3, 2::3] = np.where(c8[..., None], F, E)

    return out

def scale4x_epx(arr: np.ndarray) -> np.ndarray:
    """
    Two consecutive passes of Scale2x. Quadruples resolution (4x).
    """
    pass1 = scale2x_epx(arr)
    return scale2x_epx(pass1)

def nearest_neighbor(arr: np.ndarray, factor: int = 2) -> np.ndarray:
    """
    Pure nearest neighbor scaling.
    """
    return np.repeat(np.repeat(arr, factor, axis=0), factor, axis=1)

def lanczos_upscale(arr: np.ndarray, factor: int = 2) -> np.ndarray:
    """
    Lanczos resampling with subtle unsharp masking.
    """
    H, W, _ = arr.shape
    im = Image.fromarray(arr, "RGBA")
    up = im.resize((W * factor, H * factor), Image.Resampling.LANCZOS)
    sharpened = up.filter(ImageFilter.UnsharpMask(radius=1, percent=110, threshold=2))
    return np.array(sharpened)

def bicubic_upscale(arr: np.ndarray, factor: int = 2) -> np.ndarray:
    """
    Standard bicubic resampling.
    """
    H, W, _ = arr.shape
    im = Image.fromarray(arr, "RGBA")
    up = im.resize((W * factor, H * factor), Image.Resampling.BICUBIC)
    return np.array(up)

def upscale_image_array(arr: np.ndarray, algorithm: str = "scale2x", factor: int = 2) -> np.ndarray:
    """
    Dispatches to the requested upscaling algorithm.
    """
    algo = algorithm.lower()
    if algo == "scale2x":
        return scale2x_epx(arr)
    elif algo == "scale3x":
        return scale3x_epx(arr)
    elif algo == "scale4x":
        return scale4x_epx(arr)
    elif algo == "nearest":
        return nearest_neighbor(arr, factor)
    elif algo == "lanczos":
        return lanczos_upscale(arr, factor)
    elif algo == "bicubic":
        return bicubic_upscale(arr, factor)
    else:
        # Default fallback
        return scale2x_epx(arr)
