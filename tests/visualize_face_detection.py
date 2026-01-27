#!/usr/bin/env python3
"""
Visualize face detection boundaries
Captures a frame and draws rectangles around detected faces
"""

import sys
import cv2
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))


def visualize_face_detection(video_path: Path, output_path: Path, frame_number: int = 100):
    """
    Capture a frame and draw face detection boundaries

    Args:
        video_path: Path to video
        output_path: Path to save image
        frame_number: Which frame to capture
    """
    print(f"\n{'='*60}")
    print(f"Visualizing Face Detection")
    print(f"{'='*60}")

    # Load face detector
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(cascade_path)

    # Open video
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print(f"✗ Error: Cannot open video")
        return False

    # Get video info
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"\nVideo info:")
    print(f"  Resolution: {width}x{height}")
    print(f"  Total frames: {total_frames}")
    print(f"  FPS: {fps:.2f}")

    # Seek to frame
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print(f"✗ Error: Cannot read frame {frame_number}")
        return False

    timestamp = frame_number / fps
    print(f"\nCapturing frame {frame_number} (at {timestamp:.1f}s)")

    # Detect faces
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30)
    )

    print(f"\nDetected {len(faces)} face(s):")

    # Draw rectangles around faces and outer crop boxes
    for i, (x, y, w, h) in enumerate(faces):
        # Calculate face center
        center_x = x + w // 2
        center_y = y + h // 2

        print(f"\n  Face {i+1}:")
        print(f"    Top-left: ({x}, {y})")
        print(f"    Width x Height: {w} x {h}")
        print(f"    Center: ({center_x}, {center_y})")
        print(f"    Face occupies: {(w/width)*100:.1f}% of video width")
        print(f"    Face occupies: {(h/height)*100:.1f}% of video height")

        # Calculate outer crop box using corner-based algorithm
        # Given face detection (x, y, w, h), convert to corners:
        #   Face LT = (x, y)
        #   Face RB = (x + w, y + h)
        # Then apply padding:
        #   Box.LT-x = Face.LT-x - face.width
        #   Box.LT-y = Face.LT-y - (face.height / 2)
        #   Box.RB-x = Face.RB-x + face.width
        #   Box.RB-y = Face.RB-y + (face.height * 0.75)

        face_lt_x = x
        face_lt_y = y
        face_rb_x = x + w
        face_rb_y = y + h

        box_lt_x = int(face_lt_x - w/2)
        box_lt_y = int(face_lt_y - (h / 4))
        box_rb_x = int(face_rb_x + w/2)
        box_rb_y = int(face_rb_y + (h * 0.35))
        box_width = box_rb_x - box_lt_x
        box_height = box_rb_y - box_lt_y

        # No boundary clamping - allow visualization of full algorithm

        print(f"\n    Outer Crop Box (before 9:8 conforming):")
        print(f"      Top-left: ({box_lt_x}, {box_lt_y})")
        print(f"      Bottom-right: ({box_rb_x}, {box_rb_y})")
        print(f"      Size: {box_width}x{box_height}")
        print(f"      Ratio: {(box_rb_x - box_lt_x)/(box_rb_y - box_lt_y):.3f}")

        # Conform to 9:8 ratio
        crop_width = box_width
        crop_height = int(crop_width * 8 / 9)

        # Check if exceeds half height (for stacking)

        if crop_height > crop_width:
            crop_width = int(crop_height * 9 / 8)
            
        # Re-center the crop box horizontally, keep top position
        final_x = center_x - crop_width // 2
        final_y = box_lt_y  # Keep top position (no clamping)

        print(f"\n    Final 9:8 Crop Box:")
        print(f"      Top-left: ({final_x}, {final_y})")
        print(f"      Size: {crop_width}x{crop_height}")
        print(f"      Ratio: {crop_width/crop_height:.3f} (should be 1.125)")
        print(f"      Face occupies: {(w/crop_width)*100:.1f}% of box width")

        # Draw thick red rectangle around face detection bounds
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 5)

        # Draw green rectangle for the final 9:8 crop box
        cv2.rectangle(frame, (final_x, final_y),
                     (final_x + crop_width, final_y + crop_height),
                     (0, 255, 0), 4)


        # Draw center point
        cv2.circle(frame, (center_x, center_y), 10, (255, 0, 0), -1)

        # Add labels
        face_label = f"Face {i+1}: {w}x{h}"
        box_label = f"9:8 Box: {crop_width}x{crop_height}"
        cv2.putText(frame, face_label, (x, y - 40), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 0, 255), 3)
        cv2.putText(frame, box_label, (final_x, final_y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 255, 0), 3)

    # Save image
    cv2.imwrite(str(output_path), frame)
    print(f"\n✓ Saved visualization to: {output_path.name}")

    return True


def main():
    """Main function"""
    # Find the test clip
    downloads_dir = Path(__file__).parent.parent / 'downloads'
    video_file = downloads_dir / '6g-qJ4QZ6Sk_test_clip.mp4'

    if not video_file.exists():
        print(f"✗ Error: Test clip not found at {video_file}")
        return 1

    print(f"✓ Found video: {video_file.name}")

    # Output path
    output_file = downloads_dir / f"{video_file.stem}_face_detection.jpg"

    # Visualize at frame 100 (around 3-4 seconds in)
    success = visualize_face_detection(video_file, output_file, frame_number=100)

    if success:
        print(f"\n{'='*60}")
        print("VISUALIZATION COMPLETE")
        print(f"{'='*60}")
        print(f"Opening image...")
        print(f"{'='*60}\n")

        # Open the image
        import subprocess
        subprocess.run(['open', str(output_file)])
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())
