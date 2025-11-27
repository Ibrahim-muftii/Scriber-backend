from flask import Blueprint, request, jsonify
import rembg
import cv2
import numpy as np
import requests
import os

gm_bp = Blueprint('gm_bp', __name__)

# Create directory for any saved processing if needed
os.makedirs("./removed_bg", exist_ok=True)

# ---------- UTILITY FUNCTIONS ---------- #

def remove_background(image):
    """Removes background from an image while keeping only the object with transparency."""
    _, encoded_image = cv2.imencode('.png', image)
    image_data = encoded_image.tobytes()
    output_data = rembg.remove(image_data)
    nparr = np.frombuffer(output_data, np.uint8)
    processed_image = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
    return processed_image

def extract_largest_shape(image):
    """Returns the largest contour and binary mask of the shape."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY if image.shape[-1] == 4 else cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None, None

    largest = max(contours, key=cv2.contourArea)
    mask = np.zeros_like(binary)
    cv2.drawContours(mask, [largest], -1, 255, thickness=cv2.FILLED)
    return largest, mask

def compare_images(image1, image2):
    """Compares two shapes based on structure and pixel overlap."""
    contour1, mask1 = extract_largest_shape(image1)
    contour2, mask2 = extract_largest_shape(image2)

    if contour1 is None or contour2 is None:
        return {"message": "No shapes detected", "similarity": 0}

    # Resize both masks to the same canvas size
    height = max(mask1.shape[0], mask2.shape[0])
    width = max(mask1.shape[1], mask2.shape[1])
    mask1 = cv2.resize(mask1, (width, height), interpolation=cv2.INTER_NEAREST)
    mask2 = cv2.resize(mask2, (width, height), interpolation=cv2.INTER_NEAREST)

    # --- Shape Similarity (lower score = better) ---
    shape_score = cv2.matchShapes(contour1, contour2, cv2.CONTOURS_MATCH_I1, 0.0)
    shape_similarity = max(0, 100 - shape_score * 1000)  # Cap between 0–100

    # --- Pixel-level overlap ---
    intersection = np.logical_and(mask1 > 0, mask2 > 0).sum()
    union = np.logical_or(mask1 > 0, mask2 > 0).sum()
    pixel_similarity = (intersection / union) * 100 if union != 0 else 0

    # --- Final weighted score (more weight to shape) ---
    final_score = (shape_similarity * 0.6) + (pixel_similarity * 0.4)

    return {
        "message": "Comparison completed",
        "shape_similarity": round(shape_similarity, 2),
        "pixel_similarity": round(pixel_similarity, 2),
        "similarity": round(final_score, 2)
    }

def download_image(url):
    """Downloads an image from a URL and returns it as a NumPy array."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        image_data = np.frombuffer(response.content, np.uint8)
        return cv2.imdecode(image_data, cv2.IMREAD_UNCHANGED)
    except requests.exceptions.RequestException:
        return None

# ---------- ROUTE ---------- #

@gm_bp.route('/compare', methods=['POST'])
def compare_objects():
    """API Endpoint to compare a Cloudinary image (URL) with an uploaded file."""
    if 'image_url' not in request.form or 'image_file' not in request.files:
        return jsonify({"error": "Both 'image_url' (Cloudinary) and 'image_file' (uploaded) are required"}), 400

    image_url = request.form['image_url']
    image_file = request.files['image_file']

    # Download the Cloudinary image
    image1 = download_image(image_url)
    if image1 is None:
        return jsonify({"error": "Failed to download image from URL"}), 400

    # Load the uploaded image
    image2_data = image_file.read()
    image2_np = np.frombuffer(image2_data, np.uint8)
    image2 = cv2.imdecode(image2_np, cv2.IMREAD_UNCHANGED)
    if image2 is None:
        return jsonify({"error": "Failed to read the uploaded image file"}), 400

    # Remove backgrounds
    image1 = remove_background(image1)
    image2 = remove_background(image2)

    # Compare shapes
    result = compare_images(image1, image2)

    print("Result:", result)
    return jsonify(result)
