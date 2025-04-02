from flask import Blueprint, request, jsonify
import rembg
import cv2
import numpy as np
import requests
from skimage.metrics import structural_similarity as compare_ssim
import os

gm_bp = Blueprint('gm_bp', __name__)

# Create a directory for storing processed images
os.makedirs("./removed_bg", exist_ok=True)

def remove_background(image):
    """Removes background from an image while keeping only the object with transparency."""
    _, encoded_image = cv2.imencode('.png', image)
    image_data = encoded_image.tobytes()
    output_data = rembg.remove(image_data)
    nparr = np.frombuffer(output_data, np.uint8)
    processed_image = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    return processed_image

def preprocess_image(image):
    """Convert image to grayscale, normalize contrast, and apply Gaussian blur."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY) if image.shape[-1] == 4 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Apply Contrast Limited Adaptive Histogram Equalization (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    # Apply Gaussian blur to reduce noise
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    return gray

def compare_images(image1, image2):
    """Compares two images using SSIM (Structural Similarity Index)."""
    gray1 = preprocess_image(image1)
    gray2 = preprocess_image(image2)

    # Resize images to a common size
    target_size = (max(gray1.shape[1], gray2.shape[1]), max(gray1.shape[0], gray2.shape[0]))
    gray1_resized = cv2.resize(gray1, target_size, interpolation=cv2.INTER_AREA)
    gray2_resized = cv2.resize(gray2, target_size, interpolation=cv2.INTER_AREA)

    # Compute SSIM
    ssim_score, _ = compare_ssim(gray1_resized, gray2_resized, full=True)
    ssim_similarity = ssim_score * 100

    return {"message": "Comparison completed", "similarity": ssim_similarity}

def download_image(url):
    """Downloads an image from a URL and returns it as a NumPy array."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        image_data = np.frombuffer(response.content, np.uint8)
        return cv2.imdecode(image_data, cv2.IMREAD_UNCHANGED)
    except requests.exceptions.RequestException:
        return None

@gm_bp.route('/compare', methods=['POST'])
def compare_objects():
    """API Endpoint to compare a Cloudinary image (URL) with an uploaded file."""
    if 'image_url' not in request.form or 'image_file' not in request.files:
        return jsonify({"error": "Both 'image_url' (Cloudinary) and 'image_file' (uploaded) are required"}), 400

    image_url = request.form['image_url']
    image_file = request.files['image_file']

    image1 = download_image(image_url)
    if image1 is None:
        return jsonify({"error": "Failed to download image from URL"}), 400

    image2_data = image_file.read()
    image2_np = np.frombuffer(image2_data, np.uint8)
    image2 = cv2.imdecode(image2_np, cv2.IMREAD_UNCHANGED)
    if image2 is None:
        return jsonify({"error": "Failed to read the uploaded image file"}), 400

    # Remove backgrounds
    image1 = remove_background(image1)
    image2 = remove_background(image2)

    # Compare images using SSIM
    result = compare_images(image1, image2)

    print("Result : ", result)

    return jsonify(result)
