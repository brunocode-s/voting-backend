"""
Test biometric installation
"""
import face_recognition
import numpy as np
from PIL import Image
import io

def test_libraries():
    """Test if all biometric libraries are installed correctly"""
    
    print("Testing biometric libraries...")
    
    try:
        # Test face_recognition
        print("✓ face_recognition imported successfully")
        
        # Test opencv
        import cv2
        print(f"✓ OpenCV version: {cv2.__version__}")
        
        # Test PIL
        print(f"✓ Pillow version: {Image.__version__}")
        
        # Test numpy
        print(f"✓ NumPy version: {np.__version__}")
        
        # Create a simple test image
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[100:200, 200:300] = [255, 255, 255]  # White square
        
        # Try to find faces (should find none, but shouldn't crash)
        face_locations = face_recognition.face_locations(test_image)
        print(f"✓ Face detection works (found {len(face_locations)} faces in test image)")
        
        print("\n✅ All biometric libraries installed correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_libraries()